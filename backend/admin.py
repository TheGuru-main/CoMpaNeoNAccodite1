"""
Accodite Admin
==============
Org-scoped admin actions:

    GET    /admin/pending                 list pending worker signups
    POST   /admin/approve/{membership_id} approve + provision worker
    POST   /admin/reject/{membership_id}  reject + delete membership
    GET    /admin/members                 full roster of the org
    POST   /admin/role                    change a member's role

Access:  CEO, HR, or the caller's own role == ROLE_DEPT_HEAD for their dept.
The caller's organization is inferred from their membership.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database import SessionLocal
from db_models import User, Organization, OrganizationMembership
from auth import get_current_user
from org.roles import (
    ROLE_CEO, ROLE_C_SUITE, ROLE_HR, ROLE_DEPT_HEAD,
    ROLE_MANAGER, ROLE_MEMBER, ROLE_REVIEWER, ROLE_VIEWER,
    can_read_ltm,
)

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_ROLES = {ROLE_CEO, ROLE_C_SUITE, ROLE_HR}
VALID_ROLES = {
    ROLE_CEO, ROLE_C_SUITE, ROLE_HR, ROLE_DEPT_HEAD,
    ROLE_MANAGER, ROLE_MEMBER, ROLE_REVIEWER, ROLE_VIEWER,
}


class ChangeRoleReq(BaseModel):
    membership_id: str = Field(..., min_length=6)
    new_role: str = Field(..., min_length=2, max_length=50)


# ============================================================================
# HELPERS
# ============================================================================

def _org_memberships_for_user(db, user_id):
    return db.query(OrganizationMembership).filter(
        OrganizationMembership.user_id == user_id
    ).all()


def _pick_admin_membership(db, user, requested_org_id: Optional[str] = None):
    """
    Return the caller's admin membership.
    If requested_org_id is given, use it. Otherwise pick the first
    membership whose role grants admin access.
    """
    rows = _org_memberships_for_user(db, user.id)
    if requested_org_id:
        for m in rows:
            if str(m.organization_id) == str(requested_org_id):
                if m.role in ADMIN_ROLES or m.role == ROLE_DEPT_HEAD:
                    return m
        return None
    for m in rows:
        if m.role in ADMIN_ROLES or m.role == ROLE_DEPT_HEAD:
            return m
    return None


def _serialize_membership(db, m: OrganizationMembership) -> Dict[str, Any]:
    user = db.query(User).filter(User.id == m.user_id).first()
    return {
        "membership_id": str(m.id),
        "user_id": str(m.user_id),
        "phone": user.phone if user else None,
        "full_name": user.full_name if user else None,
        "country": user.country if user else None,
        "role": m.role,
        "department": getattr(m, "department", None),
        "title": getattr(m, "title", None),
        "credential_active": bool(getattr(m, "credential_active", False)),
        "created_at": m.created_at.isoformat() if getattr(m, "created_at", None) else None,
    }


def _assert_can_admin(m: OrganizationMembership) -> None:
    if m.role in ADMIN_ROLES:
        return
    if m.role == ROLE_DEPT_HEAD:
        return
    raise HTTPException(403, "insufficient role to perform admin actions")


# ============================================================================
# ROUTES
# ============================================================================

@router.get("/pending")
async def list_pending(
    org_id: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        me = _pick_admin_membership(db, user, org_id)
        if me is None:
            raise HTTPException(403, "not an admin in any org")
        _assert_can_admin(me)

        q = db.query(OrganizationMembership).filter(
            OrganizationMembership.organization_id == me.organization_id,
            OrganizationMembership.credential_active.is_(False),
        )
        # dept_head scopes to their own department only
        if me.role == ROLE_DEPT_HEAD and getattr(me, "department", None):
            q = q.filter(OrganizationMembership.department == me.department)

        return [_serialize_membership(db, m) for m in q.all()]
    finally:
        db.close()


@router.get("/members")
async def list_members(
    org_id: Optional[str] = None,
    include_pending: bool = False,
    user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        me = _pick_admin_membership(db, user, org_id)
        if me is None:
            raise HTTPException(403, "not an admin in any org")
        _assert_can_admin(me)

        q = db.query(OrganizationMembership).filter(
            OrganizationMembership.organization_id == me.organization_id,
        )
        if not include_pending:
            q = q.filter(OrganizationMembership.credential_active.is_(True))
        if me.role == ROLE_DEPT_HEAD and getattr(me, "department", None):
            q = q.filter(OrganizationMembership.department == me.department)

        return [_serialize_membership(db, m) for m in q.all()]
    finally:
        db.close()


@router.post("/approve/{membership_id}")
async def approve_member(
    membership_id: str,
    user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        target = db.query(OrganizationMembership).filter(
            OrganizationMembership.id == membership_id
        ).first()
        if target is None:
            raise HTTPException(404, "membership not found")

        me = _pick_admin_membership(db, user, str(target.organization_id))
        if me is None:
            raise HTTPException(403, "not an admin for that org")
        _assert_can_admin(me)
        if me.role == ROLE_DEPT_HEAD and getattr(me, "department", None):
            if target.department != me.department:
                raise HTTPException(403, "not your department")

        if target.credential_active:
            return {"ok": True, "already_active": True}

        target.credential_active = True
        target.updated_at = datetime.utcnow()
        db.commit()

        # provision worker rooms — brainstorm + dept membership
        provision_report: Dict[str, Any] = {}
        try:
            from org.worker_bootstrap import provision_org_worker
            target_user = db.query(User).filter(User.id == target.user_id).first()
            if target_user is not None:
                report = provision_org_worker(
                    session=db,
                    user_id=str(target_user.id),
                    organization_id=str(target.organization_id),
                    department=target.department or "General",
                    display_name=target_user.full_name or "Worker",
                    role=target.role,
                    added_by=str(me.user_id),
                )
                provision_report = report
                db.commit()
        except Exception as e:
            provision_report = {"error": f"{type(e).__name__}: {e}"}
            print(f"[admin] provision error: {provision_report['error']}")

        return {
            "ok": True,
            "membership_id": str(target.id),
            "phone": _serialize_membership(db, target).get("phone"),
            "provisioned": provision_report,
        }
    finally:
        db.close()


@router.post("/reject/{membership_id}")
async def reject_member(
    membership_id: str,
    user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        target = db.query(OrganizationMembership).filter(
            OrganizationMembership.id == membership_id
        ).first()
        if target is None:
            raise HTTPException(404, "membership not found")

        me = _pick_admin_membership(db, user, str(target.organization_id))
        if me is None:
            raise HTTPException(403, "not an admin for that org")
        _assert_can_admin(me)
        if me.role == ROLE_DEPT_HEAD and getattr(me, "department", None):
            if target.department != me.department:
                raise HTTPException(403, "not your department")

        if target.credential_active:
            raise HTTPException(400, "cannot reject an already-active member")

        phone = None
        u = db.query(User).filter(User.id == target.user_id).first()
        if u is not None:
            phone = u.phone

        db.delete(target)
        db.commit()
        return {"ok": True, "rejected_membership_id": membership_id, "phone": phone}
    finally:
        db.close()


@router.post("/role")
async def change_role(
    req: ChangeRoleReq,
    user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        if req.new_role not in VALID_ROLES:
            raise HTTPException(400, f"invalid role: {req.new_role}")

        target = db.query(OrganizationMembership).filter(
            OrganizationMembership.id == req.membership_id
        ).first()
        if target is None:
            raise HTTPException(404, "membership not found")

        me = _pick_admin_membership(db, user, str(target.organization_id))
        if me is None:
            raise HTTPException(403, "not an admin for that org")
        if me.role not in ADMIN_ROLES:
            raise HTTPException(403, "only CEO/HR can change roles")

        # a CEO cannot be demoted by themselves to avoid lockout
        if (target.role == ROLE_CEO and req.new_role != ROLE_CEO
                and target.user_id == user.id):
            raise HTTPException(400, "cannot demote your own CEO role")

        old_role = target.role
        target.role = req.new_role
        target.updated_at = datetime.utcnow()
        db.commit()

        return {
            "ok": True,
            "membership_id": str(target.id),
            "old_role": old_role,
            "new_role": req.new_role,
            "ltm_access": can_read_ltm(req.new_role),
        }
    finally:
        db.close()


# ============================================================================
# WORKER CREDENTIAL
# ============================================================================

def _ensure_credential(db, org):
    """
    Return the current worker credential, generating one if the org does
    not have one yet (legacy orgs created before credentials were stored).
    """
    import hashlib as _h, secrets as _s
    cred = getattr(org, "worker_credential", None)
    if cred:
        return cred
    suffix = _s.token_hex(4)
    phone_tail = "0000"
    if org.phone:
        phone_tail = org.phone[-4:]
    cred = f"{org.slug}:{phone_tail}:{suffix}"
    org.worker_credential = cred
    org.worker_credential_hash = _h.sha256(cred.encode("utf-8")).hexdigest()
    org.worker_credential_rotated_at = datetime.utcnow()
    db.commit()
    return cred


@router.get("/credential")
async def get_worker_credential(
    org_id: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """Return the current shared worker credential. CEO/HR only."""
    db = SessionLocal()
    try:
        me = _pick_admin_membership(db, user, org_id)
        if me is None:
            raise HTTPException(403, "not an admin in any org")
        if me.role not in ADMIN_ROLES:
            raise HTTPException(403, "only CEO / c_suite / HR can view the credential")

        org = db.query(Organization).filter(
            Organization.id == me.organization_id
        ).first()
        if org is None:
            raise HTTPException(404, "org not found")

        cred = _ensure_credential(db, org)
        return {
            "org_id": str(org.id),
            "org_name": org.name,
            "org_slug": org.slug,
            "worker_credential": cred,
            "rotated_at": org.worker_credential_rotated_at.isoformat()
                          if getattr(org, "worker_credential_rotated_at", None)
                          else None,
            "share_hint": "Share this one credential with every worker joining your org.",
        }
    finally:
        db.close()


@router.post("/credential/rotate")
async def rotate_worker_credential(
    org_id: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """Generate a new worker credential, invalidating the old one. CEO/HR only."""
    import hashlib as _h, secrets as _s
    db = SessionLocal()
    try:
        me = _pick_admin_membership(db, user, org_id)
        if me is None:
            raise HTTPException(403, "not an admin in any org")
        if me.role not in ADMIN_ROLES:
            raise HTTPException(403, "only CEO / c_suite / HR can rotate the credential")

        org = db.query(Organization).filter(
            Organization.id == me.organization_id
        ).first()
        if org is None:
            raise HTTPException(404, "org not found")

        phone_tail = (org.phone[-4:] if org.phone else "0000")
        new_cred = f"{org.slug}:{phone_tail}:{_s.token_hex(4)}"
        org.worker_credential = new_cred
        org.worker_credential_hash = _h.sha256(new_cred.encode("utf-8")).hexdigest()
        org.worker_credential_rotated_at = datetime.utcnow()
        db.commit()

        return {
            "ok": True,
            "worker_credential": new_cred,
            "rotated_at": org.worker_credential_rotated_at.isoformat(),
            "note": "The previous credential is now invalid.",
        }
    finally:
        db.close()


# ============================================================================
# ORG DETAILS
# ============================================================================

class OrgDetailsReq(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    country: Optional[str] = None
    org_type: Optional[str] = None
    goals: Optional[str] = None
    ai_temperament: Optional[str] = None


@router.get("/org-details")
async def get_org_details(user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        me = _pick_admin_membership(db, user)
        if me is None:
            raise HTTPException(403, "not an admin in any org")
        org = db.query(Organization).filter(Organization.id == me.organization_id).first()
        if org is None:
            raise HTTPException(404, "org not found")
        s = org.settings or {}
        return {
            "org_id": str(org.id),
            "name": org.name,
            "email": org.email,
            "country": org.country,
            "ai_uid": org.ai_uid,
            "phone": getattr(org, "phone", None),
            "settings": {
                "org_type": s.get("org_type", "software"),
                "goals": s.get("goals", ""),
                "ai_temperament": s.get("ai_temperament", "sanguine"),
            },
        }
    finally:
        db.close()


@router.put("/org-details")
async def update_org_details(req: OrgDetailsReq, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        me = _pick_admin_membership(db, user)
        if me is None:
            raise HTTPException(403, "not an admin in any org")
        if me.role not in ADMIN_ROLES:
            raise HTTPException(403, "only CEO / c_suite / HR can edit org details")
        org = db.query(Organization).filter(Organization.id == me.organization_id).first()
        if org is None:
            raise HTTPException(404, "org not found")

        if req.name is not None: org.name = req.name
        if req.email is not None: org.email = req.email
        if req.country is not None: org.country = req.country

        s = dict(org.settings or {})
        if req.org_type is not None: s["org_type"] = req.org_type
        if req.goals is not None: s["goals"] = req.goals
        if req.ai_temperament is not None: s["ai_temperament"] = req.ai_temperament
        org.settings = s
        db.commit()
        return {"ok": True, "settings": s}
    finally:
        db.close()


# ============================================================================
# DEPARTMENTS
# ============================================================================

class CreateDeptReq(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


@router.get("/departments")
async def list_departments(user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        me = _pick_admin_membership(db, user)
        if me is None:
            raise HTTPException(403, "not an admin in any org")
        from db_models import Workspace
        rows = db.query(Workspace).filter(
            Workspace.organization_id == me.organization_id,
            Workspace.workspace_type == "department",
        ).all()
        out = []
        for r in rows:
            out.append({
                "id": str(r.id),
                "name": r.project_name,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return out
    finally:
        db.close()


@router.post("/departments")
async def create_department(req: CreateDeptReq, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        me = _pick_admin_membership(db, user)
        if me is None:
            raise HTTPException(403, "not an admin in any org")
        if me.role not in ADMIN_ROLES and me.role != ROLE_DEPT_HEAD:
            raise HTTPException(403, "only CEO / c_suite / HR / dept_head can create departments")
        from org.departments import create_department_room
        room = create_department_room(
            session=db,
            organization_id=str(me.organization_id),
            department_name=req.name.strip(),
            created_by=str(user.id),
        )
        db.commit()
        return {"ok": True, "id": str(room.id), "name": room.project_name}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    finally:
        db.close()


# ============================================================================
# DIRECTIVE BOARDS
# ============================================================================

class CreateBoardReq(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    pattern_kinds: List[str] = Field(default_factory=list)
    min_severity: str = "warn"
    subscribers: List[Dict[str, Any]] = Field(default_factory=list)


@router.get("/boards")
async def list_boards(user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        me = _pick_admin_membership(db, user)
        if me is None:
            raise HTTPException(403, "not an admin in any org")
        try:
            from db.models_org import DirectiveBoard
        except Exception:
            from models_org import DirectiveBoard
        rows = db.query(DirectiveBoard).filter(
            DirectiveBoard.organization_id == me.organization_id
        ).all()
        return [{
            "id": str(r.id),
            "name": r.name,
            "pattern_kinds": r.pattern_kinds or [],
            "min_severity": r.min_severity,
            "subscribers": r.subscribers or [],
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows]
    finally:
        db.close()


@router.post("/boards")
async def create_board(req: CreateBoardReq, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        me = _pick_admin_membership(db, user)
        if me is None:
            raise HTTPException(403, "not an admin in any org")
        try:
            from db.models_org import DirectiveBoard
        except Exception:
            from models_org import DirectiveBoard
        import uuid as _uuid
        board = DirectiveBoard(
            id=_uuid.uuid4(),
            organization_id=me.organization_id,
            name=req.name.strip(),
            pattern_kinds=req.pattern_kinds,
            min_severity=req.min_severity,
            subscribers=req.subscribers,
        )
        db.add(board)
        db.commit()
        return {"ok": True, "id": str(board.id), "name": board.name}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    finally:
        db.close()


@router.delete("/boards/{board_id}")
async def delete_board(board_id: str, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        me = _pick_admin_membership(db, user)
        if me is None:
            raise HTTPException(403, "not an admin in any org")
        try:
            from db.models_org import DirectiveBoard
        except Exception:
            from models_org import DirectiveBoard
        board = db.query(DirectiveBoard).filter(
            DirectiveBoard.id == board_id,
            DirectiveBoard.organization_id == me.organization_id,
        ).first()
        if board is None:
            raise HTTPException(404, "board not found")
        db.delete(board)
        db.commit()
        return {"ok": True}
    finally:
        db.close()

"""
Accodite Rooms
==============
Workspace CRUD + room chat.

Every user-facing conversation is a Workspace row. member_count and
workspace_type decide the AI trigger rule:

    personal_brainstorm (1 member)  -> every message fires the AI
    group / department / team /
    meeting / organization (2+)     -> only @AI / highlight / swipe

Peer-to-peer DMs are handled by message.py — a separate system.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_

from database import SessionLocal
from db_models import User, Workspace, Message
try:
    from phone_util import normalize_phone, variants
except ImportError:
    def normalize_phone(p, default_country='NG'): return p
    def variants(p): return [p] if p else []
from auth import get_current_user
from org.roles import (
    ROLE_OWNER, ROLE_CEO, ROLE_HR, ROLE_DEPT_HEAD, ROLE_MANAGER,
)

try:
    from db.models_org import WorkspaceMember
except Exception:
    try:
        from models_org import WorkspaceMember
    except Exception:
        WorkspaceMember = None


router = APIRouter(prefix="/rooms", tags=["rooms"])

CREATABLE_TYPES = {
    "personal_brainstorm", "group", "department",
    "team", "meeting", "organization",
}


class CreateRoomReq(BaseModel):
    workspace_type: str = "personal_brainstorm"
    project_name: str = Field(..., min_length=1, max_length=255)
    project_domain: str = "general"
    organization_id: Optional[str] = None


class RenameRoomReq(BaseModel):
    project_name: Optional[str] = None
    project_domain: Optional[str] = None


class SendMessageReq(BaseModel):
    content: str = Field(..., min_length=1, max_length=20000)


class InviteMemberReq(BaseModel):
    phone: str = Field(..., min_length=5, max_length=32)


def _role_for(db, user, org_id):
    if not org_id:
        return ROLE_OWNER
    try:
        from db_models import OrganizationMembership
    except Exception:
        from models import OrganizationMembership
    m = db.query(OrganizationMembership).filter(
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.organization_id == org_id,
    ).first()
    return m.role if m else None


def _is_member(db, ws, user_id) -> bool:
    if ws.user_id == user_id:
        return True
    if WorkspaceMember is None:
        return False
    return db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws.id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.removed_at.is_(None),
    ).first() is not None


def _member_count(db, ws) -> int:
    # MEMBER-DEDUP: the owner may also be a WorkspaceMember row.
    # Count unique user_ids, not rows.
    ids = set()
    if ws.user_id is not None:
        ids.add(str(ws.user_id))
    if WorkspaceMember is not None:
        for r in db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.removed_at.is_(None),
        ).all():
            ids.add(str(r.user_id))
    return max(len(ids), 1)


def _can_create(db, user, wtype, org_id) -> bool:
    if wtype in ("personal_brainstorm", "group"):
        return True
    role = _role_for(db, user, org_id)
    if role is None:
        return False
    if wtype == "department":
        return role in {ROLE_CEO, ROLE_HR, ROLE_DEPT_HEAD, ROLE_MANAGER}
    if wtype == "team":
        return role in {ROLE_CEO, ROLE_DEPT_HEAD, ROLE_MANAGER}
    if wtype == "meeting":
        return True
    if wtype == "organization":
        return role == ROLE_CEO
    return False


def _serialize(db, ws) -> Dict[str, Any]:
    return {
        "id": str(ws.id),
        "workspace_type": ws.workspace_type,
        "project_name": ws.project_name,
        "project_domain": ws.project_domain,
        "user_id": str(ws.user_id) if ws.user_id else None,
        "organization_id": str(ws.organization_id) if ws.organization_id else None,
        "ai_invocation": getattr(ws, "ai_invocation", "@AI"),
        "member_count": _member_count(db, ws),
        "created_at": ws.created_at.isoformat() if ws.created_at else None,
        "updated_at": ws.updated_at.isoformat() if ws.updated_at else None,
    }


@router.get("")
async def list_rooms(
    workspace_type: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        cond = [Workspace.user_id == user.id]
        if WorkspaceMember is not None:
            sub = db.query(WorkspaceMember.workspace_id).filter(
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.removed_at.is_(None),
            )
            cond.append(Workspace.id.in_(sub))
        q = db.query(Workspace).filter(or_(*cond))
        if hasattr(Workspace, "deleted_at"):
            q = q.filter(Workspace.deleted_at.is_(None))
        if workspace_type:
            q = q.filter(Workspace.workspace_type == workspace_type)
        q = q.order_by(Workspace.updated_at.desc())
        return [_serialize(db, r) for r in q.all()]
    finally:
        db.close()


@router.post("")
async def create_room(req: CreateRoomReq, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        if req.workspace_type not in CREATABLE_TYPES:
            raise HTTPException(400, f"unknown workspace_type: {req.workspace_type}")
        if not _can_create(db, user, req.workspace_type, req.organization_id):
            raise HTTPException(403, f"your role cannot create {req.workspace_type}")

        owner_id = user.id if req.workspace_type in ("personal_brainstorm", "group") else None
        ws = Workspace(
            id=uuid.uuid4(),
            user_id=owner_id,
            organization_id=req.organization_id,
            workspace_type=req.workspace_type,
            project_name=req.project_name.strip(),
            project_domain=req.project_domain or "general",
            ai_invocation="@AI",
        )
        db.add(ws)
        db.flush()
        if req.workspace_type not in ("personal_brainstorm",) and WorkspaceMember is not None:
            db.add(WorkspaceMember(
                workspace_id=ws.id,
                user_id=user.id,
                added_by=user.id,
            ))
        db.commit()
        db.refresh(ws)
        return _serialize(db, ws)
    finally:
        db.close()


@router.get("/{room_id}")
async def get_room(room_id: str, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        ws = db.query(Workspace).filter(Workspace.id == room_id).first()
        if ws is None:
            raise HTTPException(404, "room not found")
        if not _is_member(db, ws, user.id):
            raise HTTPException(403, "not a member")
        return _serialize(db, ws)
    finally:
        db.close()


@router.patch("/{room_id}")
async def rename_room(room_id: str, req: RenameRoomReq, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        ws = db.query(Workspace).filter(Workspace.id == room_id).first()
        if ws is None:
            raise HTTPException(404, "room not found")
        if not _is_member(db, ws, user.id):
            raise HTTPException(403, "not a member")
        if ws.user_id != user.id:
            role = _role_for(db, user, ws.organization_id)
            if role not in {ROLE_CEO, ROLE_HR, ROLE_DEPT_HEAD, ROLE_MANAGER}:
                raise HTTPException(403, "role cannot rename this room")
        if req.project_name is not None:
            ws.project_name = req.project_name.strip()
        if req.project_domain is not None:
            ws.project_domain = req.project_domain
        ws.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ws)
        return _serialize(db, ws)
    finally:
        db.close()


@router.delete("/{room_id}")
async def delete_room(room_id: str, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        ws = db.query(Workspace).filter(Workspace.id == room_id).first()
        if ws is None:
            raise HTTPException(404, "room not found")
        if ws.user_id != user.id:
            role = _role_for(db, user, ws.organization_id)
            if role not in {ROLE_CEO, ROLE_HR}:
                raise HTTPException(403, "only owner/CEO/HR can delete this room")
        if hasattr(Workspace, "deleted_at"):
            ws.deleted_at = datetime.utcnow()
        else:
            db.delete(ws)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.get("/{room_id}/members")
async def list_members(room_id: str, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        ws = db.query(Workspace).filter(Workspace.id == room_id).first()
        if ws is None:
            raise HTTPException(404, "room not found")
        if not _is_member(db, ws, user.id):
            raise HTTPException(403, "not a member")
        members: List[Dict[str, Any]] = []
        if ws.user_id is not None:
            owner = db.query(User).filter(User.id == ws.user_id).first()
            if owner:
                members.append({
                    "user_id": str(owner.id),
                    "phone": owner.phone,
                    "full_name": owner.full_name,
                    "role": "owner",
                    "added_at": ws.created_at.isoformat() if ws.created_at else None,
                })
        if WorkspaceMember is not None:
            for r in db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == ws.id,
                WorkspaceMember.removed_at.is_(None),
            ).all():
                u = db.query(User).filter(User.id == r.user_id).first()
                if u:
                    members.append({
                        "user_id": str(u.id),
                        "phone": u.phone,
                        "full_name": u.full_name,
                        "role": "member",
                        "added_at": r.added_at.isoformat() if r.added_at else None,
                    })
        return members
    finally:
        db.close()


@router.post("/{room_id}/members")
async def invite_member(room_id: str, req: InviteMemberReq, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        ws = db.query(Workspace).filter(Workspace.id == room_id).first()
        if ws is None:
            raise HTTPException(404, "room not found")
        if not _is_member(db, ws, user.id):
            raise HTTPException(403, "not a member")
        if ws.workspace_type == "personal_brainstorm":
            raise HTTPException(400, "personal brainstorm is private; create a group instead")
        if WorkspaceMember is None:
            raise HTTPException(500, "membership table not available")
        # PHONE-NORM
        candidates = variants(req.phone) or [req.phone]
        target = db.query(User).filter(User.phone.in_(candidates)).first()
        if target is None:
            raise HTTPException(404, "no user with that phone")
        existing = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.user_id == target.id,
        ).first()
        if existing:
            if existing.removed_at is None:
                return {"ok": True, "already_member": True}
            existing.removed_at = None
            existing.removed_by = None
            existing.added_by = user.id
            existing.added_at = datetime.utcnow()
        else:
            db.add(WorkspaceMember(
                workspace_id=ws.id,
                user_id=target.id,
                added_by=user.id,
            ))
        db.commit()
        return {"ok": True, "invited": target.phone}
    finally:
        db.close()


@router.delete("/{room_id}/members/{phone}")
async def remove_member(room_id: str, phone: str, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        ws = db.query(Workspace).filter(Workspace.id == room_id).first()
        if ws is None:
            raise HTTPException(404, "room not found")
        role = _role_for(db, user, ws.organization_id)
        if not (ws.user_id == user.id or role in {ROLE_CEO, ROLE_HR, ROLE_DEPT_HEAD, ROLE_MANAGER}):
            raise HTTPException(403, "role cannot remove members")
        if WorkspaceMember is None:
            raise HTTPException(500, "membership table not available")
        target = db.query(User).filter(User.phone == phone).first()
        if target is None:
            raise HTTPException(404, "no user with that phone")
        m = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.user_id == target.id,
            WorkspaceMember.removed_at.is_(None),
        ).first()
        if m is None:
            raise HTTPException(404, "not a member")
        m.removed_at = datetime.utcnow()
        m.removed_by = user.id
        db.commit()
        return {"ok": True, "removed": target.phone}
    finally:
        db.close()


@router.get("/{room_id}/messages")
async def list_messages(
    room_id: str,
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        ws = db.query(Workspace).filter(Workspace.id == room_id).first()
        if ws is None:
            raise HTTPException(404, "room not found")
        if not _is_member(db, ws, user.id):
            raise HTTPException(403, "not a member")
        rows = (
            db.query(Message)
            .filter(Message.workspace_id == ws.id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )
        return [{
            "id": str(m.id),
            "user_id": str(m.user_id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        } for m in reversed(rows)]
    finally:
        db.close()


@router.post("/{room_id}/messages")
async def send_message_to_room(
    room_id: str,
    req: SendMessageReq,
    user: User = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        ws = db.query(Workspace).filter(Workspace.id == room_id).first()
        if ws is None:
            raise HTTPException(404, "room not found")
        if not _is_member(db, ws, user.id):
            raise HTTPException(403, "not a member")
        content = req.content.strip()
        if not content:
            raise HTTPException(400, "content is required")

        # MSG-PERSIST
        import uuid as _uuid
        try:
            ws_uuid = _uuid.UUID(str(ws.id)) if not isinstance(ws.id, _uuid.UUID) else ws.id
            usr_uuid = _uuid.UUID(str(user.id)) if not isinstance(user.id, _uuid.UUID) else user.id
        except Exception as e:
            print(f"[rooms] uuid parse error: {e}")
            ws_uuid = ws.id
            usr_uuid = user.id

        msg = Message(
            workspace_id=ws_uuid,
            user_id=usr_uuid,
            role="user",
            content=content,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        print(f"[rooms] stored message {msg.id} in room {ws_uuid}")

        # TYPE-TRIGGER: personal_brainstorm = solo (always fire)
        # every other type (group/department/team/meeting/organization)
        # always requires @AI, regardless of how many members there are
        member_count = 1 if ws.workspace_type == "personal_brainstorm" else 2
        ai_invoked = False
        frames: List[str] = []
        try:
            from integration import handle_generate

            def _gen(prompt):
                try:
                    from main import generate_from_prompt
                    return generate_from_prompt(prompt, 128, 0.7)
                except Exception:
                    return prompt

            out = handle_generate(
                workspace_id=str(ws.id),
                user_id=user.phone or str(user.id),
                prompt=content,
                member_count=member_count,
                generate_fn=_gen,
            )
            ai_invoked = bool(out.get("ai_invoked"))
            frames = out.get("frames") or []
        except Exception as e:
            print(f"[rooms] pipeline error: {type(e).__name__}: {e}")

        return {
            "id": str(msg.id),
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "member_count": member_count,
            "ai_invoked": ai_invoked,
            "frames": frames,
        }
    finally:
        db.close()


# ============================================================================
# CANDIDATES — who can be added to this room
# ============================================================================

@router.get("/{room_id}/candidates")
async def room_candidates(room_id: str, user: User = Depends(get_current_user)):
    """Users who can be added to this room but aren't in it yet."""
    db = SessionLocal()
    try:
        ws = db.query(Workspace).filter(Workspace.id == room_id).first()
        if ws is None:
            raise HTTPException(404, "room not found")
        if not _is_member(db, ws, user.id):
            raise HTTPException(403, "not a member")

        member_ids = set()
        if ws.user_id is not None:
            member_ids.add(str(ws.user_id))
        if WorkspaceMember is not None:
            for r in db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == ws.id,
                WorkspaceMember.removed_at.is_(None),
            ).all():
                member_ids.add(str(r.user_id))

        out = []

        # ORG room -> org members
        if ws.organization_id is not None:
            try:
                from db_models import OrganizationMembership
                rows = db.query(OrganizationMembership).filter(
                    OrganizationMembership.organization_id == ws.organization_id,
                    OrganizationMembership.credential_active.is_(True),
                ).all()
                for m in rows:
                    uid = str(m.user_id)
                    if uid in member_ids:
                        continue
                    u = db.query(User).filter(User.id == m.user_id).first()
                    if u:
                        out.append({
                            "user_id": uid,
                            "full_name": u.full_name,
                            "phone": u.phone,
                            "role": m.role,
                            "department": getattr(m, "department", None),
                            "source": "org",
                        })
            except Exception as e:
                print(f"[candidates] org lookup error: {e}")

        # SOLO/GROUP -> contacts (DM partners)
        if not out:
            try:
                from db_models import DirectMessage
                from sqlalchemy import or_
                rows = db.query(DirectMessage).filter(
                    or_(DirectMessage.sender_phone == user.phone,
                        DirectMessage.recipient_phone == user.phone)
                ).all()
                seen = set()
                for r in rows:
                    partner = r.recipient_phone if r.sender_phone == user.phone else r.sender_phone
                    if partner in seen:
                        continue
                    seen.add(partner)
                    u = db.query(User).filter(User.phone == partner).first()
                    if u and str(u.id) not in member_ids:
                        out.append({
                            "user_id": str(u.id),
                            "full_name": u.full_name,
                            "phone": u.phone,
                            "source": "contact",
                        })
            except Exception as e:
                print(f"[candidates] contacts lookup error: {e}")

        dedup = {}
        for r in out:
            dedup[r["user_id"]] = r
        return {"candidates": list(dedup.values())}
    finally:
        db.close()


# ============================================================================
# CONTACT MATCH (phone book lookup)
# ============================================================================

contacts_router = APIRouter(prefix="/contacts", tags=["contacts"])


class MatchContactsReq(BaseModel):
    phones: List[str] = Field(default_factory=list)


@contacts_router.post("/match")
async def match_contacts(
    req: MatchContactsReq,
    user: User = Depends(get_current_user),
):
    """
    Given a list of phone numbers (from the client's contact list),
    return the subset that exist as Accodite users.

    Normalizes both directions so +234... and 0... forms match.
    """
    from phone_util import normalize_phone, variants
    db = SessionLocal()
    try:
        wanted = {}
        for raw in (req.phones or [])[:1000]:
            canon = normalize_phone(raw)
            if not canon:
                continue
            wanted[canon] = raw

        if not wanted:
            return {"matched": [], "count": 0}

        # gather all candidate forms and query once
        all_forms = set()
        for canon in wanted.keys():
            for v in variants(canon):
                all_forms.add(v)

        rows = db.query(User).filter(User.phone.in_(list(all_forms))).all()

        matched = []
        for row in rows:
            canon = normalize_phone(row.phone)
            matched.append({
                "phone": row.phone,
                "canonical": canon,
                "full_name": row.full_name,
                "user_id": str(row.id),
            })

        return {"matched": matched, "count": len(matched)}
    finally:
        db.close()


# ============================================================================
# CONTACT MATCH (phone book lookup)
# ============================================================================

contacts_router = APIRouter(prefix="/contacts", tags=["contacts"])


class MatchContactsReq(BaseModel):
    phones: List[str] = Field(default_factory=list)



# ============================================================================
# CONTACT SEARCH — by name or partial phone
# ============================================================================

@contacts_router.get("/search")
async def search_contacts(
    q: str,
    limit: int = 20,
    user: User = Depends(get_current_user),
):
    """
    Search for users to invite by:
        - name (full_name contains q, case-insensitive)
        - phone (normalized partial match)
    """
    from phone_util import normalize_phone, variants
    db = SessionLocal()
    try:
        q = (q or "").strip()
        if len(q) < 2:
            return {"results": []}

        results: Dict[str, Dict[str, Any]] = {}

        # name match
        name_rows = db.query(User).filter(
            User.full_name.ilike(f"%{q}%"),
            User.id != user.id,
        ).limit(limit).all()
        for r in name_rows:
            results[str(r.id)] = {
                "user_id": str(r.id),
                "full_name": r.full_name,
                "phone": r.phone,
            }

        # phone match
        if len(results) < limit:
            digits = "".join(c for c in q if c.isdigit())
            if digits:
                cand = variants(digits)
                phone_rows = db.query(User).filter(
                    User.phone.in_(cand),
                    User.id != user.id,
                ).limit(limit).all()
                for r in phone_rows:
                    results[str(r.id)] = {
                        "user_id": str(r.id),
                        "full_name": r.full_name,
                        "phone": r.phone,
                    }

        return {"results": list(results.values())[:limit]}
    finally:
        db.close()

"""
Accodite Org Rooms
==================
Org-scoped room creation. Completely separate from /rooms (solo/group).

Endpoint:
    POST /orgs/{org_id}/rooms    { workspace_type, name }

Authorization:
    - caller must be an active member of {org_id}
    - role must permit the requested workspace_type (see ROOM_ROLES)

Regular users create personal_brainstorm / group via /rooms instead.
"""
from __future__ import annotations
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database import SessionLocal
from db_models import User, Workspace, Organization, OrganizationMembership
from auth import get_current_user
from org.roles import (
    ROLE_CEO, ROLE_C_SUITE, ROLE_HR, ROLE_DEPT_HEAD, ROLE_MANAGER,
)

router = APIRouter(prefix="/orgs", tags=["org-rooms"])

ORG_ROOM_TYPES = {"department", "team", "meeting", "organization"}

# who can create what inside an org
ROOM_ROLES = {
    "department":   {ROLE_CEO, ROLE_C_SUITE, ROLE_HR, ROLE_DEPT_HEAD, ROLE_MANAGER},
    "team":         {ROLE_CEO, ROLE_C_SUITE, ROLE_DEPT_HEAD, ROLE_MANAGER},
    "meeting":      {ROLE_CEO, ROLE_C_SUITE, ROLE_HR, ROLE_DEPT_HEAD, ROLE_MANAGER},
    "organization": {ROLE_CEO, ROLE_C_SUITE},
}


class CreateOrgRoomReq(BaseModel):
    workspace_type: str = Field(..., min_length=2, max_length=40)
    name: str = Field(..., min_length=1, max_length=255)
    domain: str = "general"
    department: Optional[str] = None    # dept tag for scoping


def _membership(db, user_id, org_id):
    return db.query(OrganizationMembership).filter(
        OrganizationMembership.user_id == user_id,
        OrganizationMembership.organization_id == org_id,
        OrganizationMembership.credential_active.is_(True),
    ).first()


def _serialize(db, ws, org) -> Dict[str, Any]:
    n = 0
    if ws.user_id is not None:
        n += 1
    try:
        from db.models_org import WorkspaceMember
        n += db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.removed_at.is_(None),
        ).count()
    except Exception:
        pass
    return {
        "id": str(ws.id),
        "workspace_type": ws.workspace_type,
        "project_name": ws.project_name,
        "project_domain": ws.project_domain,
        "user_id": str(ws.user_id) if ws.user_id else None,
        "organization_id": str(ws.organization_id) if ws.organization_id else None,
        "org_name": org.name if org else None,
        "ai_invocation": getattr(ws, "ai_invocation", "@AI"),
        "member_count": max(n, 1),
        "created_at": ws.created_at.isoformat() if ws.created_at else None,
        "updated_at": ws.updated_at.isoformat() if ws.updated_at else None,
    }


@router.post("/{org_id}/rooms")
async def create_org_room(
    org_id: str,
    req: CreateOrgRoomReq,
    user: User = Depends(get_current_user),
):
    """Create a department / team / meeting / organization room inside an org."""
    db = SessionLocal()
    try:
        if req.workspace_type not in ORG_ROOM_TYPES:
            raise HTTPException(
                400,
                f"'{req.workspace_type}' is not an org room type — "
                "use POST /rooms for personal_brainstorm / group",
            )

        org = db.query(Organization).filter(Organization.id == org_id).first()
        if org is None:
            raise HTTPException(404, "organization not found")

        m = _membership(db, user.id, org_id)
        if m is None:
            raise HTTPException(403, "not an active member of this organization")

        allowed = ROOM_ROLES.get(req.workspace_type, set())
        if m.role not in allowed:
            raise HTTPException(
                403,
                f"role '{m.role}' cannot create '{req.workspace_type}' "
                f"(allowed: {sorted(allowed)})",
            )

        ws = Workspace(
            id=uuid.uuid4(),
            user_id=None,
            organization_id=org.id,
            workspace_type=req.workspace_type,
            project_name=req.name.strip(),
            project_domain=req.domain or "general",
            ai_invocation="@AI",
        )
        db.add(ws)
        db.flush()

        # creator becomes a member
        try:
            from db.models_org import WorkspaceMember
            db.add(WorkspaceMember(
                workspace_id=ws.id,
                user_id=user.id,
                added_by=user.id,
            ))
        except Exception as e:
            print(f"[org-rooms] membership insert skipped: {e}")

        db.commit()
        db.refresh(ws)
        return _serialize(db, ws, org)
    finally:
        db.close()


@router.get("/{org_id}/rooms")
async def list_org_rooms(
    org_id: str,
    workspace_type: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """List rooms in an org the caller is a member of."""
    db = SessionLocal()
    try:
        m = _membership(db, user.id, org_id)
        if m is None:
            raise HTTPException(403, "not an active member of this organization")

        q = db.query(Workspace).filter(
            Workspace.organization_id == org_id,
            Workspace.workspace_type.in_(list(ORG_ROOM_TYPES)),
        )
        if workspace_type:
            q = q.filter(Workspace.workspace_type == workspace_type)
        if hasattr(Workspace, "deleted_at"):
            q = q.filter(Workspace.deleted_at.is_(None))

        org = db.query(Organization).filter(Organization.id == org_id).first()
        return [_serialize(db, w, org) for w in q.all()]
    finally:
        db.close()

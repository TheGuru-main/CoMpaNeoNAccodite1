"""
Canonical ownership scope for DBase / CollabSheets / Presentations / attachments.

GSP places objects by name. Ownership decides storage partition + access.
Never mix room/org data into personal storage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class OwnershipScope:
    """Resolved ownership context — one object, one partition."""
    kind: str                 # room | org | team | department | user_personal | user_regular
    owner_id: str             # room_id | org_id | team_id | department_id | user_id
    phone_uid: str = ""       # placement/grid identity when available
    org_id: Optional[str] = None
    room_id: Optional[str] = None
    user_id: Optional[str] = None
    workspace_type: Optional[str] = None  # personal_brainstorm | department | team | …
    b2_prefix: str = ""
    neon_parent_type: str = "user"
    neon_parent_id: str = ""
    audit_actor_id: Optional[str] = None  # worker who acted (not storage owner)

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "owner_id": self.owner_id,
            "phone_uid": self.phone_uid,
            "org_id": self.org_id,
            "room_id": self.room_id,
            "user_id": self.user_id,
            "workspace_type": self.workspace_type,
            "b2_prefix": self.b2_prefix,
            "neon_parent_type": self.neon_parent_type,
            "neon_parent_id": self.neon_parent_id,
            "audit_actor_id": self.audit_actor_id,
        }


class ScopeError(PermissionError):
    pass


def _phone(user) -> str:
    try:
        from memory.owner_identity import phone_uid
        return phone_uid(getattr(user, "phone", None)) or str(getattr(user, "id", "") or "")
    except Exception:
        return str(getattr(user, "id", "") or "")


def _b2_prefix(kind: str, owner_id: str, surface: str = "dbase") -> str:
    """
    Logical layout (adapted to existing ACCD_B2_PREFIX):
      accodite/rooms/{room_id}/dbase/
      accodite/organisations/{org_id}/collabsheets/
      accodite/users/{user_id}/personal/brainstorm/dbase/
      accodite/users/{user_id}/regular/dbase/
      accodite/organisations/{org_id}/teams/{team_id}/presentations/
    """
    oid = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(owner_id))[:96]
    surface = (surface or "dbase").strip("/").lower()
    if kind == "room":
        return f"rooms/{oid}/{surface}"
    if kind == "org":
        return f"organisations/{oid}/{surface}"
    if kind == "team":
        return f"organisations/{oid}/teams/{surface}"  # owner_id may encode team
    if kind == "department":
        return f"organisations/{oid}/departments/{surface}"
    if kind == "user_personal":
        return f"users/{oid}/personal/brainstorm/{surface}"
    if kind == "user_regular":
        return f"users/{oid}/regular/{surface}"
    return f"users/{oid}/{surface}"


def resolve_ownership(
    *,
    user,
    surface: str = "dbase",  # dbase | collabsheet | presentations | sheets
    room_id: Optional[str] = None,
    org_id: Optional[str] = None,
    team_id: Optional[str] = None,
    department_id: Optional[str] = None,
    workspace_type: Optional[str] = None,
    require: bool = True,
) -> OwnershipScope:
    """
    Authoritative scope for create/list/open/save/upload.
    Validates membership before accepting client-supplied room/org ids.
    """
    if user is None:
        raise ScopeError("authentication required")

    uid = str(getattr(user, "id", "") or "")
    phone = _phone(user)
    actor = uid
    wt = (workspace_type or "").strip().lower()
    surface = (surface or "dbase").lower()
    if surface in ("xlsx", "excel"):
        surface = "dbase"
    if surface in ("pptx", "pres"):
        surface = "presentations"
    if surface in ("workspace", "collab"):
        surface = "collabsheet"

    # --- Room-scoped (room DBase / room presentations) ---
    if room_id:
        room_id = str(room_id)
        _assert_room_member(user, room_id)
        # Detect personal brainstorm vs regular room via workspace row if possible
        wt_room, org_from_room = _workspace_meta(room_id)
        if wt_room:
            wt = wt_room
        if org_from_room and not org_id:
            org_id = org_from_room

        if wt == "personal_brainstorm":
            kind = "user_personal"
            owner = uid
            prefix = _b2_prefix(kind, owner, surface)
            return OwnershipScope(
                kind=kind, owner_id=owner, phone_uid=phone, user_id=uid,
                room_id=room_id, workspace_type=wt, b2_prefix=prefix,
                neon_parent_type="room", neon_parent_id=room_id, audit_actor_id=actor,
            )

        if org_from_room or org_id:
            # Org room → still room partition for room DBase; collabsheet is org-level
            if surface == "collabsheet":
                oid = str(org_from_room or org_id)
                _assert_org_member(user, oid)
                prefix = _b2_prefix("org", oid, "collabsheets")
                return OwnershipScope(
                    kind="org", owner_id=oid, phone_uid=phone, org_id=oid,
                    room_id=room_id, user_id=uid, workspace_type=wt, b2_prefix=prefix,
                    neon_parent_type="org", neon_parent_id=oid, audit_actor_id=actor,
                )
            prefix = _b2_prefix("room", room_id, surface)
            return OwnershipScope(
                kind="room", owner_id=room_id, phone_uid=phone, org_id=org_from_room or org_id,
                room_id=room_id, user_id=uid, workspace_type=wt, b2_prefix=prefix,
                neon_parent_type="room", neon_parent_id=room_id, audit_actor_id=actor,
            )

        # Regular / group room without org
        if surface in ("dbase", "sheets", "presentations"):
            prefix = _b2_prefix("room", room_id, surface)
            return OwnershipScope(
                kind="room", owner_id=room_id, phone_uid=phone,
                room_id=room_id, user_id=uid, workspace_type=wt or "group", b2_prefix=prefix,
                neon_parent_type="room", neon_parent_id=room_id, audit_actor_id=actor,
            )

    # --- Team / department presentations ---
    if team_id and surface == "presentations":
        team_id = str(team_id)
        org_for_team = org_id or _org_for_workspace(team_id)
        if org_for_team:
            _assert_org_member(user, str(org_for_team))
        prefix = _b2_prefix("team", f"{org_for_team or 'org'}/{team_id}", "presentations")
        return OwnershipScope(
            kind="team", owner_id=team_id, phone_uid=phone, org_id=org_for_team,
            user_id=uid, workspace_type="team", b2_prefix=prefix,
            neon_parent_type="team", neon_parent_id=team_id, audit_actor_id=actor,
        )

    if department_id and surface == "presentations":
        department_id = str(department_id)
        org_for_dept = org_id or _org_for_workspace(department_id)
        if org_for_dept:
            _assert_org_member(user, str(org_for_dept))
        prefix = _b2_prefix("department", f"{org_for_dept or 'org'}/{department_id}", "presentations")
        return OwnershipScope(
            kind="department", owner_id=department_id, phone_uid=phone, org_id=org_for_dept,
            user_id=uid, workspace_type="department", b2_prefix=prefix,
            neon_parent_type="department", neon_parent_id=department_id, audit_actor_id=actor,
        )

    # --- Org CollabSheets (no room required) ---
    if org_id and surface == "collabsheet":
        org_id = str(org_id)
        _assert_org_member(user, org_id)
        prefix = _b2_prefix("org", org_id, "collabsheets")
        return OwnershipScope(
            kind="org", owner_id=org_id, phone_uid=phone, org_id=org_id,
            user_id=uid, b2_prefix=prefix,
            neon_parent_type="org", neon_parent_id=org_id, audit_actor_id=actor,
        )

    if org_id and surface == "presentations":
        org_id = str(org_id)
        _assert_org_member(user, org_id)
        prefix = _b2_prefix("org", org_id, "presentations")
        return OwnershipScope(
            kind="org", owner_id=org_id, phone_uid=phone, org_id=org_id,
            user_id=uid, b2_prefix=prefix,
            neon_parent_type="org", neon_parent_id=org_id, audit_actor_id=actor,
        )

    # --- Default: personal / regular user partition ---
    acct = str(getattr(user, "account_type", "regular") or "regular").lower()
    if acct == "worker":
        # Worker with no room/org context cannot write personal collab — need org
        if surface == "collabsheet":
            if require:
                raise ScopeError("CollabSheets require an organisation context for workers")
        # workers may still have personal presentations only if allowed
        kind = "user_regular"
    elif wt == "personal_brainstorm" or surface == "dbase" and acct == "personal":
        kind = "user_personal"
    else:
        kind = "user_personal" if acct in ("personal",) else "user_regular"

    prefix = _b2_prefix(kind, uid, surface)
    return OwnershipScope(
        kind=kind, owner_id=uid, phone_uid=phone, user_id=uid,
        workspace_type=wt or None, b2_prefix=prefix,
        neon_parent_type="user", neon_parent_id=uid, audit_actor_id=actor,
    )


def _assert_room_member(user, room_id: str) -> None:
    try:
        from database import SessionLocal
        from db_models import Workspace
        db = SessionLocal()
        try:
            ws = db.query(Workspace).filter(Workspace.id == room_id).first()
            if ws is None:
                raise ScopeError("room not found")
            # owner
            if str(getattr(ws, "user_id", "")) == str(user.id):
                return
            try:
                from db.models_org import WorkspaceMember
            except Exception:
                try:
                    from models_org import WorkspaceMember
                except Exception:
                    WorkspaceMember = None
            if WorkspaceMember is not None:
                m = db.query(WorkspaceMember).filter(
                    WorkspaceMember.workspace_id == ws.id,
                    WorkspaceMember.user_id == user.id,
                    WorkspaceMember.removed_at.is_(None),
                ).first()
                if m:
                    return
            raise ScopeError("not a member of this room")
        finally:
            db.close()
    except ScopeError:
        raise
    except Exception as e:
        raise ScopeError(f"room access check failed: {e}") from e


def _assert_org_member(user, org_id: str) -> None:
    try:
        from database import SessionLocal
        from db_models import OrganizationMembership
        db = SessionLocal()
        try:
            m = db.query(OrganizationMembership).filter(
                OrganizationMembership.organization_id == org_id,
                OrganizationMembership.user_id == user.id,
            ).first()
            if not m:
                raise ScopeError("not a member of this organisation")
            if hasattr(m, "credential_active") and not m.credential_active:
                # pending workers: read-only policies can be layered later
                pass
            return
        finally:
            db.close()
    except ScopeError:
        raise
    except Exception as e:
        raise ScopeError(f"org access check failed: {e}") from e


def _workspace_meta(room_id: str):
    try:
        from database import SessionLocal
        from db_models import Workspace
        db = SessionLocal()
        try:
            ws = db.query(Workspace).filter(Workspace.id == room_id).first()
            if not ws:
                return None, None
            wt = getattr(ws, "workspace_type", None)
            org = getattr(ws, "organization_id", None)
            return (str(wt).lower() if wt else None), (str(org) if org else None)
        finally:
            db.close()
    except Exception:
        return None, None


def _org_for_workspace(ws_id: str):
    _, org = _workspace_meta(ws_id)
    return org

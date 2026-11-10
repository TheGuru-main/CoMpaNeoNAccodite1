"""
Canonical ownership for DBase / CollabSheets / Presentations / attachments / grids.

Parent owners (MemoryGrid + B2 instance partition) — ONLY:
  user:<user_phone_uid>
  org:<org_phone_uid>

Rooms, teams, departments are namespaces *inside* the owner grid.
SQL UUIDs are relational / audit only — never grid owner identity.
GSP places objects by name; ownership chooses the parent grid.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class OwnershipScope:
    """Resolved ownership — one parent grid partition."""

    kind: str  # "user" | "org" only
    owner_id: str  # normalized phone UID (grid key id, no prefix)
    phone_uid: str = ""  # same as owner_id for parent
    org_id: Optional[str] = None  # SQL UUID when kind=org (FK / membership)
    room_id: Optional[str] = None  # namespace metadata
    user_id: Optional[str] = None  # SQL UUID of actor
    team_id: Optional[str] = None
    department_id: Optional[str] = None
    workspace_type: Optional[str] = None
    namespace: Optional[str] = None  # dbase | sheets | collabsheet | presentations | room | …
    b2_prefix: str = ""
    neon_parent_type: str = "user"  # user | org  (not room/team)
    neon_parent_id: str = ""  # phone UID for uniqueness boundary
    audit_actor_id: Optional[str] = None

    @property
    def owner_key(self) -> str:
        return f"{self.kind}:{self.owner_id}"

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "owner_id": self.owner_id,
            "owner_key": self.owner_key,
            "phone_uid": self.phone_uid or self.owner_id,
            "org_id": self.org_id,
            "room_id": self.room_id,
            "user_id": self.user_id,
            "team_id": self.team_id,
            "department_id": self.department_id,
            "workspace_type": self.workspace_type,
            "namespace": self.namespace,
            "b2_prefix": self.b2_prefix,
            "neon_parent_type": self.neon_parent_type,
            "neon_parent_id": self.neon_parent_id,
            "audit_actor_id": self.audit_actor_id,
        }


class ScopeError(PermissionError):
    pass


def _phone_from_user(user) -> str:
    if user is None:
        return ""
    try:
        from memory.owner_identity import phone_uid
        p = phone_uid(getattr(user, "phone", None))
        if p:
            return p
    except Exception:
        pass
    # Do NOT fall back to SQL UUID — phone is required for grid ownership
    return ""


def _org_phone(org_id: Optional[str] = None, org=None) -> str:
    try:
        from memory.owner_identity import resolve_org_phone, phone_uid
        if org is not None:
            return phone_uid(getattr(org, "phone", None)) or ""
        if org_id:
            return resolve_org_phone(org_id=org_id) or ""
    except Exception as e:
        print("[ownership_scope] org phone:", type(e).__name__, e)
    return ""


def _b2_prefix(kind: str, phone: str, surface: str = "dbase") -> str:
    """
    Align with b2_grid_layout instance partitions + surface for docs/media:

      grids/instances/user/{phone}/docs/{surface}/
      grids/instances/org/{phone}/docs/{surface}/
    """
    ph = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(phone or ""))[:64]
    if not ph:
        raise ScopeError("phone UID required for B2 prefix")
    kind = "org" if kind == "org" else "user"
    surface = (surface or "dbase").strip("/").lower() or "dbase"
    return f"grids/instances/{kind}/{ph}/docs/{surface}"


def _require_org_member(user_id: str, org_id: str) -> None:
    if not user_id or not org_id:
        raise ScopeError("organisation access requires user_id and org_id")
    try:
        from memory.membership_access import is_active_member
        if not is_active_member(str(user_id), str(org_id)):
            raise ScopeError("not an active organisation member")
        return
    except ScopeError:
        raise
    except Exception as e:
        # Fail closed — do not use a soft pass on credential_active
        raise ScopeError(f"membership check failed: {e}") from e


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


def resolve_ownership(
    *,
    user=None,
    room_id: Optional[str] = None,
    org_id: Optional[str] = None,
    team_id: Optional[str] = None,
    department_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    surface: str = "dbase",
    explicit_kind: Optional[str] = None,
) -> OwnershipScope:
    """
    Resolve the parent MemoryGrid owner for this request.

    Returns kind in {"user", "org"} only.
    room_id / team_id / department_id are recorded as namespace metadata.
    """
    uid = str(getattr(user, "id", "") or "") if user is not None else ""
    actor_phone = _phone_from_user(user)
    audit = uid or None
    surface = (surface or "dbase").strip().lower()
    room_id = room_id or workspace_id

    # --- Explicit organisation context (API org_id or org workspace) ---
    effective_org = org_id
    wt = None
    if room_id and not effective_org:
        wt, org_from_room = _workspace_meta(str(room_id))
        if org_from_room:
            effective_org = str(org_from_room)

    if effective_org or (explicit_kind == "org"):
        if not effective_org:
            raise ScopeError("organisation context required")
        if not uid:
            raise ScopeError("authenticated user required for organisation resources")
        _require_org_member(uid, str(effective_org))
        org_phone = _org_phone(org_id=str(effective_org))
        if not org_phone:
            raise ScopeError("organisation phone UID unresolved — cannot bind org grid")
        ns = surface
        if room_id:
            ns = f"room:{room_id}"
        elif team_id:
            ns = f"team:{team_id}"
        elif department_id:
            ns = f"department:{department_id}"
        return OwnershipScope(
            kind="org",
            owner_id=org_phone,
            phone_uid=org_phone,
            org_id=str(effective_org),
            room_id=str(room_id) if room_id else None,
            user_id=uid or None,
            team_id=str(team_id) if team_id else None,
            department_id=str(department_id) if department_id else None,
            workspace_type=wt,
            namespace=ns,
            b2_prefix=_b2_prefix("org", org_phone, surface),
            neon_parent_type="org",
            neon_parent_id=org_phone,
            audit_actor_id=audit,
        )

    # --- Personal user grid ---
    if not actor_phone:
        raise ScopeError("user phone UID required for personal grid ownership")
    ns = surface
    if room_id:
        ns = f"room:{room_id}"
    return OwnershipScope(
        kind="user",
        owner_id=actor_phone,
        phone_uid=actor_phone,
        org_id=None,
        room_id=str(room_id) if room_id else None,
        user_id=uid or None,
        team_id=str(team_id) if team_id else None,
        department_id=str(department_id) if department_id else None,
        workspace_type=wt or "personal",
        namespace=ns,
        b2_prefix=_b2_prefix("user", actor_phone, surface),
        neon_parent_type="user",
        neon_parent_id=actor_phone,
        audit_actor_id=audit,
    )


def owner_ref_from_scope(scope: OwnershipScope):
    """Map to instance_grid.OwnerRef for bind/persist."""
    from memory.instance_grid import OwnerRef
    return OwnerRef(scope.kind, scope.owner_id)

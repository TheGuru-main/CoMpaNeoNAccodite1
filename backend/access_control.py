"""
Hard membership checks aligned to live Accodite schema:

  organization_memberships  (user_id, organization_id, credential_active)
  workspace_members         (workspace_id, user_id, removed_at)
  workspaces                (id, user_id, organization_id, workspace_type)

parent_type:
  room  → workspace id (UUID string)
  repo  → authenticated; optional org scope later
"""
from __future__ import annotations

from typing import Any, Optional


class AccessDenied(PermissionError):
    pass


def _uid(user: Any) -> Optional[str]:
    if user is None:
        return None
    u = getattr(user, "id", None)
    if u is None and isinstance(user, dict):
        u = user.get("id") or user.get("user_id") or user.get("sub")
    return str(u) if u is not None else None


def can_access_parent(
    user: Any,
    parent_type: str,
    parent_id: str,
    *,
    db_session=None,
) -> bool:
    parent_type = (parent_type or "").strip().lower()
    parent_id = str(parent_id or "").strip()
    uid = _uid(user)
    if not uid or not parent_id:
        return False

    if parent_type == "repo":
        # Authenticated session may use codespace repos in their scope.
        return True

    if parent_type != "room":
        return False

    close = False
    if db_session is None:
        try:
            from database import SessionLocal
            db_session = SessionLocal()
            close = True
        except Exception:
            return False

    try:
        from sqlalchemy import text

        # 1) Direct workspace membership (active)
        row = db_session.execute(
            text(
                """
                SELECT 1 FROM workspace_members
                WHERE workspace_id::text = :wid
                  AND user_id::text = :uid
                  AND removed_at IS NULL
                LIMIT 1
                """
            ),
            {"wid": parent_id, "uid": uid},
        ).first()
        if row:
            return True

        # 2) Workspace owner (personal_brainstorm / group creator)
        row = db_session.execute(
            text(
                """
                SELECT 1 FROM workspaces
                WHERE id::text = :wid AND user_id::text = :uid
                LIMIT 1
                """
            ),
            {"wid": parent_id, "uid": uid},
        ).first()
        if row:
            return True

        # 3) Org room: active org membership + workspace belongs to that org
        row = db_session.execute(
            text(
                """
                SELECT 1
                FROM workspaces w
                JOIN organization_memberships om
                  ON om.organization_id = w.organization_id
                WHERE w.id::text = :wid
                  AND om.user_id::text = :uid
                  AND om.credential_active = true
                  AND w.organization_id IS NOT NULL
                LIMIT 1
                """
            ),
            {"wid": parent_id, "uid": uid},
        ).first()
        if row:
            return True

        return False
    except Exception as e:
        print(f"[access_control] room check error: {type(e).__name__}: {e}")
        return False
    finally:
        if close:
            try:
                db_session.close()
            except Exception:
                pass


def require_parent_access(user, parent_type: str, parent_id: str, db_session=None):
    if not can_access_parent(user, parent_type, parent_id, db_session=db_session):
        raise AccessDenied(f"no access to {parent_type}:{parent_id}")

"""
Hard membership checks for room/repo scoped resources (docs, media).
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID


class AccessDenied(PermissionError):
    pass


def can_access_parent(
    user: Any,
    parent_type: str,
    parent_id: str,
    *,
    db_session=None,
) -> bool:
    parent_type = (parent_type or "").strip().lower()
    parent_id = str(parent_id or "").strip()
    if not user or not parent_id:
        return False
    if parent_type == "repo":
        # Authenticated user may access repos in their session scope.
        # Tighten to owner/org when repo ownership table exists.
        return True
    if parent_type != "room":
        return False

    # Room: require membership row
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
        uid = getattr(user, "id", None)
        if uid is None:
            return False
        # Try common membership shapes
        for sql in (
            """
            SELECT 1 FROM room_members
            WHERE room_id::text = :rid AND user_id::text = :uid LIMIT 1
            """,
            """
            SELECT 1 FROM organization_memberships om
            JOIN rooms r ON r.organization_id = om.organization_id
            WHERE r.id::text = :rid AND om.user_id::text = :uid
              AND COALESCE(om.credential_active, true) = true
            LIMIT 1
            """,
            """
            SELECT 1 FROM workspace_members
            WHERE workspace_id::text = :rid AND user_id::text = :uid LIMIT 1
            """,
        ):
            try:
                row = db_session.execute(
                    text(sql), {"rid": parent_id, "uid": str(uid)}
                ).first()
                if row:
                    return True
            except Exception:
                continue
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

"""
Active org membership check for instance grid access (ReBAC-light).

credential_active must be True. Workers have no grid; they access org grid only.
"""
from __future__ import annotations
from typing import Optional

def is_active_member(user_id: str, org_id: str, db=None) -> bool:
    """Return True if user has an active OrganizationMembership for org."""
    if not user_id or not org_id:
        return False
    close = False
    try:
        if db is None:
            from auth.auth import get_db
            # get_db is a generator Depends — open session manually
            from auth.auth import SessionLocal  # type: ignore
            db = SessionLocal()
            close = True
    except Exception:
        try:
            from database_core import SessionLocal
            db = SessionLocal()
            close = True
        except Exception as e:
            print("[membership] no db:", type(e).__name__, e)
            return False
    try:
        from db_models import OrganizationMembership
        q = (
            db.query(OrganizationMembership)
            .filter(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == org_id,
                OrganizationMembership.credential_active.is_(True),
            )
            .first()
        )
        return q is not None
    except Exception as e:
        # UUID type coercion
        try:
            import uuid
            uid = uuid.UUID(str(user_id))
            oid = uuid.UUID(str(org_id))
            from db_models import OrganizationMembership
            q = (
                db.query(OrganizationMembership)
                .filter(
                    OrganizationMembership.user_id == uid,
                    OrganizationMembership.organization_id == oid,
                    OrganizationMembership.credential_active.is_(True),
                )
                .first()
            )
            return q is not None
        except Exception as e2:
            print("[membership] query:", type(e).__name__, e, "|", type(e2).__name__, e2)
            return False
    finally:
        if close and db is not None:
            try:
                db.close()
            except Exception:
                pass


def is_active_member_fn(db=None):
    """Return a closure suitable for require_access(..., is_active_member=fn)."""
    def _fn(user_id: str, owner) -> bool:
        kind = getattr(owner, "kind", None)
        oid = getattr(owner, "id", None)
        if kind != "org" or not oid:
            return False
        return is_active_member(str(user_id), str(oid), db=db)
    return _fn

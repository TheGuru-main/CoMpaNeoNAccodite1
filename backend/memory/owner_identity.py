"""
Canonical owner identity for grids and placement.

Phone UID (normalized) is the authority for:
  - instance grid keys  org:<phone_uid> | user:<phone_uid>
  - GSP placement identity (placement S from phone digits — not token S)
  - org–worker credential spine (org phone UID)

DB UUID is support only (FK, JWT sub lookup).

Workers: no org grid ownership; no org-level start_row ownership.
Worker message box uses their own phone + start_row (message path).
"""
from __future__ import annotations
from typing import Any, Optional, Tuple

try:
    from phone_util import normalize_phone
except ImportError:
    def normalize_phone(p, default_country="NG"):
        return (p or "").strip()


def phone_uid(phone: Optional[str], default_country: str = "NG") -> str:
    return normalize_phone(phone, default_country=default_country) or ""


def owner_key_org(org_phone: str) -> str:
    p = phone_uid(org_phone)
    if not p:
        raise ValueError("org phone UID required")
    return f"org:{p}"


def owner_key_user(user_phone: str) -> str:
    p = phone_uid(user_phone)
    if not p:
        raise ValueError("user phone UID required")
    return f"user:{p}"


def resolve_user_phone(user=None, user_id=None, db=None) -> str:
    if user is not None:
        return phone_uid(getattr(user, "phone", None))
    if not user_id:
        return ""
    close = False
    try:
        if db is None:
            try:
                from database import SessionLocal
            except ImportError:
                from database_core import SessionLocal
            db = SessionLocal()
            close = True
        from db_models import User
        import uuid
        try:
            u = db.query(User).filter(User.id == uuid.UUID(str(user_id))).first()
        except Exception:
            u = db.query(User).filter(User.id == user_id).first()
        return phone_uid(getattr(u, "phone", None)) if u else ""
    except Exception as e:
        print("[owner_identity] resolve_user_phone:", type(e).__name__, e)
        return ""
    finally:
        if close and db is not None:
            try:
                db.close()
            except Exception:
                pass


def resolve_org_phone(org_id=None, org=None, db=None) -> str:
    if org is not None:
        return phone_uid(getattr(org, "phone", None))
    if not org_id:
        return ""
    close = False
    try:
        if db is None:
            try:
                from database import SessionLocal
            except ImportError:
                from database_core import SessionLocal
            db = SessionLocal()
            close = True
        from db_models import Organization
        import uuid
        try:
            o = db.query(Organization).filter(Organization.id == uuid.UUID(str(org_id))).first()
        except Exception:
            o = db.query(Organization).filter(Organization.id == org_id).first()
        return phone_uid(getattr(o, "phone", None)) if o else ""
    except Exception as e:
        print("[owner_identity] resolve_org_phone:", type(e).__name__, e)
        return ""
    finally:
        if close and db is not None:
            try:
                db.close()
            except Exception:
                pass


def message_box_coords(user) -> Tuple[Optional[int], Optional[int]]:
    """Worker/personal message box: start_row, start_col from account placement."""
    if user is None:
        return None, None
    return getattr(user, "start_row", None), getattr(user, "start_col", None)

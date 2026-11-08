import os
import re
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt  # PyJWT
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import SessionLocal
from db_models import User

def _resolve_secret_key() -> str:
    """Single source for JWT signing/validation. No weak production defaults."""
    key = (os.getenv("SECRET_KEY") or os.getenv("ACCD_SECRET_KEY") or "").strip()
    env = (os.getenv("ENV") or os.getenv("ACCD_ENV") or os.getenv("APP_ENV") or "development").strip().lower()
    if key and key not in ("your-secret-key", "change-me", "secret", "changeme"):
        return key
    if env in ("production", "prod", "staging"):
        raise RuntimeError(
            "SECRET_KEY must be set to a strong value in production "
            "(refusing insecure JWT fallback)"
        )
    # development only — unstable across restarts by design unless SECRET_KEY set
    import warnings
    warnings.warn(
        "SECRET_KEY not set; using ephemeral development secret. "
        "Set SECRET_KEY before any shared/staging/production deploy.",
        stacklevel=2,
    )
    return "accd-dev-only-insecure-key"

SECRET_KEY = _resolve_secret_key()
ALGORITHM = "HS256"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(user_id: str):
    # PyJWT prefers aware datetimes (UTC) to avoid deprecation warnings
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def validate_phone(phone: str, country_code: str = "NG") -> bool:
    """Validate phone number: starts with '+', no leading zero after '+', correct length."""
    if not phone.startswith("+"):
        return False
    digits = phone[1:]
    if digits.startswith("0"):
        return False
    lengths = {
        "NG": 13,   # +234 + 10 digits = 13 digits total after '+'
        "GH": 12,   # +233 + 9 digits
        "US": 11,   # +1 + 10 digits
        "IN": 12,   # +91 + 10 digits
        "GB": 12,   # +44 + 10 digits
    }
    expected = lengths.get(country_code, None)
    if expected is not None and len(digits) != expected:
        return False
    return True

def compute_user_cell(full_name: str, phone: str):
    """
    User message-box placement (signup / rooms).

    S = digit sum of phone UID (placement S).
    lang = detect(full_name); C = language alphabet length (26 for en;
          only 54 when alphabet reaches 54).
    start_col = first_letter_index(lang) % C
    start_row = ((L + S - 1) % 64) + 1
    """
    try:
        from gsp_chain import (
            detect_placement_lang,
            col_for_name,
            effective_col_modulus,
        )
        lang = detect_placement_lang(full_name or "", "auto")
        letters = [ch for ch in (full_name or "") if ch.isalpha()]
        L = max(len(letters), 1)
        S = sum(int(d) for d in (phone or "") if d.isdigit())
        col_info = col_for_name(full_name or "", lang)
        start_row = ((L + S - 1) % 64) + 1
        start_col = int(col_info["start_col"])
        return start_row, start_col
    except Exception:
        clean_name = re.sub(r"[^a-zA-Z]", "", full_name or "")
        L = max(len(clean_name), 1)
        S = sum(int(d) for d in (phone or "") if d.isdigit())
        c = ord(clean_name[0].lower()) - 97 if clean_name else 0
        if c < 0 or c > 25:
            c = 0
        start_row = ((L + S - 1) % 64) + 1
        start_col = c % 26  # English fallback band
        return start_row, start_col
    except Exception:
        clean_name = re.sub(r"[^a-zA-Z]", "", full_name or "")
        L = max(len(clean_name), 1)
        S = sum(int(d) for d in (phone or "") if d.isdigit())
        c = ord(clean_name[0].lower()) - 97 if clean_name else 0
        if c < 0 or c > 25:
            c = 0
        start_row = ((L + S - 1) % 64) + 1
        start_col = c % 54
        return start_row, start_col

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.split(" ")[1]
    try:
        # PyJWT requires algorithms list parameter passed as 'algorithms'
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(401, "Invalid token claims")
    except jwt.PyJWTError:  # Replaced JWTError with PyJWTError
        raise HTTPException(401, "Invalid token")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


def decode_access_token(token: str):
    """Decode a JWT and return the payload, or None if invalid. Same secret as create."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None

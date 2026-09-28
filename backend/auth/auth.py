import os
import re
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt  # PyJWT
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import SessionLocal
from db_models import User

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
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
    Compute the user's message box start row and column.
    L = name length, S = digit sum of phone UID, c = first letter index.
    start_row = ((L+S-1) % 64) + 1, start_col = c % 26.
    """
    clean_name = re.sub(r'[^a-zA-Z]', '', full_name)
    L = len(clean_name)
    S = sum(int(d) for d in phone if d.isdigit())
    c = ord(clean_name[0].lower()) - 97 if clean_name else 0
    start_row = ((L + S - 1) % 64) + 1
    start_col = c % 26
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

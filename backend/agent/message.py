"""
Internal User-to-User Messaging Module

Handles direct messages between users using phone UID.
Provides conversation list, sending, and receiving.
"""

from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from database import SessionLocal
from db_models import User
from pydantic import BaseModel


class DirectMessage(BaseModel):
    id: str
    sender_phone: str
    recipient_phone: str
    content: str
    created_at: datetime


# In-memory storage (replace with database table in production)
_messages: List[DirectMessage] = []


def generate_id() -> str:
    import uuid
    return str(uuid.uuid4())


def send_message(sender_phone: str, recipient_phone: str, content: str) -> DirectMessage:
    """Send a direct message from one user to another."""
    # Validate both users exist
    db = SessionLocal()
    try:
        sender = db.query(User).filter(User.phone == sender_phone).first()
        recipient = db.query(User).filter(User.phone == recipient_phone).first()
        if not sender or not recipient:
            raise ValueError("Sender or recipient not found")
    finally:
        db.close()

    msg = DirectMessage(
        id=generate_id(),
        sender_phone=sender_phone,
        recipient_phone=recipient_phone,
        content=content,
        created_at=datetime.utcnow(),
    )
    _messages.append(msg)
    return msg


def get_conversations(user_phone: str) -> List[Dict]:
    """List all unique users the given user has conversed with."""
    unique_phones = set()
    for m in _messages:
        if m.sender_phone == user_phone:
            unique_phones.add(m.recipient_phone)
        elif m.recipient_phone == user_phone:
            unique_phones.add(m.sender_phone)

    result = []
    for phone in unique_phones:
        # Get last message between user and this phone
        last_msg = None
        for m in reversed(_messages):
            if (m.sender_phone == user_phone and m.recipient_phone == phone) or \
               (m.sender_phone == phone and m.recipient_phone == user_phone):
                last_msg = m
                break
        result.append({
            "phone": phone,
            "last_message": last_msg.content if last_msg else "",
            "last_time": last_msg.created_at.isoformat() if last_msg else None,
        })
    return result


def get_messages_between(user_phone: str, other_phone: str) -> List[DirectMessage]:
    """Return all messages between two users, sorted by time ascending."""
    msgs = [
        m for m in _messages
        if (m.sender_phone == user_phone and m.recipient_phone == other_phone) or
           (m.sender_phone == other_phone and m.recipient_phone == user_phone)
    ]
    msgs.sort(key=lambda x: x.created_at)
    return msgs
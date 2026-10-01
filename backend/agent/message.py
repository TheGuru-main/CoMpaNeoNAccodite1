"""
Internal User-to-User Messaging Module
======================================
Peer-to-peer direct messages between users, keyed by phone.

This is the ONLY messaging system that does NOT involve the AI.
No grid writes, no training, no PSTM.

For AI-triggered messaging, use /rooms/* endpoints instead
(personal brainstorm + room chat both write to the `messages` table
via main.py's /workspace routes, which pass through the pipeline).
"""
from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy import and_, or_, func

from database import SessionLocal
from db_models import User, DirectMessage


def generate_id() -> str:
    import uuid
    return str(uuid.uuid4())


# ============================================================================
# SEND
# ============================================================================

def send_message(
    sender_phone: str,
    recipient_phone: str,
    content: str,
) -> DirectMessage:
    """Send a direct message from one user to another."""
    if sender_phone == recipient_phone:
        raise ValueError("Cannot send a message to yourself")
    content = (content or "").strip()
    if not content:
        raise ValueError("Message content is required")

    db = SessionLocal()
    try:
        sender = db.query(User).filter(User.phone == sender_phone).first()
        recipient = db.query(User).filter(User.phone == recipient_phone).first()
        if not sender or not recipient:
            raise ValueError("Sender or recipient not found")

        row = DirectMessage(
            sender_phone=sender_phone,
            recipient_phone=recipient_phone,
            content=content,
            created_at=datetime.utcnow(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


# ============================================================================
# CONVERSATIONS
# ============================================================================

def get_conversations(user_phone: str) -> List[Dict]:
    """
    Return one entry per unique partner, ordered by most recent message.

    Entry shape:
        {phone, last_message, last_time, unread}
    """
    db = SessionLocal()
    try:
        sent = db.query(DirectMessage.recipient_phone.label("phone")).filter(
            DirectMessage.sender_phone == user_phone,
        )
        received = db.query(DirectMessage.sender_phone.label("phone")).filter(
            DirectMessage.recipient_phone == user_phone,
        )
        partners = {row[0] for row in sent.union(received).all()}

        out: List[Dict] = []
        for phone in partners:
            last = (
                db.query(DirectMessage)
                .filter(or_(
                    and_(DirectMessage.sender_phone == user_phone,
                         DirectMessage.recipient_phone == phone),
                    and_(DirectMessage.sender_phone == phone,
                         DirectMessage.recipient_phone == user_phone),
                ))
                .order_by(DirectMessage.created_at.desc())
                .first()
            )
            if last is None:
                continue

            unread = (
                db.query(func.count(DirectMessage.id))
                .filter(
                    DirectMessage.sender_phone == phone,
                    DirectMessage.recipient_phone == user_phone,
                    DirectMessage.read_at.is_(None),
                )
                .scalar()
            ) or 0

            out.append({
                "phone": phone,
                "last_message": last.content,
                "last_time": last.created_at.isoformat() if last.created_at else None,
                "unread": int(unread),
            })

        out.sort(key=lambda r: r.get("last_time") or "", reverse=True)
        return out
    finally:
        db.close()


# ============================================================================
# THREAD
# ============================================================================

def get_messages_between(
    user_phone: str,
    other_phone: str,
    limit: int = 200,
) -> List[DirectMessage]:
    """Return all messages between two users, sorted ascending by time."""
    db = SessionLocal()
    try:
        return (
            db.query(DirectMessage)
            .filter(or_(
                and_(DirectMessage.sender_phone == user_phone,
                     DirectMessage.recipient_phone == other_phone),
                and_(DirectMessage.sender_phone == other_phone,
                     DirectMessage.recipient_phone == user_phone),
            ))
            .order_by(DirectMessage.created_at.asc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


# ============================================================================
# READ
# ============================================================================

def mark_read(user_phone: str, other_phone: str) -> int:
    """
    Mark all messages FROM other_phone TO user_phone as read.
    Returns the number of rows updated.
    """
    db = SessionLocal()
    try:
        n = (
            db.query(DirectMessage)
            .filter(
                DirectMessage.sender_phone == other_phone,
                DirectMessage.recipient_phone == user_phone,
                DirectMessage.read_at.is_(None),
            )
            .update({DirectMessage.read_at: datetime.utcnow()},
                    synchronize_session=False)
        )
        db.commit()
        return int(n or 0)
    finally:
        db.close()

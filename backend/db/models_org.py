"""Accodite Phase-1 Models."""
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
try:
    from db_models import Base, utcnow
except ImportError:
    from models import Base
    from datetime import datetime, timezone
    def utcnow(): return datetime.now(timezone.utc)

class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    added_by = Column(UUID(as_uuid=True), nullable=True)
    added_at = Column(DateTime, default=utcnow)
    removed_by = Column(UUID(as_uuid=True), nullable=True)
    removed_at = Column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint("workspace_id","user_id",name="uq_workspace_member"),)

class PatternEvent(Base):
    __tablename__ = "pattern_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    kind = Column(String(64), nullable=False, index=True)
    severity = Column(String(16), nullable=False, default="info")
    evidence = Column(JSON, default=dict)
    routed_to = Column(JSON, default=list)
    created_at = Column(DateTime, default=utcnow, index=True)

class DirectiveBoard(Base):
    __tablename__ = "directive_boards"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    pattern_kinds = Column(JSON, default=list)
    min_severity = Column(String(16), default="warn")
    subscribers = Column(JSON, default=list)
    out_of_band = Column(JSON, default=list)
    created_at = Column(DateTime, default=utcnow)

class DirectiveBoardEvent(Base):
    __tablename__ = "directive_board_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id = Column(UUID(as_uuid=True), ForeignKey("directive_boards.id"), nullable=False, index=True)
    pattern_id = Column(UUID(as_uuid=True), ForeignKey("pattern_events.id"), nullable=False, index=True)
    state = Column(String(16), default="open")
    acked_by = Column(UUID(as_uuid=True), nullable=True)
    acked_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)

"""
CoMpaNeoNAccodite – Enterprise Core SQLAlchemy Database Schemas
==============================================================
Manages Neon serverless PostgreSQL database tables using SQLAlchemy ORM models.
Includes tables to track users, organization workspaces, and approval states.
"""

from __future__ import annotations
import datetime
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

Base = declarative_base()

class User(Base):
    """Independent regular application users mapping structure."""
    __tablename__ = "users"
    
    uid = Column(String(64), primary_key=True) # Static Unique User Identifier
    full_name = Column(String(128), nullable=False)
    phone_number = Column(String(32), unique=True, nullable=False)
    version_tag = Column(Integer, default=1) # Tracks matrix start_row structural variations
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Organization(Base):
    """Enterprise Corporate Organization entities profile management."""
    __tablename__ = "organizations"
    
    org_uid = Column(String(64), primary_key=True)
    org_name = Column(String(128), nullable=False)
    admin_fullname = Column(String(128), nullable=False)
    admin_phone = Column(String(32), nullable=False) # Maps to the admin's secret system uID
    shared_org_worker_id = Column(String(64), nullable=False) # Shared backend token for workers
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    workers = relationship("Worker", back_populates="organization")

class Worker(Base):
    """
    Corporate employees registering under an organization.
    Holds a pending verification flag until approved by a platform admin.
    """
    __tablename__ = "workers"
    
    worker_uid = Column(String(64), primary_key=True)
    org_uid = Column(String(64), ForeignKey("organizations.org_uid"), nullable=False)
    full_name = Column(String(128), nullable=False)
    department = Column(String(64), nullable=False)
    is_approved_by_admin = Column(Boolean, default=False) # Onboarding approval state gate
    admin_worker_credential_hash = Column(String(128), nullable=False) # Master grid partition index
    version_tag = Column(Integer, default=1) # Manages start_row relocation metrics
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    organization = relationship("Organization", back_populates="workers")

class WorkspaceRoom(Base):
    """Isolates developer environments into brainstorming studios or team rooms."""
    __tablename__ = "workspace_rooms"
    
    room_id = Column(String(64), primary_key=True)
    org_uid = Column(String(64), ForeignKey("organizations.org_uid"), nullable=True)
    room_name = Column(String(128), nullable=False)
    room_type = Column(String(64), nullable=False) # personal_brainstorm | department_team | general_org
    associated_department = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Database connectivity initialization hub manager helper
class NeonDatabaseConnectionManager:
    def __init__(self, neon_postgres_connection_string: str):
        """Initializes connection pools targeting your Neon Postgres cluster database."""
        self.engine = create_engine(neon_postgres_connection_string, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def synchronize_schema_tables(self) -> None:
        """Constructs and deploys database tables if not managed via external Alembic templates."""
        Base.metadata.create_all(bind=self.engine)

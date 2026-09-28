from __future__ import annotations

import uuid

from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    JSON,
    UniqueConstraint,
)

from sqlalchemy.orm import relationship

from sqlalchemy.dialects.postgresql import UUID

from database import Base


# =====================================================================
# HELPERS
# =====================================================================

def utcnow():
    return datetime.utcnow()


# =====================================================================
# USER
# =====================================================================

class User(Base):
    """
    Human account.

    Account types:

        regular
            Independent CoMpaNeoN user.

        worker
            Human member operating under an Organization.

        admin
            Optional administrative account.

    IMPORTANT:

        A worker does NOT automatically receive an independent
        organizational brain.

        Their organization membership determines access to the
        organization's shared AI brain.

        A worker can still have a personal AI brain for private
        personal use.
    """

    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------------------
    # ACCOUNT IDENTITY
    # ---------------------------------------------------------------

    phone = Column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
    )

    full_name = Column(
        String(255),
        nullable=False,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    language = Column(
        String(10),
        default="en",
        nullable=False,
    )

    country = Column(
        String(100),
        default="Nigeria",
        nullable=False,
    )

    temperament = Column(
        String(20),
        default="sanguine",
        nullable=False,
    )

    settings = Column(
        JSON,
        default=dict,
    )

    # ---------------------------------------------------------------
    # ACCOUNT CLASSIFICATION
    # ---------------------------------------------------------------

    account_type = Column(
        String(30),
        default="regular",
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------------
    # USER DETERMINISTIC PLACEMENT
    #
    # This remains account-level placement metadata.
    # Actual MemoryGrid placement remains the responsibility of
    # memory_grid.py.
    # ---------------------------------------------------------------

    start_row = Column(
        Integer,
        nullable=False,
    )

    start_col = Column(
        Integer,
        nullable=False,
    )

    # ---------------------------------------------------------------
    # PERSONAL AI BRAIN
    #
    # Every human can have a private CoMpaNeoN brain.
    #
    # For a regular user this is their primary AI brain.
    #
    # For a worker this is PRIVATE and separate from the
    # organization's shared brain.
    # ---------------------------------------------------------------

    personal_ai_uid = Column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=utcnow,
    )

    updated_at = Column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    # ---------------------------------------------------------------
    # RELATIONSHIPS
    # ---------------------------------------------------------------

    organizations = relationship(
        "OrganizationMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    workspaces = relationship(
        "Workspace",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Workspace.user_id",
    )

    messages = relationship(
        "Message",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    personal_ai_brain = relationship(
        "AIBrain",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="AIBrain.user_id",
    )


# =====================================================================
# ORGANIZATION
# =====================================================================

class Organization(Base):
    """
    Organization identity.

    An organization owns ONE shared CoMpaNeoN AI brain.

    All authorized workers tied to this organization access the same
    organizational MemoryGrid through their organization membership.
    """

    __tablename__ = "organizations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------------------
    # ORGANIZATION IDENTITY
    # ---------------------------------------------------------------

    name = Column(
        String(255),
        nullable=False,
    )

    slug = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    email = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    phone = Column(
        String(32),
        unique=True,
        nullable=True,
    )

    country = Column(
        String(100),
        default="Nigeria",
        nullable=False,
    )

    language = Column(
        String(10),
        default="en",
        nullable=False,
    )

    settings = Column(
        JSON,
        default=dict,
    )

    # ---------------------------------------------------------------
    # ORGANIZATION AI
    #
    # ONE shared AI uID for the organization.
    # ---------------------------------------------------------------

    ai_uid = Column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------------
    # ORGANIZATION DETERMINISTIC PLACEMENT
    # ---------------------------------------------------------------

    start_row = Column(
        Integer,
        nullable=False,
    )

    start_col = Column(
        Integer,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=utcnow,
    )

    updated_at = Column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    # ---------------------------------------------------------------
    # RELATIONSHIPS
    # ---------------------------------------------------------------

    members = relationship(
        "OrganizationMembership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    workspaces = relationship(
        "Workspace",
        back_populates="organization",
        cascade="all, delete-orphan",
        foreign_keys="Workspace.organization_id",
    )

    ai_brain = relationship(
        "AIBrain",
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="AIBrain.organization_id",
    )


# =====================================================================
# ORGANIZATION MEMBERSHIP
# =====================================================================

class OrganizationMembership(Base):
    """
    Binds a worker/user to an organization.

    The organization generates the credentials.

    Those credentials establish that the worker belongs to the
    organization and therefore may access the organization's shared
    CoMpaNeoN AI brain.
    """

    __tablename__ = "organization_memberships"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------------
    # WORKER IDENTITY INSIDE ORGANIZATION
    # ---------------------------------------------------------------

    role = Column(
        String(50),
        default="worker",
        nullable=False,
    )

    department = Column(
        String(100),
        nullable=True,
    )

    title = Column(
        String(100),
        nullable=True,
    )

    # ---------------------------------------------------------------
    # ORGANIZATION-GENERATED CREDENTIAL
    #
    # Store the credential hash, never the raw secret.
    # ---------------------------------------------------------------

    credential_hash = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    credential_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=utcnow,
    )

    updated_at = Column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    # ---------------------------------------------------------------
    # RELATIONSHIPS
    # ---------------------------------------------------------------

    user = relationship(
        "User",
        back_populates="organizations",
    )

    organization = relationship(
        "Organization",
        back_populates="members",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "organization_id",
            name="uq_user_organization_membership",
        ),
    )


# =====================================================================
# AI BRAIN
# =====================================================================

class AIBrain(Base):
    """
    Identifies a CoMpaNeoN AI memory scope.

    This is intentionally separate from the human User.

    Supported scopes:

        user
            Private personal AI brain.

        organization
            Shared organizational AI brain.

        personal_workspace
            AI context belonging to a user's private brainstorming
            workspace.

        team_workspace
            Organizational AI context for a team room.

    The actual STM/LTM storage, relevance partitioning, GridCV,
    GSP-XOR permutations, retrieval and physical storage routing
    remain outside this relational model and belong to MemoryGrid.
    """

    __tablename__ = "ai_brains"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------------------
    # AI uID
    # ---------------------------------------------------------------

    ai_uid = Column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------------
    # MEMORY SCOPE
    # ---------------------------------------------------------------

    scope_type = Column(
        String(40),
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------------
    # OWNERSHIP
    #
    # Exactly one appropriate owner is populated depending on
    # scope_type.
    # ---------------------------------------------------------------

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True,
        index=True,
    )

    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id"),
        nullable=True,
        unique=True,
        index=True,
    )

    # ---------------------------------------------------------------
    # MEMORYGRID IDENTIFIER
    #
    # This is the logical storage identity. Physical disk/cloud
    # partition mapping will be added at the MemoryGrid/storage layer.
    # ---------------------------------------------------------------

    memorygrid_uid = Column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------------
    # BRAIN STATUS
    # ---------------------------------------------------------------

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=utcnow,
    )

    updated_at = Column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    # ---------------------------------------------------------------
    # RELATIONSHIPS
    # ---------------------------------------------------------------

    user = relationship(
        "User",
        back_populates="personal_ai_brain",
        foreign_keys=[user_id],
    )

    organization = relationship(
        "Organization",
        back_populates="ai_brain",
        foreign_keys=[organization_id],
    )

    workspace = relationship(
        "Workspace",
        back_populates="ai_brain",
        foreign_keys=[workspace_id],
    )


# =====================================================================
# WORKSPACE
# =====================================================================

class Workspace(Base):
    """
    CoMpaNeoN workspace / room.

    Workspace types:

        personal_brainstorm
            Private user's brainstorming room.

        team
            Organization team room.

        organization
            General organization AI workspace.

    The AI is explicitly invoked inside team/organization rooms.

    Example:

        @org

    The workspace supplies the project/room context to the AI.
    """

    __tablename__ = "workspaces"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------------------
    # OWNERSHIP
    # ---------------------------------------------------------------

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True,
        index=True,
    )

    # ---------------------------------------------------------------
    # WORKSPACE TYPE
    # ---------------------------------------------------------------

    workspace_type = Column(
        String(40),
        default="personal_brainstorm",
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------------
    # PROJECT IDENTITY
    # ---------------------------------------------------------------

    project_name = Column(
        String(255),
        nullable=False,
    )

    project_domain = Column(
        String(100),
        default="general",
    )

    project_keywords = Column(
        JSON,
        default=list,
    )

    # ---------------------------------------------------------------
    # PROJECT GRIDCV METADATA
    #
    # This remains metadata only.
    #
    # The actual GridCV architecture will later be handled by
    # MemoryGrid.
    # ---------------------------------------------------------------

    project_grid_cv = Column(
        JSON,
        default=dict,
    )

    # ---------------------------------------------------------------
    # COMPILED ROOM CONTEXT
    # ---------------------------------------------------------------

    context_summary = Column(
        Text,
        default="",
    )

    temporal_context = Column(
        JSON,
        default=dict,
    )

    context_version = Column(
        Integer,
        default=1,
    )

    # ---------------------------------------------------------------
    # AI INVOCATION
    #
    # For example:
    #
    #     @org
    #
    # The invocation mechanism itself belongs to the messaging /
    # directives layer.
    # ---------------------------------------------------------------

    ai_invocation = Column(
        String(100),
        default="@org",
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=utcnow,
    )

    updated_at = Column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    # ---------------------------------------------------------------
    # RELATIONSHIPS
    # ---------------------------------------------------------------

    user = relationship(
        "User",
        back_populates="workspaces",
        foreign_keys=[user_id],
    )

    organization = relationship(
        "Organization",
        back_populates="workspaces",
        foreign_keys=[organization_id],
    )

    ai_brain = relationship(
        "AIBrain",
        back_populates="workspace",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="AIBrain.workspace_id",
    )

    messages = relationship(
        "Message",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )


# =====================================================================
# MESSAGE
# =====================================================================

class Message(Base):
    """
    User/worker/AI message inside a workspace.

    The message is relational metadata.

    Its actual lexical representation, MemoryGrid placement, STM/LTM
    partitioning and retrieval path remain in the AI memory architecture.
    """

    __tablename__ = "messages"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------------
    # MESSAGE AUTHOR
    #
    # user
    # worker
    # ai
    # system
    # ---------------------------------------------------------------

    role = Column(
        String(20),
        nullable=False,
    )

    content = Column(
        Text,
        nullable=False,
    )

    # ---------------------------------------------------------------
    # AI INTERPRETATION METADATA
    # ---------------------------------------------------------------

    detected_domain = Column(
        String(100),
        default="general",
    )

    keywords = Column(
        JSON,
        default=list,
    )

    grid_cv = Column(
        JSON,
        default=dict,
    )

    temporal_context = Column(
        JSON,
        default=dict,
    )

    # AI brain that handled/generated the message.
    #
    # This allows a message to be associated with either:
    #
    #   user's personal brain
    #   organization's shared brain
    #   workspace brain
    #
    ai_uid = Column(
        String(128),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=utcnow,
    )

    # ---------------------------------------------------------------
    # RELATIONSHIPS
    # ---------------------------------------------------------------

    workspace = relationship(
        "Workspace",
        back_populates="messages",
    )

    user = relationship(
        "User",
        back_populates="messages",
    )


# =====================================================================
# API KEY
# =====================================================================

class APIKey(Base):
    """
    API credentials for programmatic access.

    This is separate from organization worker credentials.
    """

    __tablename__ = "api_keys"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    key = Column(
        String(64),
        unique=True,
        nullable=False,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True,
        index=True,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=utcnow,
    )
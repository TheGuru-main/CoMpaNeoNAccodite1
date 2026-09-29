CREATE TABLE IF NOT EXISTS workspace_members (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    user_id UUID NOT NULL REFERENCES users(id),
    added_by UUID, added_at TIMESTAMP DEFAULT NOW(),
    removed_by UUID, removed_at TIMESTAMP,
    CONSTRAINT uq_workspace_member UNIQUE (workspace_id, user_id)
);
CREATE INDEX IF NOT EXISTS ix_wm_workspace ON workspace_members(workspace_id);
CREATE INDEX IF NOT EXISTS ix_wm_user ON workspace_members(user_id);

CREATE TABLE IF NOT EXISTS pattern_events (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    workspace_id UUID REFERENCES workspaces(id),
    user_id UUID REFERENCES users(id),
    kind VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'info',
    evidence JSONB DEFAULT '{}'::jsonb,
    routed_to JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_pe_org ON pattern_events(organization_id);
CREATE INDEX IF NOT EXISTS ix_pe_ws ON pattern_events(workspace_id);
CREATE INDEX IF NOT EXISTS ix_pe_kind ON pattern_events(kind);

CREATE TABLE IF NOT EXISTS directive_boards (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(120) NOT NULL,
    pattern_kinds JSONB DEFAULT '[]'::jsonb,
    min_severity VARCHAR(16) DEFAULT 'warn',
    subscribers JSONB DEFAULT '[]'::jsonb,
    out_of_band JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_db_org ON directive_boards(organization_id);

CREATE TABLE IF NOT EXISTS directive_board_events (
    id UUID PRIMARY KEY,
    board_id UUID NOT NULL REFERENCES directive_boards(id),
    pattern_id UUID NOT NULL REFERENCES pattern_events(id),
    state VARCHAR(16) DEFAULT 'open',
    acked_by UUID, acked_at TIMESTAMP, resolved_at TIMESTAMP,
    notes TEXT DEFAULT '', created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_dbe_board ON directive_board_events(board_id);
CREATE INDEX IF NOT EXISTS ix_dbe_pattern ON directive_board_events(pattern_id);

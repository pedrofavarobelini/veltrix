CREATE TABLE IF NOT EXISTS pedrocore_learning_candidates (
    candidate_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    pattern_id TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    producer TEXT NOT NULL,
    decision TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    policy_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    stored_at TIMESTAMPTZ NOT NULL,
    retention_until TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (project_id, candidate_id),
    CONSTRAINT ck_pedrocore_candidate_confidence
        CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

CREATE INDEX IF NOT EXISTS idx_pedrocore_candidates_pattern
    ON pedrocore_learning_candidates
    (project_id, pattern_id, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_pedrocore_candidates_retention
    ON pedrocore_learning_candidates (retention_until);

CREATE TABLE IF NOT EXISTS pedrocore_operational_memory (
    memory_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    pattern_id TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    lifecycle TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    sample_size INTEGER NOT NULL,
    policy_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    retention_until TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (project_id, memory_id),
    CONSTRAINT uq_pedrocore_memory_pattern UNIQUE (project_id, pattern_id),
    CONSTRAINT ck_pedrocore_memory_confidence
        CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT ck_pedrocore_memory_sample_size CHECK (sample_size >= 0),
    CONSTRAINT ck_pedrocore_memory_lifecycle
        CHECK (lifecycle IN ('DETECTED', 'ACTIVE', 'MITIGATED', 'RESOLVED'))
);

CREATE INDEX IF NOT EXISTS idx_pedrocore_memory_retrieval
    ON pedrocore_operational_memory
    (project_id, lifecycle, pattern_type, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_pedrocore_memory_retention
    ON pedrocore_operational_memory (retention_until);

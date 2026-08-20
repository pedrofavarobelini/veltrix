CREATE TABLE IF NOT EXISTS pedrocore_interaction_outcomes (
    outcome_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    producer TEXT NOT NULL,
    caller_role TEXT NOT NULL,
    environment TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    input_signature TEXT NOT NULL,
    context_signature TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    response_strategy TEXT NOT NULL,
    feedback TEXT NOT NULL,
    accepted BOOLEAN,
    rejected BOOLEAN,
    fallback_used BOOLEAN NOT NULL DEFAULT FALSE,
    regeneration_used BOOLEAN NOT NULL DEFAULT FALSE,
    lifecycle TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    stored_at TIMESTAMPTZ NOT NULL,
    retention_until TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (project_id, outcome_id),
    CONSTRAINT ck_pedrocore_outcome_feedback
        CHECK (feedback IN ('positive', 'negative', 'neutral', 'unknown')),
    CONSTRAINT ck_pedrocore_outcome_acceptance
        CHECK (NOT (accepted IS TRUE AND rejected IS TRUE))
);

CREATE INDEX IF NOT EXISTS idx_pedrocore_outcomes_project_created
    ON pedrocore_interaction_outcomes (project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pedrocore_outcomes_correlation
    ON pedrocore_interaction_outcomes
    (project_id, conversation_id, message_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pedrocore_outcomes_retention
    ON pedrocore_interaction_outcomes (retention_until);

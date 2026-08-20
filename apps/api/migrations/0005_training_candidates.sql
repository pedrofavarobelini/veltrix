CREATE TABLE IF NOT EXISTS pedrocore_training_candidates (
    candidate_id VARCHAR(64) NOT NULL,
    project_id VARCHAR(128) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    source_id VARCHAR(128),
    source_reference_hash VARCHAR(71) NOT NULL,
    fingerprint VARCHAR(71) NOT NULL,
    task_type VARCHAR(128) NOT NULL,
    training_purpose VARCHAR(32) NOT NULL,
    lifecycle VARCHAR(32) NOT NULL,
    eligibility VARCHAR(32) NOT NULL,
    privacy_classification VARCHAR(32) NOT NULL,
    policy_version VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (project_id, candidate_id),
    UNIQUE (
        project_id,
        source_type,
        source_reference_hash,
        fingerprint,
        training_purpose
    ),
    CONSTRAINT pedrocore_training_candidate_lifecycle_check CHECK (
        lifecycle IN ('proposed', 'authorized', 'review_required', 'excluded', 'revoked', 'consumed')
    ),
    CONSTRAINT pedrocore_training_candidate_eligibility_check CHECK (
        eligibility IN ('eligible', 'not_eligible', 'requires_review')
    ),
    CONSTRAINT pedrocore_training_candidate_privacy_check CHECK (
        privacy_classification IN ('safe', 'requires_sanitization', 'rejected_sensitive')
    ),
    CONSTRAINT pedrocore_training_candidate_purpose_check CHECK (
        training_purpose IN ('generative_sft', 'preference', 'risk', 'evaluation_only')
    )
);

CREATE INDEX IF NOT EXISTS pedrocore_training_candidates_project_status_idx
    ON pedrocore_training_candidates (project_id, lifecycle, created_at);

CREATE INDEX IF NOT EXISTS pedrocore_training_candidates_readiness_idx
    ON pedrocore_training_candidates (
        project_id,
        training_purpose,
        source_type,
        eligibility
    );

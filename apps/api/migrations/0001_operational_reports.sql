CREATE TABLE IF NOT EXISTS pedrocore_operational_reports (
    memory_id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    producer TEXT,
    report_type TEXT NOT NULL,
    run_id TEXT,
    conversation_id TEXT,
    lifecycle TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    retention_until TIMESTAMPTZ,
    payload JSONB NOT NULL,
    CONSTRAINT uq_pedrocore_operational_report UNIQUE (project_id, report_id)
);

CREATE INDEX IF NOT EXISTS idx_pedrocore_reports_project_created
    ON pedrocore_operational_reports (project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pedrocore_reports_retention
    ON pedrocore_operational_reports (retention_until)
    WHERE retention_until IS NOT NULL;

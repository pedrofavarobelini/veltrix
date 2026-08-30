-- Era 4 — Evidence Platform.
--
-- Registro de evidencia operacional recebida por contrato universal.
-- NAO e um store de Training Candidate: nao existem colunas de elegibilidade,
-- autorizacao, proposito de treino ou lifecycle de candidato, e a ausencia e
-- deliberada. Promocao a candidato pertence a `pedrocore_training_candidates`
-- e acontece por decisao do Learning Plane.
--
-- Isolamento de projeto e CHAVE PRIMARIA, nao filtro de aplicacao: um bug de
-- query nao consegue atravessar a fronteira entre consumidores.

CREATE TABLE IF NOT EXISTS pedrocore_evidence_records (
    evidence_record_id VARCHAR(128) NOT NULL,
    project_id VARCHAR(128) NOT NULL,
    producer_id VARCHAR(128) NOT NULL,
    kind VARCHAR(32) NOT NULL,
    event_id VARCHAR(128) NOT NULL,
    correlation_id VARCHAR(128),
    idempotency_key VARCHAR(128),
    contract_version VARCHAR(128) NOT NULL,
    fingerprint VARCHAR(71) NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    policy_version VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (project_id, evidence_record_id),

    -- Dedup por conteudo: a mesma evidencia, do mesmo tipo, no mesmo projeto,
    -- entra uma vez so. O banco garante isto mesmo sob concorrencia, que e
    -- exatamente o caso que uma verificacao só na aplicacao perderia.
    CONSTRAINT pedrocore_evidence_fingerprint_unique
        UNIQUE (project_id, kind, fingerprint),

    CONSTRAINT pedrocore_evidence_kind_check CHECK (
        kind IN ('quality_evidence', 'execution_outcome', 'learning_source')
    )
);

-- Idempotencia: a chave e unica POR PROJETO, e nao globalmente. Dois
-- consumidores diferentes podem escolher a mesma string sem colidir.
-- Parcial porque `idempotency_key` e opcional: sem o WHERE, varios NULL
-- seriam tratados de forma inconsistente entre versoes do PostgreSQL.
CREATE UNIQUE INDEX IF NOT EXISTS pedrocore_evidence_idempotency_idx
    ON pedrocore_evidence_records (project_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS pedrocore_evidence_project_kind_idx
    ON pedrocore_evidence_records (project_id, kind, received_at);

CREATE INDEX IF NOT EXISTS pedrocore_evidence_correlation_idx
    ON pedrocore_evidence_records (project_id, correlation_id)
    WHERE correlation_id IS NOT NULL;

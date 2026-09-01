-- Stage R2 do Risk Engine V2 — persistência própria do domínio Risk.
--
-- Antes desta migration, o histórico de risco vinha de `report_memory` e
-- `operational_memory`. Isso fazia `PEDROCORE_REPORT_MEMORY_PERSISTENCE=off`
-- decidir, em silêncio, se o motor de risco tinha ou não história — uma
-- variável de outro domínio governando este.
--
-- As duas tabelas guardam uma PROJEÇÃO, não o objeto de domínio inteiro. Não há
-- coluna para `request_text`, prompt, comando ou diff: a proteção de privacidade
-- é a ausência de lugar onde colocar, não um sanitizador que roda depois.
--
-- Report Memory e Operational Memory continuam recebendo o que sempre
-- receberam. Elas deixam de ser a ÚNICA fonte; não deixam de existir.

-- O que o motor PREVIU, antes de qualquer execução.
CREATE TABLE IF NOT EXISTS pedrocore_risk_analyses (
    analysis_id VARCHAR(128) NOT NULL,
    project_id VARCHAR(128) NOT NULL,
    request_id VARCHAR(128) NOT NULL,

    -- Versão da política que produziu a análise. Sem ela, comparar duas
    -- análises de épocas diferentes seria comparar réguas diferentes.
    analysis_policy_version VARCHAR(64) NOT NULL,

    severity VARCHAR(32) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    uncertainty DOUBLE PRECISION NOT NULL,
    blast_radius_level VARCHAR(64),

    -- Códigos e números, nunca texto do consumidor.
    reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    dimensions JSONB NOT NULL DEFAULT '[]'::jsonb,

    fingerprint VARCHAR(71) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    policy_version VARCHAR(64) NOT NULL,

    -- Isolamento de projeto é CHAVE, não filtro de aplicação: um erro de query
    -- não consegue atravessar a fronteira entre consumidores.
    PRIMARY KEY (project_id, analysis_id),

    CONSTRAINT pedrocore_risk_analysis_confidence_check CHECK (
        confidence >= 0.0 AND confidence <= 1.0
    ),
    CONSTRAINT pedrocore_risk_analysis_uncertainty_check CHECK (
        uncertainty >= 0.0 AND uncertainty <= 1.0
    )
);

-- O que de fato ACONTECEU, depois da execução.
CREATE TABLE IF NOT EXISTS pedrocore_risk_outcomes (
    outcome_id VARCHAR(128) NOT NULL,
    project_id VARCHAR(128) NOT NULL,

    -- A correlação que fecha o par previsto/observado. Sem ela o registro seria
    -- um fato solto e o motor nunca saberia a qual previsão corresponde.
    risk_analysis_id VARCHAR(128) NOT NULL,

    contract_id VARCHAR(128) NOT NULL,
    evidence_id VARCHAR(128) NOT NULL,
    outcome_policy_version VARCHAR(64) NOT NULL,

    effective_gate VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL,
    contract_valid BOOLEAN NOT NULL,

    predicted_risk_materialized BOOLEAN NOT NULL DEFAULT FALSE,
    unpredicted_issue_detected BOOLEAN NOT NULL DEFAULT FALSE,

    predicted_dimensions JSONB NOT NULL DEFAULT '{}'::jsonb,
    actual_issue_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    scope_deviation JSONB NOT NULL DEFAULT '[]'::jsonb,

    fingerprint VARCHAR(71) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    policy_version VARCHAR(64) NOT NULL,

    PRIMARY KEY (project_id, outcome_id),

    CONSTRAINT pedrocore_risk_outcome_status_check CHECK (
        status IN ('passed', 'failed', 'blocked')
    ),
    CONSTRAINT pedrocore_risk_outcome_gate_check CHECK (
        effective_gate IN ('PASS', 'PASS_WITH_WARNINGS', 'REVIEW_REQUIRED', 'BLOCK')
    )
);

-- A consulta quente do histórico: registros recentes de um projeto.
CREATE INDEX IF NOT EXISTS pedrocore_risk_analyses_history_idx
    ON pedrocore_risk_analyses (project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS pedrocore_risk_outcomes_history_idx
    ON pedrocore_risk_outcomes (project_id, created_at DESC);

-- Reconstruir o par previsto/observado sem varrer a tabela.
CREATE INDEX IF NOT EXISTS pedrocore_risk_outcomes_analysis_idx
    ON pedrocore_risk_outcomes (project_id, risk_analysis_id);

-- Sem chave estrangeira entre as duas tabelas de propósito: um outcome pode
-- chegar de um processo que não gravou a análise (persistência ligada no meio
-- do caminho, ou análise fora da janela de retenção). Exigir a análise faria
-- perder o outcome — o fato mais caro dos dois, porque é o observado.

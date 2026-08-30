-- Final Hardening — persistência do Dataset Registry.
--
-- Guarda METADATA DE GOVERNANÇA, não população de treino. Uma definição de
-- dataset é o registro de uma decisão — quem declarou qual escopo, sob qual
-- política de split, para qual propósito. Se essa decisão morre com o
-- processo, ela vira boato.
--
-- A linhagem é o que torna um modelo auditável: sem ela ninguém responde
-- "este exemplo podia estar aqui?" depois que a resposta importa.
--
-- Persistir governança NÃO fabrica dado. `DATASET_NOT_READY` continua sendo o
-- resultado correto enquanto não houver população real autorizada.

CREATE TABLE IF NOT EXISTS pedrocore_dataset_definitions (
    dataset_id VARCHAR(128) PRIMARY KEY,
    display_name VARCHAR(128) NOT NULL,
    scope VARCHAR(32) NOT NULL,
    project_ids JSONB NOT NULL,
    training_purpose VARCHAR(32) NOT NULL,
    allowed_source_types JSONB NOT NULL,
    split_policy JSONB NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_by VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    policy_version VARCHAR(64) NOT NULL,
    notes TEXT,

    CONSTRAINT pedrocore_dataset_scope_check CHECK (
        scope IN ('project', 'cross_project')
    ),
    CONSTRAINT pedrocore_dataset_status_check CHECK (
        status IN ('defined', 'materialized', 'archived')
    ),
    CONSTRAINT pedrocore_dataset_purpose_check CHECK (
        training_purpose IN ('generative_sft', 'preference', 'risk', 'evaluation_only')
    )
);

-- Uma versão materializada é IMUTÁVEL: `(dataset_id, version)` é a chave, e
-- não existe UPDATE previsto. Reescrever uma versão apagaria a evidência de
-- contra o que uma avaliação foi feita.
CREATE TABLE IF NOT EXISTS pedrocore_dataset_versions (
    dataset_id VARCHAR(128) NOT NULL,
    version INTEGER NOT NULL,
    content_fingerprint VARCHAR(71) NOT NULL,
    materialized_at TIMESTAMPTZ NOT NULL,
    materialized_by VARCHAR(128) NOT NULL,
    total_examples INTEGER NOT NULL,
    train_examples INTEGER NOT NULL,
    validation_examples INTEGER NOT NULL,
    test_examples INTEGER NOT NULL,
    lineage JSONB NOT NULL,

    PRIMARY KEY (dataset_id, version),

    CONSTRAINT pedrocore_dataset_version_positive_check CHECK (version >= 1),
    -- A soma dos splits precisa bater com o total. Um resto silencioso seria
    -- exemplo autorizado que não entrou em split nenhum — dado coletado,
    -- aprovado e esquecido.
    CONSTRAINT pedrocore_dataset_split_sum_check CHECK (
        train_examples + validation_examples + test_examples = total_examples
    ),
    CONSTRAINT pedrocore_dataset_version_fk FOREIGN KEY (dataset_id)
        REFERENCES pedrocore_dataset_definitions (dataset_id)
);

CREATE INDEX IF NOT EXISTS pedrocore_dataset_versions_dataset_idx
    ON pedrocore_dataset_versions (dataset_id, version DESC);

-- Duas versões com a mesma composição são a mesma versão. Poder prová-lo é o
-- que torna um resultado de avaliação reproduzível.
CREATE INDEX IF NOT EXISTS pedrocore_dataset_versions_fingerprint_idx
    ON pedrocore_dataset_versions (content_fingerprint);

-- Durabilidade das registries de plataforma (Model, Asset e Evaluation).
--
-- Por que existe
-- --------------
-- As tres nasceram em memoria e guardam estado que NAO pode desaparecer num
-- restart: a evidencia que autoriza uma promocao, a versao de prompt que
-- estava ativa, e o registro de avaliacao que sustenta as duas. Perder isso
-- significaria promover de novo sem saber que ja se promoveu.
--
-- O que continua em memoria, por escolha
-- --------------------------------------
-- Trilha de correlacao, comparacoes de shadow e amostras de SLO. As tres sao
-- observacao viva: a trilha aponta para evidencia que ja e duravel, o shadow
-- pode ser reobservado, e uma janela de SLO de antes do restart descreveria um
-- processo que nao existe mais.
--
-- Nome das tabelas
-- ----------------
-- Prefixo `pedrocore_` mantido de proposito. O produto e Veltrix, mas o schema
-- inteiro usa este prefixo, e criar UMA tabela com outro deixaria duas
-- convencoes convivendo. Branding nao justifica migration destrutiva.
--
-- Migrations anteriores nao foram tocadas.

CREATE TABLE IF NOT EXISTS pedrocore_model_entries (
    model_key                   VARCHAR(128) NOT NULL,
    provider                    VARCHAR(64)  NOT NULL,
    model_name                  VARCHAR(96)  NOT NULL,
    model_version               VARCHAR(64)  NOT NULL,
    registry_version            VARCHAR(64)  NOT NULL,
    status                      VARCHAR(32)  NOT NULL,
    capabilities                JSONB        NOT NULL DEFAULT '[]'::jsonb,
    evaluation_ids              JSONB        NOT NULL DEFAULT '[]'::jsonb,
    compatible_asset_ids        JSONB        NOT NULL DEFAULT '[]'::jsonb,
    compatible_policy_version   VARCHAR(64),
    created_at                  TIMESTAMPTZ  NOT NULL,
    promoted_at                 TIMESTAMPTZ,
    rejected_at                 TIMESTAMPTZ,
    rolled_back_at              TIMESTAMPTZ,
    notes                       VARCHAR(512),
    PRIMARY KEY (model_key)
);

-- Um estado que exige evidencia nao pode existir sem ela. A guarda ja mora no
-- schema Pydantic; aqui ela vira invariante do BANCO, para que um INSERT
-- direto tambem esbarre nela.
ALTER TABLE pedrocore_model_entries
    DROP CONSTRAINT IF EXISTS pedrocore_model_promotion_needs_evidence;
ALTER TABLE pedrocore_model_entries
    ADD CONSTRAINT pedrocore_model_promotion_needs_evidence CHECK (
        status NOT IN ('APPROVED', 'PROMOTED')
        OR jsonb_array_length(evaluation_ids) > 0
    );

CREATE INDEX IF NOT EXISTS idx_pedrocore_model_entries_status
    ON pedrocore_model_entries (status);

CREATE TABLE IF NOT EXISTS pedrocore_model_transitions (
    transition_id   VARCHAR(128) NOT NULL,
    model_key       VARCHAR(128) NOT NULL,
    from_status     VARCHAR(32)  NOT NULL,
    to_status       VARCHAR(32)  NOT NULL,
    reason          VARCHAR(512) NOT NULL,
    evaluation_id   VARCHAR(128),
    actor           VARCHAR(64)  NOT NULL,
    occurred_at     TIMESTAMPTZ  NOT NULL,
    PRIMARY KEY (transition_id)
);

CREATE INDEX IF NOT EXISTS idx_pedrocore_model_transitions_key
    ON pedrocore_model_transitions (model_key, occurred_at);

CREATE TABLE IF NOT EXISTS pedrocore_asset_versions (
    asset_id                        VARCHAR(128) NOT NULL,
    version                         INTEGER      NOT NULL,
    registry_version                VARCHAR(64)  NOT NULL,
    kind                            VARCHAR(48)  NOT NULL,
    status                          VARCHAR(32)  NOT NULL,
    content                         TEXT         NOT NULL,
    content_hash                    VARCHAR(80)  NOT NULL,
    provenance                      VARCHAR(128) NOT NULL,
    author                          VARCHAR(64)  NOT NULL,
    change_reason                   VARCHAR(512) NOT NULL,
    created_at                      TIMESTAMPTZ  NOT NULL,
    compatible_policy_version       VARCHAR(64),
    compatible_contract_versions    JSONB        NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (asset_id, version)
);

-- No maximo UMA versao ativa por asset. Duas seria pior que nenhuma: ninguem
-- saberia qual rodou. O indice parcial unico faz o banco recusar a segunda.
CREATE UNIQUE INDEX IF NOT EXISTS idx_pedrocore_asset_single_active
    ON pedrocore_asset_versions (asset_id)
    WHERE status = 'ACTIVE';

CREATE TABLE IF NOT EXISTS pedrocore_evaluation_records (
    evaluation_id       VARCHAR(128) NOT NULL,
    project_id          VARCHAR(128) NOT NULL,
    plane_version       VARCHAR(64)  NOT NULL,
    subject_kind        VARCHAR(48)  NOT NULL,
    subject_id          VARCHAR(160) NOT NULL,
    subject_version     VARCHAR(64),
    suite               VARCHAR(96)  NOT NULL,
    suite_version       VARCHAR(32)  NOT NULL,
    dataset_id          VARCHAR(128),
    dataset_slice       VARCHAR(128),
    environment         VARCHAR(32)  NOT NULL,
    producer            VARCHAR(64)  NOT NULL,
    status              VARCHAR(32)  NOT NULL,
    metrics             JSONB        NOT NULL DEFAULT '[]'::jsonb,
    reason_codes        JSONB        NOT NULL DEFAULT '[]'::jsonb,
    evidence_ids        JSONB        NOT NULL DEFAULT '[]'::jsonb,
    correlation_id      VARCHAR(128),
    evaluated_at        TIMESTAMPTZ  NOT NULL,
    -- Isolamento de projeto e CHAVE, e nao filtro aplicado depois. Filtro
    -- pos-busca e uma peneira que um dia alguem esquece de aplicar.
    PRIMARY KEY (project_id, evaluation_id)
);

-- Nao se mede o que nao existe: um resultado sem dataset nao pode trazer
-- metrica. A guarda existe no Pydantic e aqui, porque um dump reconstruido
-- entra pelo banco.
ALTER TABLE pedrocore_evaluation_records
    DROP CONSTRAINT IF EXISTS pedrocore_evaluation_metrics_need_dataset;
ALTER TABLE pedrocore_evaluation_records
    ADD CONSTRAINT pedrocore_evaluation_metrics_need_dataset CHECK (
        status <> 'DATASET_NOT_READY' OR jsonb_array_length(metrics) = 0
    );

CREATE INDEX IF NOT EXISTS idx_pedrocore_evaluation_subject
    ON pedrocore_evaluation_records (project_id, subject_id);

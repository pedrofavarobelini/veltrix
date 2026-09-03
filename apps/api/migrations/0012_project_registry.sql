-- Catalogo de projetos conhecidos pelo Veltrix.
--
-- Por que existe
-- --------------
-- Um projeto criado pelo usuario E a identidade sob a qual as analises dele
-- sao gravadas. Se o catalogo morre com o processo, o `project_id` das
-- analises de ontem passa a apontar para um projeto que o sistema nao conhece
-- mais, e isolamento por projeto vira isolamento por projeto que talvez
-- exista.
--
-- O que esta tabela NAO e
-- -----------------------
-- Nao e fonte de capacidade. Ela guarda identidade e metadata de exibicao.
-- Capacidade continua vindo do Capability Manifest, do Executor Profile e da
-- Policy, e a permissao efetiva continua sendo a intersecao dos tres. Estar
-- nesta tabela nao concede nada.
--
-- Nome da tabela
-- --------------
-- Prefixo `pedrocore_` mantido: o schema inteiro usa este prefixo, e criar UMA
-- tabela com outro deixaria duas convencoes convivendo. Branding nao justifica
-- migration destrutiva.
--
-- Aditiva. Nenhuma migration anterior foi tocada.

CREATE TABLE IF NOT EXISTS pedrocore_projects (
    -- Isolamento de projeto e CHAVE. `project_id` unico por construcao: duas
    -- linhas nao podem disputar a mesma identidade, e nenhum `WHERE`
    -- esquecido pode confundir um projeto com outro.
    project_id                      VARCHAR(64)  NOT NULL,
    display_name                    VARCHAR(96)  NOT NULL,
    local_path                      VARCHAR(512),
    -- Metadado. Nada e buscado, clonado ou autenticado a partir daqui: nao ha
    -- sincronizacao com GitHub nesta versao.
    repository_url                  VARCHAR(512),
    status                          VARCHAR(16)  NOT NULL DEFAULT 'ACTIVE',
    created_at                      TIMESTAMPTZ  NOT NULL,
    updated_at                      TIMESTAMPTZ  NOT NULL,
    -- Ponteiro, nao conteudo. O manifesto continua morando no Project Context.
    capability_manifest_reference   VARCHAR(128),
    PRIMARY KEY (project_id)
);

-- Estado minimo, imposto tambem pelo banco: um INSERT direto tambem esbarra.
-- Arquivar nunca apaga, entao `status` so tem estes dois valores.
ALTER TABLE pedrocore_projects
    DROP CONSTRAINT IF EXISTS pedrocore_projects_status_valido;
ALTER TABLE pedrocore_projects
    ADD CONSTRAINT pedrocore_projects_status_valido CHECK (
        status IN ('ACTIVE', 'ARCHIVED')
    );

-- O id e normalizado antes de chegar aqui. A guarda no banco existe porque um
-- dump reconstruido entra pelo banco, e um id com separador de caminho e
-- exatamente o que nao pode virar identidade de isolamento.
ALTER TABLE pedrocore_projects
    DROP CONSTRAINT IF EXISTS pedrocore_projects_id_canonico;
ALTER TABLE pedrocore_projects
    ADD CONSTRAINT pedrocore_projects_id_canonico CHECK (
        project_id ~ '^[a-z0-9][a-z0-9_-]{1,62}[a-z0-9]$'
    );

CREATE INDEX IF NOT EXISTS idx_pedrocore_projects_status
    ON pedrocore_projects (status);

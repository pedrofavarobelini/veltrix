-- Stage R3 do Risk Engine V2 — métrica quantitativa de blast radius.
--
-- Aditiva e NULLABLE de propósito. Registros gravados pelo Stage R2 não têm
-- métrica, e forçar um default numérico neles seria inventar um alcance que
-- ninguém mediu. `NULL` diz a verdade: "esta análise é anterior à métrica".
--
-- A `0009` não foi alterada. Migration já aplicada tem checksum registrado, e
-- editá-la faria o runner recusar o banco inteiro na próxima execução.

ALTER TABLE pedrocore_risk_analyses
    ADD COLUMN IF NOT EXISTS blast_metric_version VARCHAR(64);

-- Contagem por fronteira, para que o número seja conferível item a item.
ALTER TABLE pedrocore_risk_analyses
    ADD COLUMN IF NOT EXISTS blast_boundary_counts JSONB;

-- Quantas fronteiras distintas foram tocadas (0-8).
ALTER TABLE pedrocore_risk_analyses
    ADD COLUMN IF NOT EXISTS blast_boundary_breadth INTEGER;

-- Quantos itens distintos, somados entre fronteiras.
ALTER TABLE pedrocore_risk_analyses
    ADD COLUMN IF NOT EXISTS blast_item_extent INTEGER;

-- As colunas são consistentes entre si ou todas ausentes. Um registro com
-- amplitude preenchida e extensão nula descreveria um alcance impossível.
ALTER TABLE pedrocore_risk_analyses
    DROP CONSTRAINT IF EXISTS pedrocore_risk_blast_metric_check;

ALTER TABLE pedrocore_risk_analyses
    ADD CONSTRAINT pedrocore_risk_blast_metric_check CHECK (
        (
            blast_metric_version IS NULL
            AND blast_boundary_breadth IS NULL
            AND blast_item_extent IS NULL
        )
        OR (
            blast_metric_version IS NOT NULL
            AND blast_boundary_breadth BETWEEN 0 AND 8
            AND blast_item_extent >= 0
            AND blast_item_extent >= blast_boundary_breadth
        )
    );

-- Ordenar análises por alcance é a pergunta que a métrica veio responder.
-- Parcial: registros legados não entram no índice e não o encarecem.
CREATE INDEX IF NOT EXISTS pedrocore_risk_analyses_blast_extent_idx
    ON pedrocore_risk_analyses (project_id, blast_item_extent DESC)
    WHERE blast_item_extent IS NOT NULL;

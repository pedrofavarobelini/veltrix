ALTER TABLE pedrocore_operational_memory
    ADD COLUMN IF NOT EXISTS search_document TEXT NOT NULL DEFAULT '';

UPDATE pedrocore_operational_memory
SET search_document = lower(
    concat_ws(
        ' ',
        pattern_type,
        payload #>> '{pattern,pattern_key}',
        payload #>> '{pattern,task_type}',
        payload #>> '{pattern,summary}'
    )
)
WHERE search_document = '';

ALTER TABLE pedrocore_operational_memory
    ADD COLUMN IF NOT EXISTS search_vector TSVECTOR
    GENERATED ALWAYS AS (to_tsvector('simple', search_document)) STORED;

CREATE INDEX IF NOT EXISTS idx_pedrocore_memory_fts
    ON pedrocore_operational_memory USING GIN (search_vector);

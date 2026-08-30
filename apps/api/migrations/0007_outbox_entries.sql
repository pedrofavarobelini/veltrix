-- Final Hardening — outbox durável.
--
-- O outbox existe para sobreviver ao processo que o escreveu. Um outbox que
-- só vive em memória protege contra o servidor cair, mas não contra o
-- CONSUMIDOR cair — e é aí que o dado se perde: o processo grava a entrega
-- pendente, morre antes de entregar, e a fila some com ele.
--
-- Esta tabela é de estado OPERACIONAL de entrega, não de governança: não há
-- elegibilidade, autorização nem propósito de treino, e a ausência é
-- deliberada. Um item aqui é "preciso enviar isto", nunca "isto pode treinar".

CREATE TABLE IF NOT EXISTS pedrocore_outbox_entries (
    entry_id VARCHAR(128) PRIMARY KEY,
    project_id VARCHAR(128) NOT NULL,

    -- A chave que faz o reenvio ser RECONHECIDO em vez de duplicado. Escolhida
    -- uma vez, na gravação, e nunca regerada: regerar por tentativa produziria
    -- uma duplicata a cada retry, que é o oposto do objetivo.
    idempotency_key VARCHAR(128) NOT NULL,

    payload JSONB NOT NULL,
    state VARCHAR(32) NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    created_at TIMESTAMPTZ NOT NULL,
    next_attempt_at TIMESTAMPTZ NOT NULL,

    -- Código sanitizado do último erro. Nunca a mensagem crua do transporte:
    -- ela pode carregar URL com credencial, corpo de resposta ou trecho de
    -- payload — exatamente o que não pode ficar gravado.
    last_error_code VARCHAR(128),

    delivered_at TIMESTAMPTZ,

    CONSTRAINT pedrocore_outbox_state_check CHECK (
        state IN ('pending', 'in_flight', 'delivered', 'dead_letter')
    ),
    CONSTRAINT pedrocore_outbox_attempts_check CHECK (
        attempts >= 0 AND attempts <= max_attempts
    ),
    -- Entregue exige carimbo de entrega; não entregue não pode ter um. Sem
    -- isto, um bug de transição produziria linhas que dizem duas coisas
    -- contraditórias sobre o mesmo fato.
    CONSTRAINT pedrocore_outbox_delivered_consistency_check CHECK (
        (state = 'delivered' AND delivered_at IS NOT NULL)
        OR (state <> 'delivered' AND delivered_at IS NULL)
    )
);

-- A varredura quente do despachante: pendentes já vencidos, em ordem de
-- vencimento. Parcial porque entregues e dead-letter nunca são varridos, e
-- mantê-los no índice só encareceria a escrita.
CREATE INDEX IF NOT EXISTS pedrocore_outbox_due_idx
    ON pedrocore_outbox_entries (next_attempt_at, entry_id)
    WHERE state = 'pending';

-- Reconciliação e auditoria por projeto.
CREATE INDEX IF NOT EXISTS pedrocore_outbox_project_idx
    ON pedrocore_outbox_entries (project_id, state);

-- Dead-letter é uma fila de revisão humana: precisa ser listável sem varrer
-- a tabela inteira.
CREATE INDEX IF NOT EXISTS pedrocore_outbox_dead_letter_idx
    ON pedrocore_outbox_entries (project_id, entry_id)
    WHERE state = 'dead_letter';

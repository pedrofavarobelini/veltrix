"""Outbox durável — sobrevive ao restart do processo consumidor.

Por que o outbox em memória não bastava
---------------------------------------

A Era 6 entregou retry, backoff e dead-letter, e provou a propriedade
"PedroCore fora do ar não derruba o consumidor". Mas provou só metade dela.

O outbox em memória protege contra o SERVIDOR cair. Ele não protege contra o
CONSUMIDOR cair — e é justamente aí que o dado se perde: o processo grava a
entrega pendente, morre antes de entregar, e a fila inteira desaparece com ele.
O consumidor volta achando que enviou.

Um outbox que não sobrevive ao próprio processo é um buffer, não um outbox.

Duas formas de durabilidade
---------------------------

Seguem o mesmo interruptor de persistência do resto do sistema, e não um
terceiro jeito de configurar armazenamento:

- `DurableOutboxStore` — um arquivo JSON no disco. Simples, sem dependência,
  e o que torna o teste de restart executável em qualquer ambiente.
- `PostgreSQLOutboxStore` — mesmo banco do resto do PedroCore, para produção.

Nenhum broker. Nenhum Redis, Kafka ou RabbitMQ. A entrega eventual de eventos
pequenos e idempotentes não precisa de fila distribuída — precisa de um lugar
que sobreviva a um `kill -9`.

Escrita atômica
---------------

O arquivo é escrito em um temporário e movido por `os.replace`, que é atômico
no mesmo sistema de arquivos. Escrever direto no destino tem uma janela em que
o arquivo está truncado: se o processo morre exatamente ali, o outbox volta
corrompido — e o modo de falha que ele existe para resolver seria a causa da
perda.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from app.modules.resilience.outbox import DeliveryState, OutboxEntry, OutboxStore
from app.modules.resilience.storage import (
    DurableStorageCorruptionError,
    DurableStorageDegradedError,
    load_json_records,
    parse_records,
)


class DurableOutboxStore(OutboxStore):
    """Outbox em arquivo JSON. Carrega do disco na construção.

    O carregamento no `__init__` é o que torna o restart testável de verdade:
    uma instância nova, apontando para o mesmo diretório, enxerga o que a
    anterior gravou — que é exatamente o que acontece quando o processo volta.
    """

    def __init__(self, directory: str | Path, *, name: str = "outbox") -> None:
        super().__init__()
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._file = self._directory / f"{name}.json"
        # Degradado significa: li algo ilegível e não vou gravar por cima.
        self._degraded: DurableStorageCorruptionError | None = None
        self._load()

    # -- estado -----------------------------------------------------------

    @property
    def degraded(self) -> bool:
        """A camada de entrega está bloqueada por corrupção detectada?"""
        return self._degraded is not None

    @property
    def corruption(self) -> DurableStorageCorruptionError | None:
        """Diagnóstico sanitizado da corrupção, quando houver."""
        return self._degraded

    def _require_writable(self) -> None:
        if self._degraded is not None:
            raise DurableStorageDegradedError(self._file)

    # -- persistência -----------------------------------------------------

    def _load(self) -> None:
        """Carrega o arquivo, ou entra em modo degradado.

        Arquivo ilegível NÃO vira fila vazia. Fingir vazio faria o consumidor
        concluir que não há nada pendente e a próxima escrita apagaria entregas
        que ninguém chegou a ver — corrupção recuperável virando perda
        definitiva.
        """
        try:
            raw = load_json_records(self._file)
            if raw is None:
                return
            for entry in parse_records(self._file, raw, OutboxEntry):
                self._entries[entry.entry_id] = entry
        except DurableStorageCorruptionError as error:
            # O store fica vazio em memória, mas marcado: nada será gravado por
            # cima e toda escrita é recusada explicitamente.
            self._entries.clear()
            self._degraded = error

    def _persist(self) -> None:
        with self._lock:
            payload = [entry.model_dump(mode="json") for entry in self._entries.values()]
        temporary = self._file.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Atômico no mesmo sistema de arquivos: ou o destino tem o conteúdo
        # antigo inteiro, ou o novo inteiro. Nunca um arquivo pela metade.
        os.replace(temporary, self._file)

    # -- escrita ----------------------------------------------------------

    def enqueue(self, **kwargs) -> OutboxEntry:
        self._require_writable()
        entry = super().enqueue(**kwargs)
        self._persist()
        return entry

    def _replace(self, entry: OutboxEntry) -> None:
        self._require_writable()
        super()._replace(entry)
        self._persist()

    def clear(self) -> None:
        """Limpa o store. Permitida mesmo degradado: é a saída da quarentena.

        Depois que alguém revisou a cópia preservada, `clear()` é o gesto
        explícito de "reconheci a perda e quero um store limpo". Bloqueá-la
        deixaria o consumidor sem caminho de recuperação.
        """
        self._degraded = None
        super().clear()
        self._persist()


_INSERT = """
INSERT INTO pedrocore_outbox_entries (
    entry_id, project_id, idempotency_key, payload, state, attempts,
    max_attempts, created_at, next_attempt_at, last_error_code, delivered_at
) VALUES (
    %(entry_id)s, %(project_id)s, %(idempotency_key)s, %(payload)s, %(state)s,
    %(attempts)s, %(max_attempts)s, %(created_at)s, %(next_attempt_at)s,
    %(last_error_code)s, %(delivered_at)s
)
ON CONFLICT (entry_id) DO NOTHING
"""

_UPDATE = """
UPDATE pedrocore_outbox_entries SET
    state = %(state)s,
    attempts = %(attempts)s,
    next_attempt_at = %(next_attempt_at)s,
    last_error_code = %(last_error_code)s,
    delivered_at = %(delivered_at)s
WHERE entry_id = %(entry_id)s
"""

_COLUMNS = """
    entry_id, project_id, idempotency_key, payload, state, attempts,
    max_attempts, created_at, next_attempt_at, last_error_code, delivered_at
"""


def _row_to_entry(row: tuple) -> OutboxEntry:
    return OutboxEntry(
        entry_id=row[0],
        project_id=row[1],
        idempotency_key=row[2],
        payload=row[3] or {},
        state=DeliveryState(row[4]),
        attempts=row[5],
        max_attempts=row[6],
        created_at=row[7],
        next_attempt_at=row[8],
        last_error_code=row[9],
        delivered_at=row[10],
    )


def _params(entry: OutboxEntry) -> dict:
    return {
        "entry_id": entry.entry_id,
        "project_id": entry.project_id,
        "idempotency_key": entry.idempotency_key,
        "payload": Jsonb(entry.payload),
        "state": entry.state.value,
        "attempts": entry.attempts,
        "max_attempts": entry.max_attempts,
        "created_at": entry.created_at,
        "next_attempt_at": entry.next_attempt_at,
        "last_error_code": entry.last_error_code,
        "delivered_at": entry.delivered_at,
    }


class PostgreSQLOutboxStore(OutboxStore):
    """Outbox em PostgreSQL, para produção.

    Lê o estado do banco a cada consulta em vez de manter cópia local: dois
    workers na mesma fila precisam enxergar o mesmo estado, e um cache em
    processo faria cada um trabalhar sobre uma versão diferente da verdade.
    """

    def __init__(self, database_url: str) -> None:
        super().__init__()
        self._database_url = database_url

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._database_url)

    def enqueue(
        self,
        *,
        entry_id: str,
        project_id: str,
        idempotency_key: str,
        payload: dict,
        now: datetime | None = None,
        max_attempts: int = 5,
    ) -> OutboxEntry:
        existing = self.get(entry_id)
        if existing is not None:
            return existing
        entry = OutboxEntry(
            entry_id=entry_id,
            project_id=project_id,
            idempotency_key=idempotency_key,
            payload=payload,
            created_at=now or datetime.now(),
            next_attempt_at=now or datetime.now(),
            max_attempts=max_attempts,
        )
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(_INSERT, _params(entry))
        return entry

    def get(self, entry_id: str) -> OutboxEntry | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_COLUMNS} FROM pedrocore_outbox_entries WHERE entry_id = %s",
                (entry_id,),
            )
            row = cursor.fetchone()
            return _row_to_entry(row) if row else None

    def due(self, *, now: datetime | None = None) -> list[OutboxEntry]:
        moment = now or datetime.now()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_COLUMNS} FROM pedrocore_outbox_entries "
                "WHERE state = 'pending' AND next_attempt_at <= %s "
                "ORDER BY next_attempt_at, entry_id",
                (moment,),
            )
            return [_row_to_entry(row) for row in cursor.fetchall()]

    def pending_count(self) -> int:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM pedrocore_outbox_entries WHERE state = 'pending'"
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def dead_letters(self) -> list[OutboxEntry]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_COLUMNS} FROM pedrocore_outbox_entries "
                "WHERE state = 'dead_letter' ORDER BY entry_id"
            )
            return [_row_to_entry(row) for row in cursor.fetchall()]

    def all_entries(self) -> list[OutboxEntry]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_COLUMNS} FROM pedrocore_outbox_entries ORDER BY entry_id"
            )
            return [_row_to_entry(row) for row in cursor.fetchall()]

    def _replace(self, entry: OutboxEntry) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(_UPDATE, _params(entry))

    def clear(self) -> None:
        """Apaga tudo. Existe para QA isolado, nunca para produção."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM pedrocore_outbox_entries")

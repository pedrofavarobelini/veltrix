"""Persistencia do Evidence Registry.

Segue o padrao ja estabelecido em `report_memory` e `training_data`: um
`Protocol`, uma implementacao em memoria e uma PostgreSQL, escolhidas pela
mesma variavel de ambiente. Reaproveitar o padrao (e a mesma URL de banco)
evita um terceiro jeito de configurar persistencia no mesmo processo.

Fail-closed: com persistencia `off`, o registro NAO cai para memoria. Um store
efemero lido como se fosse o real faria uma auditoria de evidencia reportar
numeros que nunca existiram.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import psycopg
from psycopg.types.json import Jsonb

from app.modules.evidence_platform.schemas import EvidenceKind, EvidenceRecord


@runtime_checkable
class EvidenceRepository(Protocol):
    def add(self, record: EvidenceRecord) -> bool:
        """`False` quando o registro ja existia — duplicata, nao erro."""
        ...

    def get(self, project_id: str, evidence_record_id: str) -> EvidenceRecord | None: ...

    def find_by_fingerprint(
        self, project_id: str, kind: EvidenceKind, fingerprint: str
    ) -> EvidenceRecord | None: ...

    def find_by_idempotency_key(
        self, project_id: str, idempotency_key: str
    ) -> EvidenceRecord | None: ...

    def list(
        self,
        project_id: str,
        *,
        kind: EvidenceKind | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[EvidenceRecord]: ...

    def count(self, project_id: str, *, kind: EvidenceKind | None = None) -> int: ...

    def clear(self) -> None: ...


def _matches(record: EvidenceRecord, kind: EvidenceKind | None) -> bool:
    return kind is None or record.kind is kind


class InMemoryEvidenceRepository:
    """Store em memoria. Usado em teste e no modo `memory` explicito."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], EvidenceRecord] = {}

    def add(self, record: EvidenceRecord) -> bool:
        key = (record.project_id, record.evidence_record_id)
        if key in self._records:
            return False
        self._records[key] = record.model_copy(deep=True)
        return True

    def get(self, project_id: str, evidence_record_id: str) -> EvidenceRecord | None:
        found = self._records.get((project_id, evidence_record_id))
        return found.model_copy(deep=True) if found else None

    def find_by_fingerprint(
        self, project_id: str, kind: EvidenceKind, fingerprint: str
    ) -> EvidenceRecord | None:
        for (record_project, _), record in self._records.items():
            if (
                record_project == project_id
                and record.kind is kind
                and record.fingerprint == fingerprint
            ):
                return record.model_copy(deep=True)
        return None

    def find_by_idempotency_key(
        self, project_id: str, idempotency_key: str
    ) -> EvidenceRecord | None:
        for (record_project, _), record in self._records.items():
            if record_project == project_id and record.idempotency_key == idempotency_key:
                return record.model_copy(deep=True)
        return None

    def list(
        self,
        project_id: str,
        *,
        kind: EvidenceKind | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[EvidenceRecord]:
        selected = [
            record.model_copy(deep=True)
            for (record_project, _), record in self._records.items()
            if record_project == project_id and _matches(record, kind)
        ]
        selected.sort(key=lambda item: (item.received_at, item.evidence_record_id))
        window = selected[offset:]
        return window[:limit] if limit is not None else window

    def count(self, project_id: str, *, kind: EvidenceKind | None = None) -> int:
        return sum(
            1
            for (record_project, _), record in self._records.items()
            if record_project == project_id and _matches(record, kind)
        )

    def clear(self) -> None:
        self._records.clear()


_INSERT = """
INSERT INTO pedrocore_evidence_records (
    evidence_record_id, project_id, producer_id, kind, event_id,
    correlation_id, idempotency_key, contract_version, fingerprint,
    submitted_at, received_at, policy_version, payload
) VALUES (
    %(evidence_record_id)s, %(project_id)s, %(producer_id)s, %(kind)s, %(event_id)s,
    %(correlation_id)s, %(idempotency_key)s, %(contract_version)s, %(fingerprint)s,
    %(submitted_at)s, %(received_at)s, %(policy_version)s, %(payload)s
)
ON CONFLICT DO NOTHING
"""

_COLUMNS = """
    evidence_record_id, project_id, producer_id, kind, event_id,
    correlation_id, idempotency_key, contract_version, fingerprint,
    submitted_at, received_at, policy_version, payload
"""


def _row_to_record(row: tuple) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_record_id=row[0],
        project_id=row[1],
        producer_id=row[2],
        kind=EvidenceKind(row[3]),
        event_id=row[4],
        correlation_id=row[5],
        idempotency_key=row[6],
        contract_version=row[7],
        fingerprint=row[8],
        submitted_at=row[9],
        received_at=row[10],
        policy_version=row[11],
        payload=row[12] or {},
    )


class PostgreSQLEvidenceRepository:
    """Store PostgreSQL. Isolamento de projeto e chave primaria, nao filtro."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._database_url)

    def add(self, record: EvidenceRecord) -> bool:
        payload = record.model_dump(mode="json")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                _INSERT,
                {
                    "evidence_record_id": record.evidence_record_id,
                    "project_id": record.project_id,
                    "producer_id": record.producer_id,
                    "kind": record.kind.value,
                    "event_id": record.event_id,
                    "correlation_id": record.correlation_id,
                    "idempotency_key": record.idempotency_key,
                    "contract_version": record.contract_version,
                    "fingerprint": record.fingerprint,
                    "submitted_at": record.submitted_at,
                    "received_at": record.received_at,
                    "policy_version": record.policy_version,
                    "payload": Jsonb(payload["payload"]),
                },
            )
            return cursor.rowcount == 1

    def get(self, project_id: str, evidence_record_id: str) -> EvidenceRecord | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_COLUMNS} FROM pedrocore_evidence_records "
                "WHERE project_id = %s AND evidence_record_id = %s",
                (project_id, evidence_record_id),
            )
            row = cursor.fetchone()
            return _row_to_record(row) if row else None

    def find_by_fingerprint(
        self, project_id: str, kind: EvidenceKind, fingerprint: str
    ) -> EvidenceRecord | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_COLUMNS} FROM pedrocore_evidence_records "
                "WHERE project_id = %s AND kind = %s AND fingerprint = %s LIMIT 1",
                (project_id, kind.value, fingerprint),
            )
            row = cursor.fetchone()
            return _row_to_record(row) if row else None

    def find_by_idempotency_key(
        self, project_id: str, idempotency_key: str
    ) -> EvidenceRecord | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_COLUMNS} FROM pedrocore_evidence_records "
                "WHERE project_id = %s AND idempotency_key = %s LIMIT 1",
                (project_id, idempotency_key),
            )
            row = cursor.fetchone()
            return _row_to_record(row) if row else None

    def list(
        self,
        project_id: str,
        *,
        kind: EvidenceKind | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[EvidenceRecord]:
        clauses = ["project_id = %s"]
        params: list[object] = [project_id]
        if kind is not None:
            clauses.append("kind = %s")
            params.append(kind.value)
        query = (
            f"SELECT {_COLUMNS} FROM pedrocore_evidence_records "
            f"WHERE {' AND '.join(clauses)} "
            "ORDER BY received_at, evidence_record_id"
        )
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        if offset:
            query += " OFFSET %s"
            params.append(offset)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, tuple(params))
            return [_row_to_record(row) for row in cursor.fetchall()]

    def count(self, project_id: str, *, kind: EvidenceKind | None = None) -> int:
        clauses = ["project_id = %s"]
        params: list[object] = [project_id]
        if kind is not None:
            clauses.append("kind = %s")
            params.append(kind.value)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM pedrocore_evidence_records "
                f"WHERE {' AND '.join(clauses)}",
                tuple(params),
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def clear(self) -> None:
        """Apaga TODOS os registros. Existe para QA isolado, nunca para producao."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM pedrocore_evidence_records")

from __future__ import annotations

from typing import Protocol, runtime_checkable

import psycopg
from psycopg import Connection
from psycopg.types.json import Jsonb

from app.modules.report_memory.repository import (
    ReportMemoryRepositoryConfigurationError,
    ReportMemoryRepositoryError,
)
from app.modules.training_data.schemas import (
    CandidateLifecycle,
    TrainingCandidateRecord,
    TrainingPurpose,
    TrainingSourceType,
)


@runtime_checkable
class TrainingCandidateRepository(Protocol):
    def add(self, record: TrainingCandidateRecord) -> bool: ...

    def get(self, project_id: str, candidate_id: str) -> TrainingCandidateRecord | None: ...

    def list(
        self,
        project_id: str,
        *,
        lifecycle: CandidateLifecycle | None = None,
        source_type: TrainingSourceType | None = None,
        training_purpose: TrainingPurpose | None = None,
        task_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TrainingCandidateRecord]: ...

    def count(
        self,
        project_id: str,
        *,
        lifecycle: CandidateLifecycle | None = None,
        source_type: TrainingSourceType | None = None,
        training_purpose: TrainingPurpose | None = None,
        task_type: str | None = None,
    ) -> int: ...

    def replace(
        self,
        record: TrainingCandidateRecord,
        *,
        expected_lifecycles: set[CandidateLifecycle],
    ) -> bool: ...

    def clear(self) -> None: ...


def _matches(
    record: TrainingCandidateRecord,
    *,
    lifecycle: CandidateLifecycle | None,
    source_type: TrainingSourceType | None,
    training_purpose: TrainingPurpose | None,
    task_type: str | None,
) -> bool:
    return (
        (lifecycle is None or record.lifecycle is lifecycle)
        and (source_type is None or record.source_type is source_type)
        and (training_purpose is None or record.training_purpose is training_purpose)
        and (task_type is None or record.task_type == task_type)
    )


class InMemoryTrainingCandidateRepository:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], TrainingCandidateRecord] = {}

    def add(self, record: TrainingCandidateRecord) -> bool:
        key = (record.project_id, record.candidate_id)
        if key in self._records:
            return False
        self._records[key] = record.model_copy(deep=True)
        return True

    def get(self, project_id: str, candidate_id: str) -> TrainingCandidateRecord | None:
        record = self._records.get((project_id, candidate_id))
        return record.model_copy(deep=True) if record is not None else None

    def list(
        self,
        project_id: str,
        *,
        lifecycle: CandidateLifecycle | None = None,
        source_type: TrainingSourceType | None = None,
        training_purpose: TrainingPurpose | None = None,
        task_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TrainingCandidateRecord]:
        records = sorted(
            (
                item.model_copy(deep=True)
                for (project, _candidate_id), item in self._records.items()
                if project == project_id
                and _matches(
                    item,
                    lifecycle=lifecycle,
                    source_type=source_type,
                    training_purpose=training_purpose,
                    task_type=task_type,
                )
            ),
            key=lambda item: (item.created_at, item.candidate_id),
        )
        records = records[offset:]
        return records[:limit] if limit is not None else records

    def count(
        self,
        project_id: str,
        *,
        lifecycle: CandidateLifecycle | None = None,
        source_type: TrainingSourceType | None = None,
        training_purpose: TrainingPurpose | None = None,
        task_type: str | None = None,
    ) -> int:
        return len(
            self.list(
                project_id,
                lifecycle=lifecycle,
                source_type=source_type,
                training_purpose=training_purpose,
                task_type=task_type,
            )
        )

    def replace(
        self,
        record: TrainingCandidateRecord,
        *,
        expected_lifecycles: set[CandidateLifecycle],
    ) -> bool:
        key = (record.project_id, record.candidate_id)
        current = self._records.get(key)
        if current is None or current.lifecycle not in expected_lifecycles:
            return False
        self._records[key] = record.model_copy(deep=True)
        return True

    def clear(self) -> None:
        self._records.clear()


class PostgreSQLTrainingCandidateRepository:
    """Candidate Store no mesmo PostgreSQL operacional, criado só por migração."""

    def __init__(self, database_url: str) -> None:
        if not database_url.strip():
            raise ReportMemoryRepositoryConfigurationError(
                "PEDROCORE_REPORT_MEMORY_DATABASE_URL é obrigatória no modo postgresql."
            )
        self._database_url = database_url

    def _connect(self) -> Connection:
        try:
            return psycopg.connect(self._database_url, connect_timeout=5)
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("PostgreSQL indisponível.") from exc

    @staticmethod
    def _values(record: TrainingCandidateRecord) -> dict[str, object]:
        return {
            "candidate_id": record.candidate_id,
            "project_id": record.project_id,
            "source_type": record.source_type.value,
            "source_id": record.source_id,
            "source_reference_hash": record.source_reference_hash,
            "fingerprint": record.fingerprint,
            "task_type": record.task_type,
            "training_purpose": record.training_purpose.value,
            "lifecycle": record.lifecycle.value,
            "eligibility": record.eligibility.value,
            "privacy_classification": record.privacy_classification.value,
            "policy_version": record.policy_version,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "payload": Jsonb(record.model_dump(mode="json")),
        }

    def add(self, record: TrainingCandidateRecord) -> bool:
        statement = """
            INSERT INTO pedrocore_training_candidates (
                candidate_id, project_id, source_type, source_id,
                source_reference_hash, fingerprint, task_type, training_purpose,
                lifecycle, eligibility, privacy_classification, policy_version,
                created_at, updated_at, payload
            ) VALUES (
                %(candidate_id)s, %(project_id)s, %(source_type)s, %(source_id)s,
                %(source_reference_hash)s, %(fingerprint)s, %(task_type)s,
                %(training_purpose)s, %(lifecycle)s, %(eligibility)s,
                %(privacy_classification)s, %(policy_version)s, %(created_at)s,
                %(updated_at)s, %(payload)s
            ) ON CONFLICT (project_id, candidate_id) DO NOTHING
        """
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(statement, self._values(record))
                return cursor.rowcount == 1
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao persistir training candidate.") from exc

    def get(self, project_id: str, candidate_id: str) -> TrainingCandidateRecord | None:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT payload FROM pedrocore_training_candidates
                    WHERE project_id = %s AND candidate_id = %s""",
                    (project_id, candidate_id),
                )
                row = cursor.fetchone()
                return TrainingCandidateRecord.model_validate(row[0]) if row else None
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao consultar training candidate.") from exc

    def list(
        self,
        project_id: str,
        *,
        lifecycle: CandidateLifecycle | None = None,
        source_type: TrainingSourceType | None = None,
        training_purpose: TrainingPurpose | None = None,
        task_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TrainingCandidateRecord]:
        statement = """SELECT payload FROM pedrocore_training_candidates
            WHERE project_id = %s
              AND lifecycle = COALESCE(%s, lifecycle)
              AND source_type = COALESCE(%s, source_type)
              AND training_purpose = COALESCE(%s, training_purpose)
              AND task_type = COALESCE(%s, task_type)
            ORDER BY created_at ASC, candidate_id ASC"""
        params: list[object] = [
            project_id,
            lifecycle.value if lifecycle else None,
            source_type.value if source_type else None,
            training_purpose.value if training_purpose else None,
            task_type,
        ]
        if limit is not None:
            statement += " LIMIT %s"
            params.append(limit)
        if offset:
            statement += " OFFSET %s"
            params.append(offset)
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(statement, params)
                return [TrainingCandidateRecord.model_validate(row[0]) for row in cursor]
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao listar training candidates.") from exc

    def count(
        self,
        project_id: str,
        *,
        lifecycle: CandidateLifecycle | None = None,
        source_type: TrainingSourceType | None = None,
        training_purpose: TrainingPurpose | None = None,
        task_type: str | None = None,
    ) -> int:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT COUNT(*) FROM pedrocore_training_candidates
                    WHERE project_id = %s
                      AND lifecycle = COALESCE(%s, lifecycle)
                      AND source_type = COALESCE(%s, source_type)
                      AND training_purpose = COALESCE(%s, training_purpose)
                      AND task_type = COALESCE(%s, task_type)""",
                    (
                        project_id,
                        lifecycle.value if lifecycle else None,
                        source_type.value if source_type else None,
                        training_purpose.value if training_purpose else None,
                        task_type,
                    ),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao contar training candidates.") from exc

    def replace(
        self,
        record: TrainingCandidateRecord,
        *,
        expected_lifecycles: set[CandidateLifecycle],
    ) -> bool:
        if not expected_lifecycles:
            return False
        values = self._values(record)
        values["expected_lifecycles"] = [item.value for item in expected_lifecycles]
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE pedrocore_training_candidates SET
                        source_id = %(source_id)s,
                        lifecycle = %(lifecycle)s,
                        eligibility = %(eligibility)s,
                        privacy_classification = %(privacy_classification)s,
                        updated_at = %(updated_at)s,
                        payload = %(payload)s
                    WHERE project_id = %(project_id)s
                      AND candidate_id = %(candidate_id)s
                      AND lifecycle = ANY(%(expected_lifecycles)s)""",
                    values,
                )
                return cursor.rowcount == 1
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao atualizar training candidate.") from exc

    def clear(self) -> None:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute("DELETE FROM pedrocore_training_candidates")
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao limpar training candidates de teste.") from exc

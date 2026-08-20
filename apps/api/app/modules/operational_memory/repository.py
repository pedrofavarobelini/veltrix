from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

import psycopg
from psycopg import Connection
from psycopg.types.json import Jsonb

from app.modules.operational_memory.schemas import (
    LearningCandidate,
    MemoryLifecycle,
    OperationalMemoryEntry,
    PatternType,
)
from app.modules.report_memory.repository import (
    ReportMemoryRepositoryConfigurationError,
    ReportMemoryRepositoryError,
)


@runtime_checkable
class OperationalMemoryRepository(Protocol):
    def get_candidate(self, project_id: str, candidate_id: str) -> LearningCandidate | None: ...

    def list_candidates_for_pattern(
        self, project_id: str, pattern_id: str
    ) -> list[LearningCandidate]: ...

    def get_memory_by_pattern(
        self, project_id: str, pattern_id: str
    ) -> OperationalMemoryEntry | None: ...

    def save_evaluation(
        self, candidate: LearningCandidate, memory: OperationalMemoryEntry
    ) -> bool: ...

    def list_memory(
        self,
        project_id: str,
        *,
        pattern_type: PatternType | None = None,
        lifecycle: MemoryLifecycle | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[OperationalMemoryEntry]: ...

    def count_memory(
        self,
        project_id: str,
        *,
        pattern_type: PatternType | None = None,
        lifecycle: MemoryLifecycle | None = None,
    ) -> int: ...

    def delete_project(self, project_id: str) -> tuple[int, int]: ...

    def delete_expired(self, now: datetime | None = None) -> tuple[int, int]: ...

    def clear(self) -> None: ...


class InMemoryOperationalMemoryRepository:
    def __init__(self) -> None:
        self._candidates: dict[str, dict[str, LearningCandidate]] = {}
        self._memories: dict[str, dict[str, OperationalMemoryEntry]] = {}

    def get_candidate(self, project_id: str, candidate_id: str) -> LearningCandidate | None:
        return self._candidates.get(project_id, {}).get(candidate_id)

    def list_candidates_for_pattern(
        self, project_id: str, pattern_id: str
    ) -> list[LearningCandidate]:
        return sorted(
            [
                item
                for item in self._candidates.get(project_id, {}).values()
                if item.pattern_id == pattern_id
            ],
            key=lambda item: (item.created_at, item.candidate_id),
        )

    def get_memory_by_pattern(
        self, project_id: str, pattern_id: str
    ) -> OperationalMemoryEntry | None:
        return next(
            (
                item
                for item in self._memories.get(project_id, {}).values()
                if item.pattern.pattern_id == pattern_id
            ),
            None,
        )

    def save_evaluation(self, candidate: LearningCandidate, memory: OperationalMemoryEntry) -> bool:
        candidates = self._candidates.setdefault(candidate.project_id, {})
        if candidate.candidate_id in candidates:
            return False
        candidates[candidate.candidate_id] = candidate
        self._memories.setdefault(memory.project_id, {})[memory.memory_id] = memory
        return True

    def list_memory(
        self,
        project_id: str,
        *,
        pattern_type: PatternType | None = None,
        lifecycle: MemoryLifecycle | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[OperationalMemoryEntry]:
        items = sorted(
            [
                item
                for item in self._memories.get(project_id, {}).values()
                if (pattern_type is None or item.pattern.pattern_type is pattern_type)
                and (lifecycle is None or item.lifecycle is lifecycle)
            ],
            key=lambda item: (item.updated_at, item.memory_id),
            reverse=True,
        )
        if offset:
            items = items[offset:]
        return items[:limit] if limit is not None else items

    def count_memory(
        self,
        project_id: str,
        *,
        pattern_type: PatternType | None = None,
        lifecycle: MemoryLifecycle | None = None,
    ) -> int:
        return len(
            self.list_memory(
                project_id,
                pattern_type=pattern_type,
                lifecycle=lifecycle,
            )
        )

    def delete_project(self, project_id: str) -> tuple[int, int]:
        candidates = len(self._candidates.pop(project_id, {}))
        memories = len(self._memories.pop(project_id, {}))
        return candidates, memories

    def delete_expired(self, now: datetime | None = None) -> tuple[int, int]:
        reference = now or datetime.now(timezone.utc)
        deleted_candidates = 0
        deleted_memories = 0
        for project_id, candidates in list(self._candidates.items()):
            retained = {
                key: item for key, item in candidates.items() if item.retention_until > reference
            }
            deleted_candidates += len(candidates) - len(retained)
            if retained:
                self._candidates[project_id] = retained
            else:
                self._candidates.pop(project_id, None)
        for project_id, memories in list(self._memories.items()):
            retained = {
                key: item for key, item in memories.items() if item.retention_until > reference
            }
            deleted_memories += len(memories) - len(retained)
            if retained:
                self._memories[project_id] = retained
            else:
                self._memories.pop(project_id, None)
        return deleted_candidates, deleted_memories

    def clear(self) -> None:
        self._candidates.clear()
        self._memories.clear()


class LocalJsonOperationalMemoryRepository(InMemoryOperationalMemoryRepository):
    """Persistência dev/test em um documento por projeto."""

    def __init__(self, directory: str | Path) -> None:
        super().__init__()
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._load_all()

    def _file_for(self, project_id: str) -> Path:
        safe_name = "".join(
            char if char.isalnum() or char in {"-", "_"} else "_" for char in project_id
        )
        return self._directory / f"{safe_name}.json"

    def _load_all(self) -> None:
        for file in self._directory.glob("*.json"):
            try:
                raw = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(raw, dict):
                continue
            candidates: dict[str, LearningCandidate] = {}
            memories: dict[str, OperationalMemoryEntry] = {}
            for value in raw.get("candidates", []):
                try:
                    candidate = LearningCandidate.model_validate(value)
                except Exception:
                    continue
                candidates[candidate.candidate_id] = candidate
            for value in raw.get("memories", []):
                try:
                    memory = OperationalMemoryEntry.model_validate(value)
                except Exception:
                    continue
                memories[memory.memory_id] = memory
            project_ids = {item.project_id for item in [*candidates.values(), *memories.values()]}
            if len(project_ids) != 1:
                continue
            project_id = project_ids.pop()
            self._candidates[project_id] = candidates
            self._memories[project_id] = memories

    def _persist_project(self, project_id: str) -> None:
        candidates = list(self._candidates.get(project_id, {}).values())
        memories = list(self._memories.get(project_id, {}).values())
        target = self._file_for(project_id)
        if not candidates and not memories:
            target.unlink(missing_ok=True)
            return
        target.write_text(
            json.dumps(
                {
                    "candidates": [item.model_dump(mode="json") for item in candidates],
                    "memories": [item.model_dump(mode="json") for item in memories],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def save_evaluation(self, candidate: LearningCandidate, memory: OperationalMemoryEntry) -> bool:
        saved = super().save_evaluation(candidate, memory)
        if saved:
            self._persist_project(candidate.project_id)
        return saved

    def delete_project(self, project_id: str) -> tuple[int, int]:
        deleted = super().delete_project(project_id)
        self._persist_project(project_id)
        return deleted

    def delete_expired(self, now: datetime | None = None) -> tuple[int, int]:
        projects = set(self._candidates) | set(self._memories)
        deleted = super().delete_expired(now)
        for project_id in projects:
            self._persist_project(project_id)
        return deleted


class PostgreSQLOperationalMemoryRepository:
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

    def get_candidate(self, project_id: str, candidate_id: str) -> LearningCandidate | None:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT payload FROM pedrocore_learning_candidates
                    WHERE project_id = %s AND candidate_id = %s""",
                    (project_id, candidate_id),
                )
                row = cursor.fetchone()
                return LearningCandidate.model_validate(row[0]) if row else None
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao consultar learning candidate.") from exc

    def list_candidates_for_pattern(
        self, project_id: str, pattern_id: str
    ) -> list[LearningCandidate]:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT payload FROM pedrocore_learning_candidates
                    WHERE project_id = %s AND pattern_id = %s
                    ORDER BY created_at ASC, candidate_id ASC""",
                    (project_id, pattern_id),
                )
                return [LearningCandidate.model_validate(row[0]) for row in cursor]
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao listar learning candidates.") from exc

    def get_memory_by_pattern(
        self, project_id: str, pattern_id: str
    ) -> OperationalMemoryEntry | None:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT payload FROM pedrocore_operational_memory
                    WHERE project_id = %s AND pattern_id = %s""",
                    (project_id, pattern_id),
                )
                row = cursor.fetchone()
                return OperationalMemoryEntry.model_validate(row[0]) if row else None
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao consultar operational memory.") from exc

    def save_evaluation(self, candidate: LearningCandidate, memory: OperationalMemoryEntry) -> bool:
        candidate_values = candidate.model_dump(mode="python")
        candidate_values["pattern_type"] = candidate.pattern_type.value
        candidate_values["decision"] = candidate.decision.value
        candidate_values["payload"] = Jsonb(candidate.model_dump(mode="json"))
        memory_values = memory.model_dump(mode="python")
        memory_values["pattern_id"] = memory.pattern.pattern_id
        memory_values["pattern_type"] = memory.pattern.pattern_type.value
        memory_values["lifecycle"] = memory.lifecycle.value
        memory_values["payload"] = Jsonb(memory.model_dump(mode="json"))
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO pedrocore_learning_candidates (
                        candidate_id, project_id, pattern_id, pattern_type,
                        producer, decision, confidence, policy_version,
                        created_at, stored_at, retention_until, payload
                    ) VALUES (
                        %(candidate_id)s, %(project_id)s, %(pattern_id)s,
                        %(pattern_type)s, %(producer)s, %(decision)s,
                        %(confidence)s, %(policy_version)s, %(created_at)s,
                        %(stored_at)s, %(retention_until)s, %(payload)s
                    ) ON CONFLICT (project_id, candidate_id) DO NOTHING""",
                    candidate_values,
                )
                if cursor.rowcount != 1:
                    return False
                cursor.execute(
                    """INSERT INTO pedrocore_operational_memory (
                        memory_id, project_id, pattern_id, pattern_type,
                        lifecycle, confidence, sample_size, policy_version,
                        created_at, updated_at, retention_until, payload
                    ) VALUES (
                        %(memory_id)s, %(project_id)s, %(pattern_id)s,
                        %(pattern_type)s, %(lifecycle)s, %(confidence)s,
                        %(sample_size)s, %(policy_version)s, %(created_at)s,
                        %(updated_at)s, %(retention_until)s, %(payload)s
                    ) ON CONFLICT (project_id, pattern_id) DO UPDATE SET
                        lifecycle = EXCLUDED.lifecycle,
                        confidence = EXCLUDED.confidence,
                        sample_size = EXCLUDED.sample_size,
                        policy_version = EXCLUDED.policy_version,
                        updated_at = EXCLUDED.updated_at,
                        retention_until = EXCLUDED.retention_until,
                        payload = EXCLUDED.payload""",
                    memory_values,
                )
            return True
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError(
                "Falha ao persistir avaliação de Operational Memory."
            ) from exc

    def list_memory(
        self,
        project_id: str,
        *,
        pattern_type: PatternType | None = None,
        lifecycle: MemoryLifecycle | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[OperationalMemoryEntry]:
        statement = """SELECT payload FROM pedrocore_operational_memory
            WHERE project_id = %s
              AND pattern_type = COALESCE(%s, pattern_type)
              AND lifecycle = COALESCE(%s, lifecycle)
            ORDER BY updated_at DESC, memory_id ASC"""
        params: list[object] = [
            project_id,
            pattern_type.value if pattern_type else None,
            lifecycle.value if lifecycle else None,
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
                return [OperationalMemoryEntry.model_validate(row[0]) for row in cursor]
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao listar Operational Memory.") from exc

    def count_memory(
        self,
        project_id: str,
        *,
        pattern_type: PatternType | None = None,
        lifecycle: MemoryLifecycle | None = None,
    ) -> int:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT COUNT(*) FROM pedrocore_operational_memory
                    WHERE project_id = %s
                      AND pattern_type = COALESCE(%s, pattern_type)
                      AND lifecycle = COALESCE(%s, lifecycle)""",
                    (
                        project_id,
                        pattern_type.value if pattern_type else None,
                        lifecycle.value if lifecycle else None,
                    ),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao contar Operational Memory.") from exc

    def delete_project(self, project_id: str) -> tuple[int, int]:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM pedrocore_learning_candidates WHERE project_id = %s",
                    (project_id,),
                )
                candidates = cursor.rowcount
                cursor.execute(
                    "DELETE FROM pedrocore_operational_memory WHERE project_id = %s",
                    (project_id,),
                )
                memories = cursor.rowcount
                return candidates, memories
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError(
                "Falha ao excluir Operational Memory do projeto."
            ) from exc

    def delete_expired(self, now: datetime | None = None) -> tuple[int, int]:
        reference = now or datetime.now(timezone.utc)
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """DELETE FROM pedrocore_learning_candidates
                    WHERE retention_until <= %s""",
                    (reference,),
                )
                candidates = cursor.rowcount
                cursor.execute(
                    """DELETE FROM pedrocore_operational_memory
                    WHERE retention_until <= %s""",
                    (reference,),
                )
                memories = cursor.rowcount
                return candidates, memories
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError(
                "Falha ao aplicar retenção da Operational Memory."
            ) from exc

    def clear(self) -> None:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute("DELETE FROM pedrocore_learning_candidates")
                cursor.execute("DELETE FROM pedrocore_operational_memory")
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError(
                "Falha ao limpar Operational Memory de teste."
            ) from exc

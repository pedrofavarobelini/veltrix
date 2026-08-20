from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

import psycopg
from psycopg import Connection
from psycopg.types.json import Jsonb

from app.modules.interaction_outcomes.schemas import InteractionOutcome
from app.modules.report_memory.repository import (
    MAX_ENTRIES_PER_PROJECT,
    ReportMemoryRepositoryConfigurationError,
    ReportMemoryRepositoryError,
)


@runtime_checkable
class InteractionOutcomeRepository(Protocol):
    def add(self, outcome: InteractionOutcome) -> bool: ...

    def list(
        self,
        project_id: str,
        *,
        conversation_id: str | None = None,
        message_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[InteractionOutcome]: ...

    def count(
        self,
        project_id: str,
        *,
        conversation_id: str | None = None,
        message_id: str | None = None,
    ) -> int: ...

    def get(self, project_id: str, outcome_id: str) -> InteractionOutcome | None: ...

    def delete_project(self, project_id: str) -> int: ...

    def delete_expired(self, now: datetime | None = None) -> int: ...

    def clear(self) -> None: ...


def _expired(outcome: InteractionOutcome, now: datetime) -> bool:
    return outcome.retention_until <= now


class InMemoryInteractionOutcomeRepository:
    """Repositório volátil de dev/test, com o mesmo limite local histórico."""

    def __init__(self) -> None:
        self._outcomes: dict[str, list[InteractionOutcome]] = {}

    def add(self, outcome: InteractionOutcome) -> bool:
        if self.get(outcome.project_id, outcome.outcome_id) is not None:
            return False
        outcomes = self._outcomes.setdefault(outcome.project_id, [])
        outcomes.append(outcome)
        if len(outcomes) > MAX_ENTRIES_PER_PROJECT:
            del outcomes[: len(outcomes) - MAX_ENTRIES_PER_PROJECT]
        return True

    def list(
        self,
        project_id: str,
        *,
        conversation_id: str | None = None,
        message_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[InteractionOutcome]:
        outcomes = [
            item
            for item in self._outcomes.get(project_id, [])
            if (conversation_id is None or item.conversation_id == conversation_id)
            and (message_id is None or item.message_id == message_id)
        ]
        if offset:
            outcomes = outcomes[offset:]
        return outcomes[:limit] if limit is not None else outcomes

    def count(
        self,
        project_id: str,
        *,
        conversation_id: str | None = None,
        message_id: str | None = None,
    ) -> int:
        return len(
            self.list(
                project_id,
                conversation_id=conversation_id,
                message_id=message_id,
            )
        )

    def get(self, project_id: str, outcome_id: str) -> InteractionOutcome | None:
        return next(
            (item for item in self._outcomes.get(project_id, []) if item.outcome_id == outcome_id),
            None,
        )

    def delete_project(self, project_id: str) -> int:
        return len(self._outcomes.pop(project_id, []))

    def delete_expired(self, now: datetime | None = None) -> int:
        reference = now or datetime.now(timezone.utc)
        deleted = 0
        for project_id, outcomes in list(self._outcomes.items()):
            retained = [item for item in outcomes if not _expired(item, reference)]
            deleted += len(outcomes) - len(retained)
            if retained:
                self._outcomes[project_id] = retained
            else:
                self._outcomes.pop(project_id, None)
        return deleted

    def clear(self) -> None:
        self._outcomes.clear()


class LocalJsonInteractionOutcomeRepository(InMemoryInteractionOutcomeRepository):
    """Persistência local de dev/test; um arquivo sanitizado por projeto."""

    def __init__(self, directory: str | Path) -> None:
        super().__init__()
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._load_all()

    def _file_for(self, project_id: str) -> Path:
        safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in project_id)
        return self._directory / f"{safe_name}.json"

    def _load_all(self) -> None:
        for file in self._directory.glob("*.json"):
            try:
                raw = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for item in raw if isinstance(raw, list) else []:
                try:
                    outcome = InteractionOutcome.model_validate(item)
                except Exception:
                    continue
                super().add(outcome)

    def _persist_project(self, project_id: str) -> None:
        outcomes = self.list(project_id)
        target = self._file_for(project_id)
        if not outcomes:
            target.unlink(missing_ok=True)
            return
        target.write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in outcomes],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def add(self, outcome: InteractionOutcome) -> bool:
        added = super().add(outcome)
        if added:
            self._persist_project(outcome.project_id)
        return added

    def delete_project(self, project_id: str) -> int:
        deleted = super().delete_project(project_id)
        self._persist_project(project_id)
        return deleted

    def delete_expired(self, now: datetime | None = None) -> int:
        projects = list(self._outcomes)
        deleted = super().delete_expired(now)
        for project_id in projects:
            self._persist_project(project_id)
        return deleted


class PostgreSQLInteractionOutcomeRepository:
    """Outcomes no mesmo PostgreSQL operacional; schema é criado por migração."""

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

    def add(self, outcome: InteractionOutcome) -> bool:
        statement = """
            INSERT INTO pedrocore_interaction_outcomes (
                outcome_id, project_id, producer, caller_role, environment,
                conversation_id, message_id, task_type, input_signature,
                context_signature, provider, model, response_strategy, feedback,
                accepted, rejected, fallback_used, regeneration_used, lifecycle,
                created_at, stored_at, retention_until, payload
            ) VALUES (
                %(outcome_id)s, %(project_id)s, %(producer)s, %(caller_role)s,
                %(environment)s, %(conversation_id)s, %(message_id)s,
                %(task_type)s, %(input_signature)s, %(context_signature)s,
                %(provider)s, %(model)s, %(response_strategy)s, %(feedback)s,
                %(accepted)s, %(rejected)s, %(fallback_used)s,
                %(regeneration_used)s, %(lifecycle)s, %(created_at)s,
                %(stored_at)s, %(retention_until)s, %(payload)s
            )
            ON CONFLICT (project_id, outcome_id) DO NOTHING
        """
        values = outcome.model_dump(mode="python")
        values["payload"] = Jsonb(outcome.model_dump(mode="json"))
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(statement, values)
                return cursor.rowcount == 1
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao persistir interaction outcome.") from exc

    def list(
        self,
        project_id: str,
        *,
        conversation_id: str | None = None,
        message_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[InteractionOutcome]:
        statement = """SELECT payload FROM pedrocore_interaction_outcomes
            WHERE project_id = %s
              AND conversation_id = COALESCE(%s, conversation_id)
              AND message_id = COALESCE(%s, message_id)
            ORDER BY created_at ASC, outcome_id ASC"""
        params: list[object] = [
            project_id,
            conversation_id,
            message_id,
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
                return [InteractionOutcome.model_validate(row[0]) for row in cursor]
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao consultar interaction outcomes.") from exc

    def count(
        self,
        project_id: str,
        *,
        conversation_id: str | None = None,
        message_id: str | None = None,
    ) -> int:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT COUNT(*) FROM pedrocore_interaction_outcomes
                    WHERE project_id = %s
                      AND conversation_id = COALESCE(%s, conversation_id)
                      AND message_id = COALESCE(%s, message_id)""",
                    (
                        project_id,
                        conversation_id,
                        message_id,
                    ),
                )
                row = cursor.fetchone()
                return int(row[0]) if row is not None else 0
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao contar interaction outcomes.") from exc

    def get(self, project_id: str, outcome_id: str) -> InteractionOutcome | None:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT payload FROM pedrocore_interaction_outcomes
                    WHERE project_id = %s AND outcome_id = %s""",
                    (project_id, outcome_id),
                )
                row = cursor.fetchone()
                return InteractionOutcome.model_validate(row[0]) if row else None
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao consultar interaction outcome.") from exc

    def delete_project(self, project_id: str) -> int:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM pedrocore_interaction_outcomes WHERE project_id = %s",
                    (project_id,),
                )
                return cursor.rowcount
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao excluir interaction outcomes.") from exc

    def delete_expired(self, now: datetime | None = None) -> int:
        reference = now or datetime.now(timezone.utc)
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """DELETE FROM pedrocore_interaction_outcomes
                    WHERE retention_until <= %s""",
                    (reference,),
                )
                return cursor.rowcount
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError(
                "Falha ao aplicar retenção de interaction outcomes."
            ) from exc

    def clear(self) -> None:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute("DELETE FROM pedrocore_interaction_outcomes")
        except psycopg.Error as exc:
            raise ReportMemoryRepositoryError("Falha ao limpar outcomes de teste.") from exc

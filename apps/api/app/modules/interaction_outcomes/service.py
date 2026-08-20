from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.modules.caller_identity.schemas import AuthenticatedCallerContext
from app.modules.contracts import codes
from app.modules.contracts.codes import WarningItem, make_warning
from app.modules.interaction_outcomes.repository import (
    InMemoryInteractionOutcomeRepository,
    InteractionOutcomeRepository,
    LocalJsonInteractionOutcomeRepository,
    PostgreSQLInteractionOutcomeRepository,
)
from app.modules.interaction_outcomes.schemas import (
    InteractionOutcome,
    InteractionOutcomeInput,
)
from app.modules.report_memory.repository import (
    ReportMemoryRepositoryConfigurationError,
)
from app.modules.report_memory.service import (
    FLAG_DATABASE_URL,
    FLAG_MEMORY_DIR,
    MODE_LOCAL_JSON,
    MODE_MEMORY,
    MODE_POSTGRESQL,
    persistence_mode,
    retention_days,
)

OUTCOMES_LOCAL_SUBDIRECTORY = "interaction_outcomes"


def _quality_signals(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


class InteractionOutcomeService:
    """Persistência observacional; nenhum feedback altera comportamento."""

    def __init__(self) -> None:
        self._memory_repository = InMemoryInteractionOutcomeRepository()
        self._json_repositories: dict[str, LocalJsonInteractionOutcomeRepository] = {}
        self._postgres_repositories: dict[str, PostgreSQLInteractionOutcomeRepository] = {}

    def enabled(self) -> bool:
        return persistence_mode() != "off"

    def _repository(self) -> InteractionOutcomeRepository | None:
        mode = persistence_mode()
        if mode == MODE_MEMORY:
            return self._memory_repository
        if mode == MODE_LOCAL_JSON:
            configured = (os.environ.get(FLAG_MEMORY_DIR) or "").strip()
            if not configured:
                return None
            directory = str(Path(configured) / OUTCOMES_LOCAL_SUBDIRECTORY)
            repository = self._json_repositories.get(directory)
            if repository is None:
                repository = LocalJsonInteractionOutcomeRepository(directory)
                self._json_repositories[directory] = repository
            return repository
        if mode == MODE_POSTGRESQL:
            database_url = (os.environ.get(FLAG_DATABASE_URL) or "").strip()
            if not database_url:
                raise ReportMemoryRepositoryConfigurationError(
                    f"{FLAG_DATABASE_URL} é obrigatória no modo postgresql."
                )
            repository = self._postgres_repositories.get(database_url)
            if repository is None:
                repository = PostgreSQLInteractionOutcomeRepository(database_url)
                self._postgres_repositories[database_url] = repository
            return repository
        return None

    def reset(self) -> None:
        """Limpa apenas referências/estado in-process; nunca apaga PostgreSQL."""
        self._memory_repository.clear()
        self._json_repositories.clear()
        self._postgres_repositories.clear()

    def ingest(
        self,
        payload: InteractionOutcomeInput,
        caller: AuthenticatedCallerContext,
    ) -> tuple[InteractionOutcome | None, bool, list[WarningItem]]:
        warnings = [
            make_warning(
                codes.INTERACTION_FEEDBACK_OBSERVATIONAL,
                "Outcome e feedback são observacionais; um evento isolado não altera comportamento.",
            )
        ]
        repository = self._repository()
        if repository is None:
            warnings.append(
                make_warning(
                    codes.INTERACTION_OUTCOME_DISABLED,
                    "Persistência de Interaction Outcomes desabilitada; nada foi guardado.",
                )
            )
            return None, False, warnings

        project_id = payload.project_id.strip().lower()
        outcome_id = payload.outcome_id.strip()
        existing = repository.get(project_id, outcome_id)
        if existing is not None:
            warnings.append(
                make_warning(
                    codes.INTERACTION_OUTCOME_DUPLICATE,
                    "outcome_id já persistido neste projeto; nenhum efeito duplicado foi criado.",
                )
            )
            return existing, True, warnings

        now = datetime.now(timezone.utc)
        outcome = InteractionOutcome(
            **payload.model_dump(
                exclude={
                    "outcome_id",
                    "producer",
                    "project_id",
                    "conversation_id",
                    "message_id",
                    "task_type",
                    "input_signature",
                    "context_signature",
                    "provider",
                    "model",
                    "response_strategy",
                    "quality_signals",
                    "audit_id",
                }
            ),
            outcome_id=outcome_id,
            producer=caller.credential_id,
            project_id=project_id,
            conversation_id=payload.conversation_id.strip(),
            message_id=payload.message_id.strip(),
            task_type=payload.task_type.strip().lower(),
            input_signature=payload.input_signature.lower(),
            context_signature=payload.context_signature.lower(),
            provider=payload.provider.strip().lower(),
            model=payload.model.strip(),
            response_strategy=payload.response_strategy.strip().lower(),
            quality_signals=_quality_signals(payload.quality_signals),
            audit_id=payload.audit_id.strip() if payload.audit_id else None,
            caller_role=caller.caller_role.value,
            environment=caller.environment.strip().lower(),
            stored_at=now,
            retention_until=now + timedelta(days=retention_days()),
        )
        if not repository.add(outcome):
            existing = repository.get(project_id, outcome_id)
            if existing is None:
                raise ReportMemoryRepositoryConfigurationError(
                    "Repository recusou outcome sem retornar registro existente."
                )
            warnings.append(
                make_warning(
                    codes.INTERACTION_OUTCOME_DUPLICATE,
                    "outcome_id concorrente já persistido; nenhum efeito duplicado foi criado.",
                )
            )
            return existing, True, warnings
        return outcome, False, warnings

    def page(
        self,
        project_id: str,
        *,
        conversation_id: str | None,
        message_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[InteractionOutcome], int]:
        repository = self._repository()
        if repository is None:
            return [], 0
        normalized_project = project_id.strip().lower()
        normalized_conversation = conversation_id.strip() if conversation_id else None
        normalized_message = message_id.strip() if message_id else None
        return (
            repository.list(
                normalized_project,
                conversation_id=normalized_conversation,
                message_id=normalized_message,
                limit=limit,
                offset=offset,
            ),
            repository.count(
                normalized_project,
                conversation_id=normalized_conversation,
                message_id=normalized_message,
            ),
        )

    def delete_project(self, project_id: str) -> int:
        repository = self._repository()
        if repository is None:
            return 0
        return repository.delete_project(project_id.strip().lower())

    def get(self, project_id: str, outcome_id: str) -> InteractionOutcome | None:
        repository = self._repository()
        if repository is None:
            return None
        return repository.get(project_id.strip().lower(), outcome_id.strip())

    def apply_retention(self, now: datetime | None = None) -> int:
        repository = self._repository()
        if repository is None:
            return 0
        return repository.delete_expired(now)


interaction_outcome_service = InteractionOutcomeService()

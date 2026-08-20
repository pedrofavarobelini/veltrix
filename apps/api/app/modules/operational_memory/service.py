from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.modules.caller_identity.schemas import AuthenticatedCallerContext
from app.modules.contracts import codes
from app.modules.contracts.codes import WarningItem, make_warning
from app.modules.interaction_outcomes.service import interaction_outcome_service
from app.modules.operational_memory.policy import (
    OPERATIONAL_MEMORY_POLICY_VERSION,
    RISK_PATTERN_TYPES,
    assess_pattern,
    stable_pattern_id,
)
from app.modules.operational_memory.repository import (
    InMemoryOperationalMemoryRepository,
    LocalJsonOperationalMemoryRepository,
    OperationalMemoryRepository,
    PostgreSQLOperationalMemoryRepository,
)
from app.modules.operational_memory.schemas import (
    EvidenceEffect,
    EvidenceReference,
    EvidenceReferenceInput,
    EvidenceSourceType,
    LearningCandidate,
    LearningCandidateInput,
    LifecycleTransition,
    MemoryLifecycle,
    OperationalMemoryEntry,
    OperationalPattern,
    PatternType,
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
    report_memory_service,
    retention_days,
)

OPERATIONAL_MEMORY_LOCAL_SUBDIRECTORY = "operational_memory"
_SECRET_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|senha|chave)\b\s*[:=]\s*\S+"
)


class OperationalEvidenceError(ValueError):
    pass


def _redact(value: str) -> str:
    return _SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


def _as_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class OperationalMemoryService:
    """Pipeline de evidência; nunca aplica padrões automaticamente."""

    def __init__(self) -> None:
        self._memory_repository = InMemoryOperationalMemoryRepository()
        self._json_repositories: dict[str, LocalJsonOperationalMemoryRepository] = {}
        self._postgres_repositories: dict[str, PostgreSQLOperationalMemoryRepository] = {}

    def enabled(self) -> bool:
        return persistence_mode() != "off"

    def _repository(self) -> OperationalMemoryRepository | None:
        mode = persistence_mode()
        if mode == MODE_MEMORY:
            return self._memory_repository
        if mode == MODE_LOCAL_JSON:
            configured = (os.environ.get(FLAG_MEMORY_DIR) or "").strip()
            if not configured:
                return None
            directory = str(Path(configured) / OPERATIONAL_MEMORY_LOCAL_SUBDIRECTORY)
            repository = self._json_repositories.get(directory)
            if repository is None:
                repository = LocalJsonOperationalMemoryRepository(directory)
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
                repository = PostgreSQLOperationalMemoryRepository(database_url)
                self._postgres_repositories[database_url] = repository
            return repository
        return None

    def reset(self) -> None:
        self._memory_repository.clear()
        self._json_repositories.clear()
        self._postgres_repositories.clear()

    def _resolve_evidence(
        self,
        project_id: str,
        task_type: str,
        reference: EvidenceReferenceInput,
    ) -> EvidenceReference:
        if reference.source_type is EvidenceSourceType.REPORT:
            report = report_memory_service.get_report(project_id, reference.source_id)
            if report is None:
                raise OperationalEvidenceError(
                    f"Report evidence não encontrada no projeto: {reference.source_id}"
                )
            qa_validated = report.report_type == "qa_evidence" and report.status in {
                "passed",
                "pass",
                "success",
                "ok",
            }
            return EvidenceReference(
                **reference.model_dump(),
                source_reliability=0.95 if qa_validated else 0.82,
                evidence_strength=0.90 if qa_validated else 0.72,
                context_match=0.75,
                qa_validated=qa_validated,
                human_validated=False,
                observed_at=_as_datetime(report.created_at),
            )
        if reference.source_type is EvidenceSourceType.INTERACTION_OUTCOME:
            outcome = interaction_outcome_service.get(project_id, reference.source_id)
            if outcome is None:
                raise OperationalEvidenceError(
                    f"Interaction Outcome evidence não encontrada no projeto: {reference.source_id}"
                )
            positive_feedback = outcome.feedback == "positive" or outcome.accepted is True
            explicit_feedback = outcome.feedback != "unknown"
            return EvidenceReference(
                **reference.model_dump(),
                source_reliability=0.80 if positive_feedback else 0.70,
                evidence_strength=0.78 if explicit_feedback else 0.60,
                context_match=1.0 if outcome.task_type == task_type else 0.40,
                qa_validated=False,
                human_validated=False,
                observed_at=outcome.created_at,
            )
        raise OperationalEvidenceError(
            "Human validation exige contrato/autorização próprios e ainda não está disponível."
        )

    @staticmethod
    def _deduplicate_evidence(
        values: list[EvidenceReference],
    ) -> list[EvidenceReference]:
        result: list[EvidenceReference] = []
        seen: set[tuple[str, str, str]] = set()
        for value in values:
            key = (
                value.source_type.value,
                value.source_id,
                value.effect.value,
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result

    def ingest_candidate(
        self,
        payload: LearningCandidateInput,
        caller: AuthenticatedCallerContext,
    ) -> tuple[
        LearningCandidate | None,
        OperationalMemoryEntry | None,
        bool,
        list[WarningItem],
    ]:
        repository = self._repository()
        if repository is None:
            return (
                None,
                None,
                False,
                [
                    make_warning(
                        codes.OPERATIONAL_MEMORY_DISABLED,
                        "Operational Memory desabilitada; candidate não foi guardado.",
                    )
                ],
            )

        project_id = payload.project_id.strip().lower()
        candidate_id = payload.candidate_id.strip()
        existing_candidate = repository.get_candidate(project_id, candidate_id)
        if existing_candidate is not None:
            return (
                existing_candidate,
                repository.get_memory_by_pattern(project_id, existing_candidate.pattern_id),
                True,
                [
                    make_warning(
                        codes.LEARNING_CANDIDATE_DUPLICATE,
                        "candidate_id já processado; nenhum efeito duplicado foi criado.",
                    )
                ],
            )

        pattern_id = stable_pattern_id(
            project_id,
            payload.pattern_type,
            payload.pattern_key,
            payload.task_type.strip().lower(),
        )
        if payload.pattern_type not in RISK_PATTERN_TYPES and any(
            item.effect in {EvidenceEffect.MITIGATES, EvidenceEffect.RESOLVES}
            for item in payload.evidence
        ):
            raise OperationalEvidenceError(
                "mitigates/resolves só são válidos para failure, anti ou risk pattern"
            )

        resolved = [
            self._resolve_evidence(project_id, payload.task_type, item) for item in payload.evidence
        ]
        previous_candidates = repository.list_candidates_for_pattern(project_id, pattern_id)
        aggregate = self._deduplicate_evidence(
            [evidence for candidate in previous_candidates for evidence in candidate.evidence]
            + resolved
        )
        current_memory = repository.get_memory_by_pattern(project_id, pattern_id)
        assessment = assess_pattern(
            pattern_type=payload.pattern_type,
            evidence=aggregate,
            current_lifecycle=(current_memory.lifecycle if current_memory else None),
        )
        now = datetime.now(timezone.utc)
        retention_until = now + timedelta(days=retention_days())
        pattern = (
            current_memory.pattern
            if current_memory
            else OperationalPattern(
                pattern_id=pattern_id,
                pattern_type=payload.pattern_type,
                pattern_key=payload.pattern_key,
                task_type=payload.task_type.strip().lower(),
                summary=_redact(payload.summary.strip()),
            )
        )
        candidate = LearningCandidate(
            **payload.model_dump(
                exclude={
                    "candidate_id",
                    "producer",
                    "project_id",
                    "pattern_key",
                    "task_type",
                    "summary",
                    "evidence",
                }
            ),
            candidate_id=candidate_id,
            producer=caller.credential_id,
            project_id=project_id,
            pattern_key=payload.pattern_key,
            task_type=payload.task_type.strip().lower(),
            summary=_redact(payload.summary.strip()),
            evidence=resolved,
            pattern_id=pattern_id,
            confidence=assessment.confidence,
            decision=assessment.decision,
            policy_version=OPERATIONAL_MEMORY_POLICY_VERSION,
            caller_role=caller.caller_role.value,
            environment=caller.environment.strip().lower(),
            created_at=now,
            stored_at=now,
            retention_until=retention_until,
        )
        history = list(current_memory.lifecycle_history) if current_memory else []
        previous_lifecycle = current_memory.lifecycle if current_memory else None
        if previous_lifecycle is not assessment.lifecycle:
            history.append(
                LifecycleTransition(
                    from_lifecycle=previous_lifecycle,
                    to_lifecycle=assessment.lifecycle,
                    reason=assessment.reason,
                    at=now,
                )
            )
        positive_evidence = [
            item for item in aggregate if item.effect is not EvidenceEffect.CONTRADICTS
        ]
        contradictions = [item for item in aggregate if item.effect is EvidenceEffect.CONTRADICTS]
        sample_size = len({(item.source_type.value, item.source_id) for item in aggregate})
        memory = OperationalMemoryEntry(
            memory_id=f"memory-{pattern_id.removeprefix('pattern-')}",
            project_id=project_id,
            pattern=pattern,
            confidence=assessment.confidence,
            confidence_breakdown=assessment.breakdown,
            lifecycle=assessment.lifecycle,
            candidate_ids=[
                *[item.candidate_id for item in previous_candidates],
                candidate_id,
            ],
            evidence=positive_evidence,
            contradictions=contradictions,
            sample_size=sample_size,
            policy_version=OPERATIONAL_MEMORY_POLICY_VERSION,
            lifecycle_history=history,
            created_at=current_memory.created_at if current_memory else now,
            updated_at=now,
            retention_until=retention_until,
        )
        if not repository.save_evaluation(candidate, memory):
            existing_candidate = repository.get_candidate(project_id, candidate_id)
            if existing_candidate is None:
                raise ReportMemoryRepositoryConfigurationError(
                    "Repository recusou candidate sem retornar registro existente."
                )
            return (
                existing_candidate,
                repository.get_memory_by_pattern(project_id, existing_candidate.pattern_id),
                True,
                [
                    make_warning(
                        codes.LEARNING_CANDIDATE_DUPLICATE,
                        "candidate concorrente já processado; nenhum efeito duplicado foi criado.",
                    )
                ],
            )

        warnings: list[WarningItem] = []
        distinct_support = {
            (item.source_type.value, item.source_id)
            for item in aggregate
            if item.effect is EvidenceEffect.SUPPORTS
        }
        if assessment.lifecycle is MemoryLifecycle.DETECTED and len(distinct_support) < 3:
            warnings.append(
                make_warning(
                    codes.OPERATIONAL_SINGLE_EVIDENCE_NOT_PROMOTED,
                    "Evidência insuficiente: um evento isolado não vira regra ativa.",
                )
            )
        if contradictions:
            warnings.append(
                make_warning(
                    codes.OPERATIONAL_CONTRADICTION_PRESERVED,
                    "Contradições foram preservadas e penalizam a confiança.",
                )
            )
        if assessment.lifecycle is MemoryLifecycle.RESOLVED:
            warnings.append(
                make_warning(
                    codes.OPERATIONAL_PATTERN_RESOLVED,
                    "Padrão de risco marcado como resolvido por evidência validada.",
                )
            )
        return candidate, memory, False, warnings

    def page(
        self,
        project_id: str,
        *,
        pattern_type: PatternType | None,
        lifecycle: MemoryLifecycle | None,
        limit: int,
        offset: int,
    ) -> tuple[list[OperationalMemoryEntry], int]:
        repository = self._repository()
        if repository is None:
            return [], 0
        normalized_project = project_id.strip().lower()
        return (
            repository.list_memory(
                normalized_project,
                pattern_type=pattern_type,
                lifecycle=lifecycle,
                limit=limit,
                offset=offset,
            ),
            repository.count_memory(
                normalized_project,
                pattern_type=pattern_type,
                lifecycle=lifecycle,
            ),
        )

    def delete_project(self, project_id: str) -> tuple[int, int]:
        repository = self._repository()
        if repository is None:
            return 0, 0
        return repository.delete_project(project_id.strip().lower())

    def apply_retention(self, now: datetime | None = None) -> tuple[int, int]:
        repository = self._repository()
        if repository is None:
            return 0, 0
        return repository.delete_expired(now)


operational_memory_service = OperationalMemoryService()

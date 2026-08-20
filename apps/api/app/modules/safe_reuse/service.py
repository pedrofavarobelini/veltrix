from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.modules.operational_memory.schemas import MemoryLifecycle, PatternType
from app.modules.operational_memory.service import operational_memory_service
from app.modules.safe_reuse.schemas import (
    ReuseDecision,
    ReuseEvaluationRequest,
    ReuseFingerprint,
    ReuseMode,
    ValidationStatus,
)

_COMMON_DIMENSIONS = (
    "project_id",
    "user_scope_signature",
    "family_scope_signature",
    "permissions",
    "environment",
    "temporal_state_signature",
    "policy_version",
    "dependency_version",
)
_DIRECT_DIMENSIONS = (
    "input_signature",
    "context_signature",
    "data_signature",
    *_COMMON_DIMENSIONS,
)


def _canonical(value: object) -> object:
    if isinstance(value, list):
        return tuple(sorted(str(item) for item in value))
    if isinstance(value, str) and value:
        return value.strip().lower()
    return value


def _mismatches(
    current: ReuseFingerprint,
    source: ReuseFingerprint,
    dimensions: tuple[str, ...],
) -> list[str]:
    return [
        dimension
        for dimension in dimensions
        if _canonical(getattr(current, dimension)) != _canonical(getattr(source, dimension))
    ]


class SafeReuseService:
    """Classifies reuse candidates; it never bypasses a provider or returns cached output."""

    @staticmethod
    def _no_reuse(
        request: ReuseEvaluationRequest,
        evaluation_id: str,
        now: datetime,
        reason_codes: list[str],
        invalidated_dimensions: list[str] | None = None,
    ) -> ReuseDecision:
        return ReuseDecision(
            evaluation_id=evaluation_id,
            project_id=request.project_id.strip().lower(),
            candidate_id=request.candidate.candidate_id,
            mode=ReuseMode.NO_REUSE,
            reason_codes=reason_codes,
            invalidated_dimensions=invalidated_dimensions or [],
            evaluated_at=now,
        )

    def evaluate(self, request: ReuseEvaluationRequest) -> ReuseDecision:
        now = datetime.now(timezone.utc)
        evaluation_id = request.evaluation_id or f"reuse_{uuid.uuid4().hex}"
        candidate = request.candidate
        project_id = request.project_id.strip().lower()
        if request.current_fingerprint.project_id.strip().lower() != project_id:
            return self._no_reuse(
                request,
                evaluation_id,
                now,
                ["REQUEST_PROJECT_MISMATCH"],
                ["project_id"],
            )
        if candidate.proposed_mode is ReuseMode.NO_REUSE:
            return self._no_reuse(request, evaluation_id, now, ["NO_REUSE_REQUESTED"])
        if candidate.validation_status is not ValidationStatus.VALIDATED:
            return self._no_reuse(request, evaluation_id, now, ["VALIDATION_REQUIRED"])
        if candidate.validation_signature is None or candidate.validated_at is None:
            return self._no_reuse(request, evaluation_id, now, ["VALIDATION_INCOMPLETE"])
        if candidate.valid_until is None or candidate.valid_until <= now:
            return self._no_reuse(request, evaluation_id, now, ["VALIDATION_EXPIRED"])
        if candidate.source_fingerprint is None:
            return self._no_reuse(request, evaluation_id, now, ["SOURCE_FINGERPRINT_REQUIRED"])

        dimensions = (
            _DIRECT_DIMENSIONS
            if candidate.proposed_mode is ReuseMode.DIRECT_REUSE
            else _COMMON_DIMENSIONS
        )
        invalidated = _mismatches(
            request.current_fingerprint,
            candidate.source_fingerprint,
            dimensions,
        )
        if invalidated:
            return self._no_reuse(
                request,
                evaluation_id,
                now,
                ["FINGERPRINT_MISMATCH"],
                invalidated,
            )

        reason_codes: list[str]
        matched_memory_id: str | None = None
        if candidate.proposed_mode is ReuseMode.DIRECT_REUSE:
            reason_codes = ["STRONG_EQUIVALENCE_CONFIRMED", "PROVIDER_BYPASS_FORBIDDEN"]
        elif candidate.proposed_mode is ReuseMode.TEMPLATE_REUSE:
            if not candidate.template_id or not candidate.template_version:
                return self._no_reuse(request, evaluation_id, now, ["TEMPLATE_REFERENCE_REQUIRED"])
            reason_codes = ["VALIDATED_TEMPLATE_CANDIDATE"]
        elif candidate.proposed_mode in {ReuseMode.KNOWLEDGE_REUSE, ReuseMode.ANTI_PATTERN}:
            if not candidate.memory_id:
                return self._no_reuse(request, evaluation_id, now, ["MEMORY_REFERENCE_REQUIRED"])
            repository = operational_memory_service.repository_for_retrieval()
            if repository is None:
                return self._no_reuse(request, evaluation_id, now, ["MEMORY_DISABLED"])
            memory = repository.get_memory(project_id, candidate.memory_id)
            if memory is None:
                return self._no_reuse(request, evaluation_id, now, ["MEMORY_NOT_FOUND"])
            if memory.lifecycle not in {MemoryLifecycle.ACTIVE, MemoryLifecycle.MITIGATED}:
                return self._no_reuse(request, evaluation_id, now, ["MEMORY_NOT_ACTIVE"])
            is_anti_pattern = memory.pattern.pattern_type is PatternType.ANTI_PATTERN
            if candidate.proposed_mode is ReuseMode.ANTI_PATTERN and not is_anti_pattern:
                return self._no_reuse(request, evaluation_id, now, ["MEMORY_TYPE_MISMATCH"])
            if candidate.proposed_mode is ReuseMode.KNOWLEDGE_REUSE and is_anti_pattern:
                return self._no_reuse(request, evaluation_id, now, ["ANTI_PATTERN_MODE_REQUIRED"])
            matched_memory_id = memory.memory_id
            reason_codes = [
                "ACTIVE_OPERATIONAL_MEMORY",
                "ANTI_PATTERN_WARNING" if is_anti_pattern else "KNOWLEDGE_CANDIDATE",
            ]
        else:
            return self._no_reuse(request, evaluation_id, now, ["UNSUPPORTED_REUSE_MODE"])

        return ReuseDecision(
            evaluation_id=evaluation_id,
            project_id=project_id,
            candidate_id=candidate.candidate_id,
            mode=candidate.proposed_mode,
            matched_memory_id=matched_memory_id,
            reason_codes=reason_codes,
            evaluated_at=now,
        )


safe_reuse_service = SafeReuseService()

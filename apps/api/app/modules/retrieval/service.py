from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone

from app.modules.observability.service import observability_service
from app.modules.operational_memory.schemas import (
    MemoryLifecycle,
    OperationalMemoryEntry,
    PatternType,
)
from app.modules.operational_memory.service import operational_memory_service
from app.modules.retrieval.schemas import (
    RetrievalCandidateTrace,
    RetrievalQuery,
    RetrievalResponse,
    RetrievedMemory,
)

_DEFAULT_LIFECYCLES = {MemoryLifecycle.ACTIVE, MemoryLifecycle.MITIGATED}
_CANDIDATE_LIMIT = 200


def _terms(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return set(re.findall(r"[a-z0-9][a-z0-9_.:-]{1,63}", ascii_value))


def _document(memory: OperationalMemoryEntry) -> str:
    pattern = memory.pattern
    return " ".join(
        (
            pattern.pattern_type.value,
            pattern.pattern_key,
            pattern.task_type,
            pattern.summary,
        )
    )


class RetrievalService:
    """Ranks bounded projections; it never mutates memory or a prompt."""

    @staticmethod
    def _score(
        memory: OperationalMemoryEntry,
        query: RetrievalQuery,
        now: datetime,
    ) -> float:
        requested_terms = _terms(" ".join(query.keywords))
        document_terms = _terms(_document(memory))
        lexical = (
            len(requested_terms & document_terms) / len(requested_terms) if requested_terms else 1.0
        )
        requested_task = (query.task_type or "").strip().lower()
        task_match = (
            1.0 if not requested_task else float(memory.pattern.task_type == requested_task)
        )
        evidence = min(1.0, memory.sample_size / 3.0)
        age_days = max(0.0, (now - memory.updated_at).total_seconds() / 86_400)
        recency_window = float(query.recency_days or 365)
        recency = max(0.0, 1.0 - (age_days / recency_window))
        lifecycle = {
            MemoryLifecycle.ACTIVE: 1.0,
            MemoryLifecycle.MITIGATED: 0.75,
            MemoryLifecycle.DETECTED: 0.4,
            MemoryLifecycle.RESOLVED: 0.2,
        }[memory.lifecycle]
        return round(
            (0.35 * lexical)
            + (0.20 * task_match)
            + (0.15 * memory.confidence)
            + (0.10 * evidence)
            + (0.10 * recency)
            + (0.10 * lifecycle),
            6,
        )

    @staticmethod
    def _rejections(
        memory: OperationalMemoryEntry,
        query: RetrievalQuery,
        now: datetime,
    ) -> list[str]:
        reasons: list[str] = []
        allowed_lifecycles = set(query.lifecycles) or _DEFAULT_LIFECYCLES
        if memory.lifecycle not in allowed_lifecycles:
            reasons.append("LIFECYCLE_NOT_REQUESTED")
        if query.pattern_types and memory.pattern.pattern_type not in set(query.pattern_types):
            reasons.append("PATTERN_TYPE_NOT_REQUESTED")
        if (
            memory.pattern.pattern_type is PatternType.ANTI_PATTERN
            and not query.include_anti_patterns
        ):
            reasons.append("ANTI_PATTERN_NOT_AUTHORIZED")
        if memory.confidence < query.min_confidence:
            reasons.append("BELOW_MIN_CONFIDENCE")
        if memory.sample_size < query.min_evidence_count:
            reasons.append("BELOW_MIN_EVIDENCE")
        if query.recency_days is not None:
            cutoff = now - timedelta(days=query.recency_days)
            if memory.updated_at < cutoff:
                reasons.append("OUTSIDE_RECENCY_WINDOW")
        return reasons

    def retrieve(self, query: RetrievalQuery) -> RetrievalResponse:
        query_id = query.query_id or f"qry_{uuid.uuid4().hex}"
        project_id = query.project_id.strip().lower()
        repository = operational_memory_service.repository_for_retrieval()
        if repository is None:
            response = RetrievalResponse(
                status="disabled",
                query_id=query_id,
                project_id=project_id,
            )
            observability_service.record_retrieval(response, query, [])
            return response

        raw_candidates = repository.search_memory(
            project_id,
            keywords=query.keywords,
            limit=_CANDIDATE_LIMIT,
        )
        now = datetime.now(timezone.utc)
        ranked = sorted(
            (
                (memory, self._score(memory, query, now))
                for memory, _repository_rank in raw_candidates
            ),
            key=lambda item: (item[1], item[0].updated_at, item[0].memory_id),
            reverse=True,
        )
        items: list[RetrievedMemory] = []
        traces: list[RetrievalCandidateTrace] = []
        context_chars = 0
        for memory, score in ranked:
            reasons = self._rejections(memory, query, now)
            selected = False
            summary = memory.pattern.summary[:300]
            projected_chars = (
                len(summary) + len(memory.memory_id) + len(memory.pattern.pattern_id) + 96
            )
            if not reasons and len(items) >= query.max_results:
                reasons.append("RESULT_LIMIT_REACHED")
            if not reasons and context_chars + projected_chars > query.max_context_chars:
                reasons.append("CONTEXT_BUDGET_EXCEEDED")
            if not reasons:
                selected = True
                context_chars += projected_chars
                items.append(
                    RetrievedMemory(
                        memory_id=memory.memory_id,
                        pattern_id=memory.pattern.pattern_id,
                        pattern_type=memory.pattern.pattern_type,
                        lifecycle=memory.lifecycle,
                        task_type=memory.pattern.task_type,
                        summary=summary,
                        confidence=memory.confidence,
                        evidence_count=memory.sample_size,
                        relevance_score=score,
                        policy_version=memory.policy_version,
                        updated_at=memory.updated_at,
                    )
                )
            traces.append(
                RetrievalCandidateTrace(
                    memory_id=memory.memory_id,
                    score=score,
                    selected=selected,
                    rejection_reasons=reasons,
                )
            )

        response = RetrievalResponse(
            query_id=query_id,
            project_id=project_id,
            items=items,
            candidates=traces,
            context_chars=context_chars,
        )
        observability_service.record_retrieval(response, query, traces)
        return response


retrieval_service = RetrievalService()

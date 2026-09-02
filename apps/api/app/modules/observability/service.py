from __future__ import annotations

import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.modules.caller_identity.schemas import AuthenticatedCallerContext
from app.modules.evaluation.service import evaluation_service
from app.modules.observability.sanitizer import sanitize_payload, sanitize_text
from app.modules.observability.schemas import (
    ExecutionRecord,
    ExecutionSummary,
    ProviderAttempt,
    TimelineEvent,
)

FLAG_ENABLED = "PEDROCORE_OBSERVABILITY_ENABLED"
FLAG_MAX_ENTRIES = "PEDROCORE_OBSERVABILITY_MAX_ENTRIES"
FLAG_QA_FORCE_TOTAL_FAILURE = "PEDROCORE_QA_FORCE_TOTAL_PROVIDER_FAILURE"

LOCAL_ENVS = {"dev", "development", "local", "qa", "test", "testing"}
PRODUCTION_ENVS = {"prod", "production"}

NOTICE = (
    "MODO DE OBSERVABILIDADE QA/LOCAL. Não é painel público. "
    "Memória técnica não altera os pesos do modelo e não constitui treinamento ou fine-tuning. "
    "Treinamento de modelo: não implementado."
)


def _flag_true(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() == "true"


def _environment() -> str:
    return (os.environ.get("APP_ENV") or settings.app_env or "development").strip().lower()


def _max_entries() -> int:
    raw = (os.environ.get(FLAG_MAX_ENTRIES) or "200").strip()
    try:
        return min(1_000, max(10, int(raw)))
    except ValueError:
        return 200


def _model_dump(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


class ObservabilityService:
    def __init__(self) -> None:
        self._records: list[ExecutionRecord] = []
        self._lock = threading.RLock()

    def enabled(self) -> bool:
        environment = _environment()
        return (
            _flag_true(FLAG_ENABLED)
            and environment in LOCAL_ENVS
            and environment not in PRODUCTION_ENVS
        )

    def mode(self) -> str:
        return _environment()

    def max_entries(self) -> int:
        return _max_entries()

    def force_total_provider_failure(self, payload: Any) -> bool:
        return (
            self.enabled()
            and _environment() in {"qa", "test", "testing"}
            and _flag_true(FLAG_QA_FORCE_TOTAL_FAILURE)
            and str(getattr(payload, "origin_system", "")).lower() == "finguard"
        )

    def reset(self) -> None:
        with self._lock:
            self._records.clear()

    def _append(self, record: ExecutionRecord) -> None:
        if not self.enabled():
            return
        with self._lock:
            self._records.append(record)
            overflow = len(self._records) - self.max_entries()
            if overflow > 0:
                del self._records[:overflow]

    def list(
        self,
        *,
        origin: str | None = None,
        task: str | None = None,
        status: str | None = None,
        provider: str | None = None,
        fallback: bool | None = None,
        limit: int = 100,
    ) -> list[ExecutionSummary]:
        with self._lock:
            records = list(reversed(self._records))

        def matches(record: ExecutionRecord) -> bool:
            return (
                (not origin or record.origin_system == origin)
                and (not task or record.task == task)
                and (not status or record.status == status)
                and (not provider or record.provider_effective == provider)
                and (fallback is None or record.fallback is fallback)
            )

        return [
            ExecutionSummary(
                execution_id=record.execution_id,
                audit_id=record.audit_id,
                timestamp=record.timestamp,
                origin_system=record.origin_system,
                task=record.task,
                status=record.status,
                provider_effective=record.provider_effective,
                fallback=record.fallback,
                duration_ms=record.duration_ms,
            )
            for record in records
            if matches(record)
        ][: min(500, max(1, limit))]

    def get(self, execution_id: str) -> ExecutionRecord | None:
        with self._lock:
            return next(
                (record for record in self._records if record.execution_id == execution_id),
                None,
            )

    def record_retrieval(
        self,
        response: Any,
        query: Any,
        traces: list[Any],
    ) -> None:
        """Record IDs, scores and decisions, never search terms or memory text."""
        if not self.enabled():
            return
        selected_ids = [item.memory_id for item in response.items]
        candidate_projection = [
            {
                "memory_id": item.memory_id,
                "score": item.score,
                "selected": item.selected,
                "rejection_reasons": list(item.rejection_reasons),
            }
            for item in traces
        ]
        self._append(
            ExecutionRecord(
                execution_id=response.query_id,
                audit_id=response.query_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                origin_system="pedrocore",
                task="operational_memory_retrieval",
                status=response.status,
                payload_sanitized={
                    "query_id": response.query_id,
                    "project_id": response.project_id,
                    "task_type": query.task_type,
                    "policy_version": response.policy_version,
                    "max_results": query.max_results,
                    "max_context_chars": query.max_context_chars,
                },
                removed_fields=["keywords"],
                memory_consulted=True,
                timeline=[
                    TimelineEvent(stage="retrieval_started", status="ok", offset_ms=0.0),
                    TimelineEvent(stage="candidates_ranked", status="completed"),
                    TimelineEvent(stage="context_bounded", status="completed"),
                ],
                result_returned={
                    "policy_version": response.policy_version,
                    "selected_memory_ids": selected_ids,
                    "candidates": candidate_projection,
                    "context_chars": response.context_chars,
                },
            )
        )

    def record_orchestration(self, payload: Any, outcome: Any, duration_ms: float) -> None:
        if not self.enabled():
            return

        payload_sanitized, removed_fields = sanitize_payload(payload)
        error = sanitize_text(outcome.error, 1_000) if outcome.error else None
        blocked_reason = (
            sanitize_text(outcome.blocked_reason, 1_000)
            if outcome.blocked_reason
            else None
        )
        provider_selected = self._selected_provider(outcome)
        attempts = self._provider_attempts(outcome, provider_selected, error)
        evaluation = (
            evaluation_service.evaluate_intelligence_plan(
                outcome.intelligence_plan
            ).model_dump(mode="json")
            if outcome.intelligence_plan is not None
            else None
        )
        signals = self._orchestration_signals(outcome)
        timeline = [
            TimelineEvent(stage="pipeline_started", status="ok", offset_ms=0.0),
            TimelineEvent(stage="routing_and_policy", status="completed"),
        ]
        if attempts:
            timeline.append(
                TimelineEvent(
                    stage="provider",
                    status=attempts[0].result,
                    detail=attempts[0].detail,
                )
            )
        if outcome.fallback_used:
            timeline.append(
                TimelineEvent(
                    stage="fallback",
                    status="completed",
                    detail=f"provider efetivo: {outcome.provider_used}",
                )
            )
        timeline.append(
            TimelineEvent(
                stage="pipeline_completed",
                status=outcome.status,
                detail=blocked_reason,
                offset_ms=round(duration_ms, 2),
            )
        )

        record = ExecutionRecord(
            execution_id=str(uuid.uuid4()),
            audit_id=outcome.audit.audit_id,
            timestamp=outcome.audit.timestamp,
            origin_system=outcome.origin_system,
            task=outcome.task_type,
            status=outcome.status,
            payload_sanitized=payload_sanitized,
            removed_fields=removed_fields,
            caller=self._caller_projection(outcome),
            binding=self._binding_projection(outcome),
            shadow_routing=self._shadow_projection(outcome),
            provider_requested=outcome.provider_requested,
            provider_selected=provider_selected,
            provider_effective=outcome.provider_used,
            provider_attempts=attempts,
            generation_budget=self._generation_budget_projection(outcome),
            fallback=outcome.fallback_used,
            fallback_reason=error,
            duration_ms=round(duration_ms, 2),
            public_response=sanitize_text(outcome.answer),
            release_gate=_model_dump(outcome.release_gate),
            evaluation=evaluation,
            signals=signals,
            memory_consulted=outcome.memory_used,
            memory_created=False,
            error=error,
            # Constante por construção, não por omissão: não existe retry no
            # adapter, na orquestração nem no SDK (o default do google-genai é
            # `stop_after_attempt(1)` e o Veltrix nunca passa
            # `HttpRetryOptions`). Uma chamada lógica = no máximo um dispatch.
            retry={"attempted": False, "count": 0},
            timeline=timeline,
            result_returned={
                "status": outcome.status,
                "project_id": outcome.project_id,
                "provider_used": outcome.provider_used,
                "model": outcome.model,
                "fallback_used": outcome.fallback_used,
                "audit_id": outcome.audit.audit_id,
                "warning_codes": outcome.warning_codes,
                "blocked_reason": blocked_reason,
            },
        )
        self._append(record)

    def record_exception(self, payload: Any, error: Exception, duration_ms: float) -> None:
        if not self.enabled():
            return
        payload_sanitized, removed_fields = sanitize_payload(payload)
        safe_error = sanitize_text(error, 1_000)
        execution_id = str(uuid.uuid4())
        self._append(
            ExecutionRecord(
                execution_id=execution_id,
                audit_id=execution_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                origin_system=str(getattr(payload, "origin_system", "unknown")),
                task=str(getattr(payload, "task_type", "unknown")),
                status="error",
                payload_sanitized=payload_sanitized,
                removed_fields=removed_fields,
                provider_requested=str(getattr(payload, "provider", "unknown")),
                duration_ms=round(duration_ms, 2),
                error=safe_error,
                retry={"attempted": False, "count": 0},
                timeline=[
                    TimelineEvent(stage="pipeline_started", status="ok", offset_ms=0.0),
                    TimelineEvent(
                        stage="pipeline_exception",
                        status="error",
                        detail=safe_error,
                        offset_ms=round(duration_ms, 2),
                    ),
                ],
                result_returned={"status": "error"},
            )
        )

    def record_report(
        self,
        *,
        task: str,
        payload: Any,
        response: Any,
        duration_ms: float,
        caller: AuthenticatedCallerContext | None = None,
    ) -> None:
        if not self.enabled():
            return
        payload_sanitized, removed_fields = sanitize_payload(payload)
        response_dump = _model_dump(response) or {}
        response_sanitized, response_removed = sanitize_payload(response_dump)
        removed_fields.extend(f"response.{item}" for item in response_removed)
        execution_id = str(uuid.uuid4())
        status = str(response_sanitized.get("status") or "ok")
        signals = list(response_sanitized.get("signals") or [])
        evaluation = response_sanitized.get("evaluation")
        memory_created = bool(response_sanitized.get("stored"))
        memory_id = response_sanitized.get("memory_id")
        release_gate = self._release_gate_from_signals(signals)
        origin = str(
            payload_sanitized.get("source")
            or payload_sanitized.get("project_id")
            or "unknown"
        )
        caller_projection = (
            {
                "producer": caller.credential_id,
                "credential_id": caller.credential_id,
                "authenticated": caller.authenticated,
                "identity_strength": caller.identity_strength.value,
                "project_id_authenticated": caller.project_id,
                "project_id_authorized": payload_sanitized.get("project_id"),
                "caller_role": caller.caller_role.value,
                "environment": caller.environment,
            }
            if caller is not None
            else None
        )
        self._append(
            ExecutionRecord(
                execution_id=execution_id,
                audit_id=execution_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                origin_system=origin,
                task=task,
                status=status,
                payload_sanitized=payload_sanitized,
                removed_fields=list(dict.fromkeys(removed_fields)),
                caller=caller_projection,
                duration_ms=round(duration_ms, 2),
                public_response=sanitize_text(payload_sanitized.get("summary") or ""),
                release_gate=release_gate,
                evaluation=evaluation,
                signals=signals,
                memory_consulted=False,
                memory_created=memory_created,
                memory_id=str(memory_id) if memory_id else None,
                retry={"attempted": False, "count": 0},
                timeline=[
                    TimelineEvent(stage="report_received", status="ok", offset_ms=0.0),
                    TimelineEvent(stage="sanitization", status="completed"),
                    TimelineEvent(
                        stage="report_completed",
                        status=status,
                        offset_ms=round(duration_ms, 2),
                    ),
                ],
                result_returned=response_sanitized,
            )
        )

    def record_gemini_smoke(self, payload: Any, response: Any, duration_ms: float) -> None:
        if not self.enabled():
            return
        payload_sanitized, removed_fields = sanitize_payload(payload)
        execution_id = str(uuid.uuid4())
        reason = sanitize_text(response.reason, 500) if response.reason else None
        attempt_result = (
            "success"
            if response.status == "ok"
            else "failed" if response.executed else "blocked"
        )
        attempts = [
            ProviderAttempt(provider="gemini", result=attempt_result, detail=reason)
        ]
        if response.fallback:
            attempts.append(ProviderAttempt(provider="safe_local", result="fallback_success"))
        self._append(
            ExecutionRecord(
                execution_id=execution_id,
                audit_id=execution_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                origin_system="pedrocore",
                task="gemini_real_smoke",
                status=response.status,
                payload_sanitized=payload_sanitized,
                removed_fields=removed_fields,
                provider_requested="gemini",
                provider_selected="gemini" if response.executed else None,
                provider_effective=response.provider if response.executed else None,
                provider_attempts=attempts,
                fallback=response.fallback,
                fallback_reason=reason,
                duration_ms=round(duration_ms, 2),
                public_response=sanitize_text(response.public_response, 500),
                error=reason if response.status != "ok" else None,
                retry={"attempted": False, "count": 0},
                timeline=[
                    TimelineEvent(stage="gemini_smoke_guard", status="completed"),
                    TimelineEvent(stage="gemini_call", status=attempt_result),
                    TimelineEvent(
                        stage="gemini_smoke_completed",
                        status=response.status,
                        offset_ms=round(duration_ms, 2),
                    ),
                ],
                result_returned={
                    "status": response.status,
                    "executed": response.executed,
                    "call_count": response.call_count,
                    "fallback": response.fallback,
                },
            )
        )

    @staticmethod
    def _caller_projection(outcome: Any) -> dict[str, Any]:
        """Identidade autenticada vs. origem declarada, sem qualquer segredo.

        `credential_id` é um ID configurado ou fingerprint truncado: nunca a
        chave, nunca um hash reutilizável como credencial.
        """
        audit = outcome.audit
        return {
            "credential_id": audit.credential_id,
            "authenticated": audit.authenticated,
            "identity_strength": audit.identity_strength,
            "project_id_authenticated": audit.project_id_authenticated,
            "caller_role": audit.caller_role,
            "environment": audit.environment,
            "origin_system_declared": audit.origin_system_declared,
            "origin_validation": audit.origin_validation,
            "provider_selection_mode": audit.provider_selection_mode,
            "provider_selected": audit.provider_selected,
            "authorization_result": audit.authorization_result,
            "authorization_reason_code": audit.authorization_reason_code,
        }

    @staticmethod
    def _binding_projection(outcome: Any) -> dict[str, Any]:
        """Provider/model planejado pelo binding vs. efetivamente executado."""
        audit = outcome.audit
        return {
            "provider_requested": outcome.provider_requested,
            "provider_selected": audit.provider_selected,
            "provider_effective": outcome.provider_used,
            "model_requested": audit.model_requested,
            "model_selected": audit.model_selected,
            "model_effective": outcome.model,
            "model_source": audit.model_source,
            "selection_mode": audit.provider_selection_mode,
        }

    @staticmethod
    def _shadow_projection(outcome: Any) -> dict[str, Any] | None:
        """Decisão planejada e candidatos eliminados, sem segredos.

        Distingue o provider/model PLANEJADO do efetivamente executado; o
        candidato planejado nunca é executado.
        """
        decision = getattr(outcome, "shadow_decision", None)
        if decision is None:
            return None
        return {
            "enabled": decision.enabled,
            "routing_mode": decision.routing_mode.value,
            "configuration_valid": decision.configuration_valid,
            "configuration_reason": decision.configuration_reason,
            "policy_version": decision.policy_version,
            "project_id": decision.project_id,
            "task_type": decision.task_type,
            "provider_shadow_planned": decision.selected_provider,
            "model_shadow_planned": decision.selected_model,
            "provider_effective": outcome.provider_used,
            "model_effective": outcome.model,
            "would_differ_from_actual": decision.would_differ_from_actual,
            "selection_reason": decision.selection_reason,
            "real_provider_attempt_count": outcome.audit.real_provider_attempt_count,
            "candidates_considered": [
                {
                    "provider_id": candidate.provider_id,
                    "model_id": candidate.model_id,
                    "priority": candidate.priority,
                    "eliminated": candidate.eliminated,
                    "elimination_reason": (
                        candidate.elimination_reason.value
                        if candidate.elimination_reason is not None
                        else None
                    ),
                }
                for candidate in decision.candidates_considered
            ],
            "candidates_eliminated": [
                {
                    "provider_id": candidate.provider_id,
                    "elimination_reason": (
                        candidate.elimination_reason.value
                        if candidate.elimination_reason is not None
                        else None
                    ),
                }
                for candidate in decision.candidates_eliminated
            ],
        }

    @staticmethod
    def _generation_budget_projection(outcome: Any) -> dict[str, Any] | None:
        """Orçamento, tempos e término — somente números e rótulos.

        Nunca inclui prompt, resposta, contexto financeiro ou credencial. Note
        que `transport_close_outcome="confirmed"` convive com
        `completion_certainty="ambiguous"`: fechar a conexão local não prova
        que a geração remota terminou. `unknown` é o valor honesto quando o
        fechamento foi pedido mas o resultado não é observável.
        """
        audit = outcome.audit
        if audit.output_budget_effective is None and not audit.provider_attempts:
            return None
        return {
            "global_cap": audit.output_budget_global_cap,
            "model_cap": audit.output_budget_model_cap,
            "task_cap": audit.output_budget_task_cap,
            "effective_budget": audit.output_budget_effective,
            "budget_source": audit.output_budget_source,
            "budget_clamped": audit.output_budget_clamped,
            "orchestration_timeout_ms": audit.orchestration_timeout_ms,
            "transport_timeout_ms": audit.transport_timeout_ms,
            "transport_close_requested": audit.transport_close_requested,
            "transport_close_outcome": audit.transport_close_outcome,
            "finish_reason": audit.provider_finish_reason,
            "input_tokens": audit.provider_input_tokens,
            "output_tokens": audit.provider_output_tokens,
            "total_tokens": audit.provider_total_tokens,
            "output_truncated": audit.provider_output_truncated,
        }

    @staticmethod
    def _selected_provider(outcome: Any) -> str | None:
        requested = outcome.provider_requested
        if outcome.provider_used == "none":
            return None
        if requested == "auto":
            return outcome.provider_used if not outcome.fallback_used else None
        if requested in {"local", "local_qa"}:
            return "local_qa"
        return requested

    @staticmethod
    def _provider_attempts(
        outcome: Any,
        selected_provider: str | None,
        error: str | None,
    ) -> list[ProviderAttempt]:
        structured = list(getattr(outcome.audit, "provider_attempts", []) or [])
        if structured:
            attempts = [
                ProviderAttempt(
                    provider=str(item.get("provider_id") or "unknown"),
                    model=item.get("model_id"),
                    result=str(item.get("result") or "unknown"),
                    telemetry_structured=True,
                    request_id=item.get("request_id"),
                    attempt_id=item.get("attempt_id"),
                    ordinal=item.get("ordinal"),
                    selection_reason=item.get("selection_reason"),
                    started_at=item.get("started_at"),
                    finished_at=item.get("finished_at"),
                    external_dispatch=item.get("external_dispatch"),
                    completion_certainty=item.get("completion_certainty"),
                    failure_classification=item.get("failure_classification"),
                    circuit_state_before=item.get("circuit_state_before"),
                    circuit_state_after=item.get("circuit_state_after"),
                    half_open_probe=bool(item.get("half_open_probe")),
                    duration_ms=item.get("duration_ms"),
                    fallback_eligible=bool(item.get("fallback_eligible")),
                    fallback_decision_reason=item.get("fallback_decision_reason"),
                    output_budget=item.get("output_budget"),
                    budget_source=item.get("budget_source"),
                    budget_clamped=item.get("budget_clamped"),
                    orchestration_timeout_ms=item.get("orchestration_timeout_ms"),
                    transport_timeout_ms=item.get("transport_timeout_ms"),
                    transport_close_requested=bool(
                        item.get("transport_close_requested")
                    ),
                    transport_close_outcome=item.get("transport_close_outcome"),
                    finish_reason=item.get("finish_reason"),
                    input_tokens=item.get("input_tokens"),
                    output_tokens=item.get("output_tokens"),
                    total_tokens=item.get("total_tokens"),
                    output_truncated=bool(item.get("output_truncated")),
                )
                for item in structured
            ]
            if outcome.fallback_used and outcome.provider_used == "mock":
                attempts.append(
                    ProviderAttempt(
                        provider=outcome.provider_used,
                        result="fallback_success",
                    )
                )
            return attempts

        if outcome.provider_used == "none":
            return []
        if not outcome.fallback_used:
            return [
                ProviderAttempt(
                    provider=outcome.provider_used,
                    result="success",
                )
            ]
        if outcome.safe_mode_blocked:
            first_result = "blocked"
        elif outcome.error_code == "PROVIDER_TIMEOUT":
            first_result = "timeout"
        else:
            first_result = "failed_or_unavailable"
        attempts = [
            ProviderAttempt(
                provider=selected_provider or outcome.provider_requested,
                result=first_result,
                detail=error,
            )
        ]
        attempts.append(
            ProviderAttempt(provider=outcome.provider_used, result="fallback_success")
        )
        return attempts

    @staticmethod
    def _orchestration_signals(outcome: Any) -> list[dict[str, Any]]:
        signals = [
            {
                "type": "warning",
                "code": item.code,
                "severity": item.severity,
                "summary": sanitize_text(item.message, 1_000),
            }
            for item in outcome.warning_items
        ]
        if outcome.qa_skeleton is not None:
            qa = outcome.qa_skeleton
            signals.append(
                {
                    "type": "qa",
                    "status": qa.status,
                    "risk_level": qa.risk_level,
                    "can_advance": qa.can_advance,
                    "analysis_source": qa.analysis_source,
                    "findings": [sanitize_text(item, 1_000) for item in qa.findings],
                    "failures": [sanitize_text(item, 1_000) for item in qa.failures],
                }
            )
        return signals

    @staticmethod
    def _release_gate_from_signals(signals: list[dict[str, Any]]) -> dict[str, Any] | None:
        signal_types = {str(item.get("signal_type")) for item in signals}
        if "release_gate_blocked" in signal_types:
            return {"can_advance": False, "source": "technical_report_signal"}
        if "release_gate_passed" in signal_types:
            return {"can_advance": True, "source": "technical_report_signal"}
        return None


observability_service = ObservabilityService()


def elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1_000

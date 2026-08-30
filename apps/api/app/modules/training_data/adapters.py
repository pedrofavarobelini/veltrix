from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from pydantic import JsonValue

from app.modules.evidence_platform.schemas import EvidenceKind, EvidenceRecord
from app.modules.evidence_platform.service import evidence_ingestion_service
from app.modules.interaction_outcomes.schemas import InteractionOutcome
from app.modules.interaction_outcomes.service import interaction_outcome_service
from app.modules.operational_memory.schemas import MemoryLifecycle, OperationalMemoryEntry
from app.modules.operational_memory.service import operational_memory_service
from app.modules.report_memory.schemas import ReportMemoryEntry
from app.modules.report_memory.service import report_memory_service
from app.modules.training_data.schemas import (
    CandidateQualitySignals,
    HumanFeedback,
    SourceOutcome,
    TrainingCandidateProposal,
    TrainingEvidenceReference,
    TrainingRiskMetadata,
    TrainingPurpose,
    TrainingSourceSelection,
    TrainingSourceType,
)


class TrainingSourceSelectionError(LookupError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _signature(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _aware(value: str | datetime | None) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(value or "")
        except ValueError:
            parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _interaction_outcome(value: InteractionOutcome) -> SourceOutcome:
    if value.accepted is True:
        return SourceOutcome.ACCEPTED
    if value.rejected is True:
        return SourceOutcome.REJECTED
    return SourceOutcome.UNKNOWN


def _interaction_quality(value: InteractionOutcome) -> CandidateQualitySignals:
    known = _interaction_outcome(value) is not SourceOutcome.UNKNOWN
    qa_passed = "qa_passed" in {item.strip().lower() for item in value.quality_signals}
    return CandidateQualitySignals(
        provenance_quality=1.0,
        evidence_strength=0.9 if known else 0.5,
        completeness=0.95,
        source_reliability=0.9,
        outcome_known=known,
        qa_validated=qa_passed,
        human_feedback_present=value.feedback != "unknown",
        outcome_consistent=not (value.accepted is True and value.rejected is True),
        qa_result="passed" if qa_passed else "not_available",
    )


def _interaction_proposal(
    selection: TrainingSourceSelection,
    outcome: InteractionOutcome,
) -> TrainingCandidateProposal:
    features: dict[str, JsonValue] = {
        "input_signature": outcome.input_signature,
        "context_signature": outcome.context_signature,
        "provider": outcome.provider,
        "model": outcome.model,
        "response_characteristics": outcome.response_characteristics.model_dump(mode="json"),
    }
    target: dict[str, JsonValue] = {
        "response_strategy": outcome.response_strategy,
        "accepted": outcome.accepted,
        "rejected": outcome.rejected,
    }
    evidence = TrainingEvidenceReference(
        source_type=TrainingSourceType.INTERACTION_OUTCOME,
        source_id=outcome.outcome_id,
        project_id=outcome.project_id,
        source_schema_version=outcome.schema_version,
        policy_version="interaction-outcomes-v1",
        outcome=_interaction_outcome(outcome),
        content_signature=_signature({"features": features, "target": target}),
        observed_at=outcome.stored_at,
        run_id=outcome.audit_id,
        conversation_id=outcome.conversation_id,
        verified=True,
    )
    feedback = None
    if outcome.feedback != "unknown":
        feedback = HumanFeedback(
            feedback_id=outcome.outcome_id,
            rating=outcome.feedback,
            accepted=outcome.accepted,
            explicitly_provided=True,
        )
    return TrainingCandidateProposal(
        producer=selection.producer,
        source_type=selection.source_type,
        project_id=outcome.project_id,
        task_type=outcome.task_type,
        training_purpose=selection.training_purpose,
        input_features=features,
        context_features={
            "fallback_used": outcome.fallback_used,
            "regeneration_used": outcome.regeneration_used,
        },
        target=target,
        evidence_refs=[evidence],
        quality_signals=_interaction_quality(outcome),
        feedback=feedback,
        proposed_at=datetime.now(timezone.utc),
    )


def _human_feedback_proposal(
    selection: TrainingSourceSelection,
    outcome: InteractionOutcome,
) -> TrainingCandidateProposal:
    if outcome.feedback == "unknown":
        raise TrainingSourceSelectionError("EXPLICIT_HUMAN_FEEDBACK_NOT_FOUND")
    source_outcome = (
        SourceOutcome.ACCEPTED if outcome.feedback == "positive" else SourceOutcome.REJECTED
    )
    features: dict[str, JsonValue] = {
        "input_signature": outcome.input_signature,
        "context_signature": outcome.context_signature,
        "response_strategy": outcome.response_strategy,
    }
    target: dict[str, JsonValue] = {
        "rating": outcome.feedback,
        "accepted": outcome.accepted,
    }
    return TrainingCandidateProposal(
        producer=selection.producer,
        source_type=TrainingSourceType.HUMAN_FEEDBACK,
        project_id=outcome.project_id,
        task_type=outcome.task_type,
        training_purpose=selection.training_purpose,
        input_features=features,
        context_features={},
        target=target,
        evidence_refs=[
            TrainingEvidenceReference(
                source_type=TrainingSourceType.HUMAN_FEEDBACK,
                source_id=outcome.outcome_id,
                project_id=outcome.project_id,
                source_schema_version=outcome.schema_version,
                policy_version="interaction-feedback-v1",
                outcome=source_outcome,
                content_signature=_signature({"features": features, "target": target}),
                observed_at=outcome.stored_at,
                run_id=outcome.audit_id,
                conversation_id=outcome.conversation_id,
                verified=True,
            )
        ],
        quality_signals=_interaction_quality(outcome).model_copy(
            update={"outcome_known": True, "human_feedback_present": True}
        ),
        feedback=HumanFeedback(
            feedback_id=outcome.outcome_id,
            rating=outcome.feedback,
            accepted=outcome.accepted,
            explicitly_provided=True,
        ),
        proposed_at=datetime.now(timezone.utc),
    )


def _operational_proposal(
    selection: TrainingSourceSelection,
    memory: OperationalMemoryEntry,
) -> TrainingCandidateProposal:
    features: dict[str, JsonValue] = {
        "pattern_type": memory.pattern.pattern_type.value,
        "pattern_key": memory.pattern.pattern_key,
        "sample_size": memory.sample_size,
        "confidence": memory.confidence,
        "lifecycle": memory.lifecycle.value,
    }
    target: dict[str, JsonValue] = {
        "pattern_type": memory.pattern.pattern_type.value,
        "lifecycle": memory.lifecycle.value,
    }
    qa_validated = any(item.qa_validated for item in memory.evidence)
    source_outcome = (
        SourceOutcome.SUCCESSFUL
        if memory.lifecycle in {MemoryLifecycle.ACTIVE, MemoryLifecycle.RESOLVED}
        else SourceOutcome.BLOCKED
    )
    return TrainingCandidateProposal(
        producer=selection.producer,
        source_type=TrainingSourceType.OPERATIONAL_PATTERN,
        project_id=memory.project_id,
        task_type=memory.pattern.task_type,
        training_purpose=selection.training_purpose,
        input_features=features,
        context_features={"candidate_count": len(memory.candidate_ids)},
        target=target,
        evidence_refs=[
            TrainingEvidenceReference(
                source_type=TrainingSourceType.OPERATIONAL_PATTERN,
                source_id=memory.memory_id,
                project_id=memory.project_id,
                source_schema_version="1.0",
                policy_version=memory.policy_version,
                outcome=source_outcome,
                content_signature=_signature({"features": features, "target": target}),
                observed_at=memory.updated_at,
                verified=True,
            )
        ],
        quality_signals=CandidateQualitySignals(
            provenance_quality=1.0,
            evidence_strength=memory.confidence_breakdown.evidence_strength,
            completeness=min(1.0, 0.7 + min(memory.sample_size, 3) * 0.1),
            source_reliability=memory.confidence_breakdown.source_reliability,
            outcome_known=True,
            qa_validated=qa_validated,
            human_feedback_present=any(item.human_validated for item in memory.evidence),
            outcome_consistent=not memory.contradictions,
            contradiction_detected=bool(memory.contradictions),
            qa_result="passed" if qa_validated else "not_available",
        ),
        proposed_at=datetime.now(timezone.utc),
    )


def _report_outcome(status: str) -> SourceOutcome:
    normalized = status.strip().lower()
    if normalized in {"ok", "pass", "passed", "success", "successful", "accepted"}:
        return SourceOutcome.SUCCESSFUL
    if normalized in {"fail", "failed", "error", "rejected"}:
        return SourceOutcome.FAILED
    if normalized in {"blocked", "not_ready", "dataset_not_ready"}:
        return SourceOutcome.BLOCKED
    return SourceOutcome.UNKNOWN


def _report_proposal(
    selection: TrainingSourceSelection,
    report: ReportMemoryEntry,
) -> TrainingCandidateProposal:
    expected_report_type = {
        TrainingSourceType.QA_EVIDENCE: "qa_evidence",
        TrainingSourceType.RISK_ANALYSIS: "risk_analysis",
        TrainingSourceType.EXECUTION_OUTCOME: "execution_outcome",
    }.get(selection.source_type)
    if expected_report_type is not None and report.report_type != expected_report_type:
        raise TrainingSourceSelectionError("SOURCE_TYPE_MISMATCH")

    signal_types = sorted({item.signal_type for item in report.signals})
    severities = sorted({item.severity for item in report.signals})
    signal_types_json: list[JsonValue] = list(signal_types)
    severities_json: list[JsonValue] = list(severities)
    features: dict[str, JsonValue] = {
        "report_type": report.report_type,
        "status": report.status,
        "signal_types": signal_types_json,
        "signal_severities": severities_json,
        "signal_count": len(report.signals),
    }
    target: dict[str, JsonValue] = {
        "status": report.status,
        "report_type": report.report_type,
    }
    qa_passed = "qa_passed" in signal_types and "qa_failed" not in signal_types
    qa_failed = "qa_failed" in signal_types
    source_outcome = _report_outcome(report.status)
    source_policy = f"report-intelligence-v{report.schema_version}"
    quality = CandidateQualitySignals(
        provenance_quality=1.0,
        evidence_strength=max((item.confidence for item in report.signals), default=0.5),
        completeness=0.9 if report.report_id and report.status else 0.6,
        source_reliability=0.85,
        outcome_known=source_outcome is not SourceOutcome.UNKNOWN,
        qa_validated=qa_passed or qa_failed,
        human_feedback_present=False,
        outcome_consistent=not (qa_passed and qa_failed),
        contradiction_detected=qa_passed and qa_failed,
        qa_result="passed" if qa_passed else "failed" if qa_failed else "not_available",
    )
    risk_metadata = None
    if selection.source_type in {
        TrainingSourceType.RISK_ANALYSIS,
        TrainingSourceType.EXECUTION_OUTCOME,
    }:
        risk_metadata = TrainingRiskMetadata(
            risk_policy_version=source_policy,
            predicted_outcome=report.report_type,
            actual_outcome=report.status,
            reason_codes=signal_types[:50],
        )
    return TrainingCandidateProposal(
        producer=selection.producer,
        source_type=selection.source_type,
        project_id=report.project_id,
        task_type=report.report_type,
        training_purpose=selection.training_purpose,
        input_features=features,
        context_features={"has_run_id": report.source_run_id is not None},
        target=target,
        evidence_refs=[
            TrainingEvidenceReference(
                source_type=selection.source_type,
                source_id=report.report_id or report.memory_id,
                project_id=report.project_id,
                source_schema_version=report.schema_version,
                policy_version=source_policy,
                outcome=source_outcome,
                content_signature=_signature({"features": features, "target": target}),
                observed_at=_aware(report.updated_at or report.created_at),
                run_id=report.source_run_id,
                conversation_id=report.conversation_id,
                verified=True,
            )
        ],
        quality_signals=quality,
        risk_metadata=risk_metadata,
        proposed_at=datetime.now(timezone.utc),
    )



# Era 5 — promocao governada de evidencia registrada.
#
# Cada TIPO de evidencia admite propositos diferentes, e o teto declarado na
# policy nao basta. Uma fonte de aprendizado submetida por um consumidor e a
# origem mais sensivel que existe aqui: ela nasce de dado de pessoa, e por isso
# so admite `EVALUATION_ONLY` — treinar pesos a partir dela exigiria mudar esta
# tabela, com ADR, e nao mudar a request.
_PURPOSES_BY_EVIDENCE_KIND: dict[EvidenceKind, frozenset[TrainingPurpose]] = {
    EvidenceKind.QUALITY_EVIDENCE: frozenset(
        {TrainingPurpose.GENERATIVE_SFT, TrainingPurpose.EVALUATION_ONLY}
    ),
    EvidenceKind.EXECUTION_OUTCOME: frozenset(
        {TrainingPurpose.RISK, TrainingPurpose.EVALUATION_ONLY}
    ),
    EvidenceKind.LEARNING_SOURCE: frozenset({TrainingPurpose.EVALUATION_ONLY}),
}


def _evidence_outcome(record: EvidenceRecord) -> SourceOutcome:
    """Desfecho derivado do payload — nunca um campo que o produtor batizou.

    O contrato universal ja separou fato de julgamento: `outcome`, `result` e
    `producer_asserted_outcome` sao observacoes. Traduzi-las aqui e o PedroCore
    formando a SUA opiniao a partir delas.
    """
    payload = record.payload or {}
    if record.kind is EvidenceKind.QUALITY_EVIDENCE:
        return {
            "passed": SourceOutcome.SUCCESSFUL,
            "failed": SourceOutcome.FAILED,
            "blocked": SourceOutcome.BLOCKED,
        }.get(str(payload.get("outcome")), SourceOutcome.UNKNOWN)
    if record.kind is EvidenceKind.EXECUTION_OUTCOME:
        return {
            "succeeded": SourceOutcome.SUCCESSFUL,
            "failed": SourceOutcome.FAILED,
            "blocked": SourceOutcome.BLOCKED,
            "cancelled": SourceOutcome.BLOCKED,
            "rolled_back": SourceOutcome.FAILED,
        }.get(str(payload.get("result")), SourceOutcome.UNKNOWN)
    return {
        "successful": SourceOutcome.SUCCESSFUL,
        "failed": SourceOutcome.FAILED,
        "accepted": SourceOutcome.ACCEPTED,
        "rejected": SourceOutcome.REJECTED,
        "blocked": SourceOutcome.BLOCKED,
    }.get(str(payload.get("producer_asserted_outcome")), SourceOutcome.UNKNOWN)


def _evidence_features(record: EvidenceRecord) -> dict[str, JsonValue]:
    """Features DERIVADAS: contagens e rotulos, jamais o payload inteiro.

    Copiar o payload bruto para dentro do candidato transformaria o registro de
    evidencia em um atalho para conteudo nao minimizado entrar no dataset.
    """
    payload = record.payload or {}
    features: dict[str, JsonValue] = {
        "evidence_kind": record.kind.value,
        "contract_version": record.contract_version,
    }
    if record.kind is EvidenceKind.QUALITY_EVIDENCE:
        suites = payload.get("suites") or []
        features["suite_count"] = len(suites)
        features["total_cases"] = sum(int(item.get("total", 0)) for item in suites)
        features["failed_cases"] = sum(int(item.get("failed", 0)) for item in suites)
        features["environment"] = str(payload.get("environment", "unknown"))
    elif record.kind is EvidenceKind.EXECUTION_OUTCOME:
        features["operation"] = str(payload.get("operation", "unknown"))
        features["final_state"] = str(payload.get("final_state", "unknown"))
        features["diagnostic_count"] = len(payload.get("diagnostics") or [])
    else:
        derived = payload.get("derived_features") or {}
        features["derived_feature_count"] = len(derived)
        provenance = payload.get("provenance") or {}
        features["source_kind"] = str(provenance.get("source_kind", "unknown"))
    return features


def _evidence_proposal(
    selection: TrainingSourceSelection,
    record: EvidenceRecord,
) -> TrainingCandidateProposal:
    allowed = _PURPOSES_BY_EVIDENCE_KIND[record.kind]
    if selection.training_purpose not in allowed:
        raise TrainingSourceSelectionError("EVIDENCE_PURPOSE_NOT_ALLOWED_FOR_KIND")

    outcome = _evidence_outcome(record)
    features = _evidence_features(record)
    target: dict[str, JsonValue] = {
        "observed_outcome": outcome.value,
        "evidence_kind": record.kind.value,
    }
    quality = CandidateQualitySignals(
        provenance_quality=1.0,
        evidence_strength=0.8 if outcome is not SourceOutcome.UNKNOWN else 0.3,
        completeness=0.9 if record.correlation_id else 0.7,
        source_reliability=0.85,
        outcome_known=outcome is not SourceOutcome.UNKNOWN,
        qa_validated=record.kind is EvidenceKind.QUALITY_EVIDENCE,
        human_feedback_present=False,
        outcome_consistent=True,
        contradiction_detected=False,
    )
    return TrainingCandidateProposal(
        producer=selection.producer,
        project_id=selection.project_id.strip().lower(),
        source_type=TrainingSourceType.EVIDENCE_RECORD,
        task_type=f"evidence_{record.kind.value}",
        training_purpose=selection.training_purpose,
        input_features=features,
        context_features={"producer_id": record.producer_id},
        target=target,
        quality_signals=quality,
        evidence_refs=[
            TrainingEvidenceReference(
                source_type=TrainingSourceType.EVIDENCE_RECORD,
                source_id=record.evidence_record_id,
                project_id=record.project_id,
                source_schema_version=record.contract_version,
                policy_version=record.policy_version,
                outcome=outcome,
                content_signature=record.fingerprint,
                observed_at=record.submitted_at,
                run_id=record.correlation_id,
                verified=True,
            )
        ],
        derived_content_only=True,
    )

class TrainingSourceAdapterRegistry:
    """Sete selectors sobre os stores operacionais existentes; coleta nunca é automática."""

    automatic_collection = False

    def select(self, selection: TrainingSourceSelection) -> TrainingCandidateProposal:
        project_id = selection.project_id.strip().lower()
        source_id = selection.source_id.strip()
        if selection.source_type in {
            TrainingSourceType.INTERACTION_OUTCOME,
            TrainingSourceType.HUMAN_FEEDBACK,
        }:
            outcome = interaction_outcome_service.get(project_id, source_id)
            if outcome is None:
                raise TrainingSourceSelectionError("OPERATIONAL_SOURCE_NOT_FOUND")
            if selection.source_type is TrainingSourceType.HUMAN_FEEDBACK:
                return _human_feedback_proposal(selection, outcome)
            return _interaction_proposal(selection, outcome)

        if selection.source_type is TrainingSourceType.EVIDENCE_RECORD:
            record = evidence_ingestion_service.get_evidence(project_id, source_id)
            if record is None:
                raise TrainingSourceSelectionError("OPERATIONAL_SOURCE_NOT_FOUND")
            return _evidence_proposal(selection, record)

        if selection.source_type is TrainingSourceType.OPERATIONAL_PATTERN:
            memory = operational_memory_service.get_memory(project_id, source_id)
            if memory is None:
                raise TrainingSourceSelectionError("OPERATIONAL_SOURCE_NOT_FOUND")
            return _operational_proposal(selection, memory)

        report = report_memory_service.get_report(project_id, source_id)
        if report is None:
            raise TrainingSourceSelectionError("OPERATIONAL_SOURCE_NOT_FOUND")
        return _report_proposal(selection, report)


training_source_adapters = TrainingSourceAdapterRegistry()

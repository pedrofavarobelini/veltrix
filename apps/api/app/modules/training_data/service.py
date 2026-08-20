from __future__ import annotations

import hashlib
import json

from pydantic import JsonValue

from app.modules.training_data.privacy import scan_payload
from app.modules.training_data.schemas import (
    CandidateEvaluation,
    ContentClassification,
    SourceOutcome,
    TrainingExampleCandidate,
    TrainingExampleCandidateDraft,
    TrainingSourceDefinition,
    TrainingSourceType,
)

MAX_CANDIDATE_PAYLOAD_BYTES = 48_000

_SOURCE_DEFINITIONS = (
    TrainingSourceDefinition(
        source_type=TrainingSourceType.INTERACTION_OUTCOME,
        entity="InteractionOutcome",
        module="interaction_outcomes",
        required_provenance=["outcome_id", "policy_version", "content_signature", "outcome"],
        target_basis="accepted/rejected response strategy with observed feedback",
    ),
    TrainingSourceDefinition(
        source_type=TrainingSourceType.OPERATIONAL_PATTERN,
        entity="OperationalMemoryEntry",
        module="operational_memory",
        required_provenance=["memory_id", "policy_version", "evidence", "lifecycle"],
        target_basis="evidence-backed operational behavior, never raw memory payload",
    ),
    TrainingSourceDefinition(
        source_type=TrainingSourceType.REPORT_INTELLIGENCE_V2,
        entity="IntelligenceReportEnvelopeV2",
        module="report_intelligence",
        required_provenance=["report_id", "schema_version", "policy_version", "status"],
        target_basis="structured report outcome supported by evidence",
    ),
    TrainingSourceDefinition(
        source_type=TrainingSourceType.QA_EVIDENCE,
        entity="QaEvidencePayload",
        module="report_intelligence",
        required_provenance=["report_id", "run_id", "policy_version", "qa_result"],
        target_basis="QA result and reviewed corrective behavior",
    ),
    TrainingSourceDefinition(
        source_type=TrainingSourceType.RISK_ANALYSIS,
        entity="PreExecutionRiskAnalysis",
        module="risk_engine",
        required_provenance=["analysis_id", "risk_policy_version", "predicted_outcome"],
        target_basis="versioned analytical risk label; no replacement of deterministic risk",
    ),
    TrainingSourceDefinition(
        source_type=TrainingSourceType.EXECUTION_OUTCOME,
        entity="PostExecutionOutcome",
        module="risk_engine",
        required_provenance=["outcome_id", "contract_id", "risk_policy_version", "actual_outcome"],
        target_basis="predicted versus actual execution outcome",
    ),
    TrainingSourceDefinition(
        source_type=TrainingSourceType.HUMAN_FEEDBACK,
        entity="HumanFeedback",
        module="training_data",
        required_provenance=["feedback_id", "explicitly_provided", "policy_version", "outcome"],
        target_basis="explicit human preference or acceptance decision",
    ),
)


def source_definitions() -> list[TrainingSourceDefinition]:
    return [item.model_copy(deep=True) for item in _SOURCE_DEFINITIONS]


def _candidate_payload(draft: TrainingExampleCandidateDraft) -> dict[str, JsonValue]:
    payload: dict[str, JsonValue] = {
        "input_features": draft.input_features,
        "context_features": draft.context_features,
        "target": draft.target,
    }
    if draft.feedback is not None:
        payload["feedback"] = draft.feedback.model_dump(mode="json")
    if draft.risk_metadata is not None:
        payload["risk_metadata"] = draft.risk_metadata.model_dump(mode="json")
    return payload


def _candidate_id(draft: TrainingExampleCandidateDraft) -> str:
    stable = draft.model_dump(mode="json", exclude={"created_at"})
    stable["data_use"].pop("authorized_at", None)
    for evidence in stable["evidence_refs"]:
        evidence.pop("observed_at", None)
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    return "training-candidate-" + hashlib.sha256(encoded).hexdigest()[:24]


class DatasetFoundationService:
    @staticmethod
    def source_map() -> list[TrainingSourceDefinition]:
        return source_definitions()

    def evaluate(self, draft: TrainingExampleCandidateDraft) -> CandidateEvaluation:
        rejection_codes: set[str] = set()
        authorization = draft.data_use
        if not authorization.authorized or not authorization.allows_neural_training:
            rejection_codes.add("NEURAL_TRAINING_AUTHORIZATION_REQUIRED")
        if authorization.basis == "evaluation_only":
            rejection_codes.add("EVALUATION_ONLY_AUTHORIZATION")
        if authorization.content_classification is ContentClassification.RESTRICTED:
            rejection_codes.add("RESTRICTED_CONTENT_EXCLUDED")
        if (
            authorization.content_classification is ContentClassification.CONFIDENTIAL
            and not authorization.confidential_content_approved
        ):
            rejection_codes.add("CONFIDENTIAL_CONTENT_NOT_APPROVED")
        if not draft.derived_content_only:
            rejection_codes.add("RAW_CONTENT_NOT_ALLOWED")

        evidence_keys: set[tuple[TrainingSourceType, str]] = set()
        primary_found = False
        normalized_project = draft.project_id.strip().lower()
        for evidence in draft.evidence_refs:
            key = (evidence.source_type, evidence.source_id)
            if key in evidence_keys:
                rejection_codes.add("DUPLICATE_EVIDENCE_REFERENCE")
            evidence_keys.add(key)
            if evidence.source_type is draft.source_type:
                primary_found = True
            if not evidence.verified:
                rejection_codes.add("UNVERIFIED_PROVENANCE")
            if evidence.outcome is SourceOutcome.UNKNOWN:
                rejection_codes.add("SOURCE_OUTCOME_UNKNOWN")
            if evidence.policy_version.strip().lower() in {"unknown", "none", "n/a"}:
                rejection_codes.add("SOURCE_POLICY_UNKNOWN")
            if evidence.project_id.strip().lower() != normalized_project:
                rejection_codes.add("CROSS_PROJECT_PROVENANCE")
        if not primary_found:
            rejection_codes.add("PRIMARY_SOURCE_PROVENANCE_MISSING")

        if draft.source_type is TrainingSourceType.HUMAN_FEEDBACK:
            if draft.feedback is None or not draft.feedback.explicitly_provided:
                rejection_codes.add("EXPLICIT_HUMAN_FEEDBACK_REQUIRED")
        if draft.source_type is TrainingSourceType.QA_EVIDENCE:
            if draft.quality_signals.qa_result == "not_available":
                rejection_codes.add("QA_RESULT_REQUIRED")
        if draft.source_type in {
            TrainingSourceType.RISK_ANALYSIS,
            TrainingSourceType.EXECUTION_OUTCOME,
        } and draft.risk_metadata is None:
            rejection_codes.add("RISK_METADATA_REQUIRED")

        candidate_payload = _candidate_payload(draft)
        encoded_payload = json.dumps(
            candidate_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        if len(encoded_payload) > MAX_CANDIDATE_PAYLOAD_BYTES:
            rejection_codes.add("CANDIDATE_PAYLOAD_TOO_LARGE")
        privacy_findings = scan_payload(candidate_payload)
        rejection_codes.update(item.code for item in privacy_findings)

        if rejection_codes:
            return CandidateEvaluation(
                status="rejected",
                rejection_codes=sorted(rejection_codes),
                privacy_findings=privacy_findings,
            )
        return CandidateEvaluation(
            status="eligible",
            candidate=TrainingExampleCandidate(
                **draft.model_dump(),
                candidate_id=_candidate_id(draft),
            ),
        )


dataset_foundation_service = DatasetFoundationService()

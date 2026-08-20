from __future__ import annotations

from app.modules.training_data.privacy import scan_payload
from app.modules.training_data.schemas import (
    TRAINING_ACQUISITION_POLICY_VERSION,
    DataUseAuthorization,
    EligibilityDecision,
    EligibilityEvaluation,
    PrivacyClassification,
    SourceOutcome,
    TrainingCandidateProposal,
    TrainingPurpose,
    TrainingSourceType,
)

_PURPOSES_BY_SOURCE: dict[TrainingSourceType, frozenset[TrainingPurpose]] = {
    TrainingSourceType.INTERACTION_OUTCOME: frozenset(
        {
            TrainingPurpose.GENERATIVE_SFT,
            TrainingPurpose.PREFERENCE,
            TrainingPurpose.EVALUATION_ONLY,
        }
    ),
    TrainingSourceType.OPERATIONAL_PATTERN: frozenset(
        {
            TrainingPurpose.GENERATIVE_SFT,
            TrainingPurpose.RISK,
            TrainingPurpose.EVALUATION_ONLY,
        }
    ),
    TrainingSourceType.REPORT_INTELLIGENCE_V2: frozenset(
        {TrainingPurpose.GENERATIVE_SFT, TrainingPurpose.EVALUATION_ONLY}
    ),
    TrainingSourceType.QA_EVIDENCE: frozenset(
        {TrainingPurpose.GENERATIVE_SFT, TrainingPurpose.EVALUATION_ONLY}
    ),
    TrainingSourceType.RISK_ANALYSIS: frozenset(
        {TrainingPurpose.RISK, TrainingPurpose.EVALUATION_ONLY}
    ),
    TrainingSourceType.EXECUTION_OUTCOME: frozenset(
        {TrainingPurpose.RISK, TrainingPurpose.EVALUATION_ONLY}
    ),
    TrainingSourceType.HUMAN_FEEDBACK: frozenset(
        {TrainingPurpose.PREFERENCE, TrainingPurpose.EVALUATION_ONLY}
    ),
}


def _privacy_sections(proposal: TrainingCandidateProposal) -> dict:
    return {
        "producer": proposal.producer,
        "project_id": proposal.project_id,
        "task_type": proposal.task_type,
        "input_features": proposal.input_features,
        "context_features": proposal.context_features,
        "target": proposal.target,
        "evidence_refs": [item.model_dump(mode="json") for item in proposal.evidence_refs],
        "feedback": proposal.feedback.model_dump(mode="json") if proposal.feedback else None,
        "risk_metadata": (
            proposal.risk_metadata.model_dump(mode="json") if proposal.risk_metadata else None
        ),
    }


class TrainingEligibilityPolicy:
    """Policy versionada; nenhuma ausência ou ambiguidade concede eligibility."""

    policy_version = TRAINING_ACQUISITION_POLICY_VERSION

    def pre_screen(self, proposal: TrainingCandidateProposal) -> EligibilityEvaluation:
        return self._evaluate(proposal, authorization=None, review_approved=False, require_auth=False)

    def evaluate(
        self,
        proposal: TrainingCandidateProposal,
        authorization: DataUseAuthorization | None,
        *,
        review_approved: bool = False,
    ) -> EligibilityEvaluation:
        return self._evaluate(
            proposal,
            authorization=authorization,
            review_approved=review_approved,
            require_auth=True,
        )

    def _evaluate(
        self,
        proposal: TrainingCandidateProposal,
        *,
        authorization: DataUseAuthorization | None,
        review_approved: bool,
        require_auth: bool,
    ) -> EligibilityEvaluation:
        hard_codes: set[str] = set()
        review_codes: set[str] = set()

        privacy_findings = scan_payload(_privacy_sections(proposal))
        if privacy_findings:
            hard_codes.add("PRIVACY_GATE_REJECTED")

        allowed_purposes = _PURPOSES_BY_SOURCE[proposal.source_type]
        if proposal.training_purpose not in allowed_purposes:
            hard_codes.add("SOURCE_PURPOSE_MISMATCH")
        if not proposal.derived_content_only:
            hard_codes.add("RAW_CONTENT_NOT_ALLOWED")

        primary_found = False
        evidence_keys: set[tuple[TrainingSourceType, str]] = set()
        normalized_project = proposal.project_id.strip().lower()
        for evidence in proposal.evidence_refs:
            key = (evidence.source_type, evidence.source_id)
            if key in evidence_keys:
                hard_codes.add("DUPLICATE_EVIDENCE_REFERENCE")
            evidence_keys.add(key)
            primary_found = primary_found or evidence.source_type is proposal.source_type
            if evidence.project_id.strip().lower() != normalized_project:
                hard_codes.add("CROSS_PROJECT_PROVENANCE")
            if not evidence.verified:
                hard_codes.add("UNVERIFIED_PROVENANCE")
            if evidence.outcome is SourceOutcome.UNKNOWN:
                hard_codes.add("SOURCE_OUTCOME_UNKNOWN")
            if evidence.policy_version.strip().lower() in {"", "unknown", "none", "n/a"}:
                hard_codes.add("SOURCE_POLICY_UNKNOWN")
        if not primary_found:
            hard_codes.add("PRIMARY_SOURCE_PROVENANCE_MISSING")

        quality = proposal.quality_signals
        if quality.provenance_quality < 0.8:
            review_codes.add("PROVENANCE_QUALITY_REVIEW_REQUIRED")
        if quality.evidence_strength < 0.6:
            review_codes.add("EVIDENCE_STRENGTH_REVIEW_REQUIRED")
        if quality.completeness < 0.7:
            review_codes.add("COMPLETENESS_REVIEW_REQUIRED")
        if quality.source_reliability < 0.7:
            review_codes.add("SOURCE_RELIABILITY_REVIEW_REQUIRED")
        if not quality.outcome_consistent or quality.contradiction_detected:
            review_codes.add("CONTRADICTION_REVIEW_REQUIRED")

        if proposal.source_type is TrainingSourceType.HUMAN_FEEDBACK:
            if proposal.feedback is None or not proposal.feedback.explicitly_provided:
                hard_codes.add("EXPLICIT_HUMAN_FEEDBACK_REQUIRED")
        if proposal.source_type is TrainingSourceType.QA_EVIDENCE and not quality.qa_validated:
            hard_codes.add("QA_RESULT_REQUIRED")
        if proposal.source_type in {
            TrainingSourceType.RISK_ANALYSIS,
            TrainingSourceType.EXECUTION_OUTCOME,
        } and proposal.risk_metadata is None:
            hard_codes.add("RISK_METADATA_REQUIRED")

        if require_auth:
            self._evaluate_authorization(proposal, authorization, hard_codes)

        if hard_codes:
            decision = EligibilityDecision.NOT_ELIGIBLE
        elif review_codes and not review_approved:
            decision = EligibilityDecision.REQUIRES_REVIEW
        else:
            decision = EligibilityDecision.ELIGIBLE

        return EligibilityEvaluation(
            decision=decision,
            privacy_classification=(
                PrivacyClassification.REJECTED_SENSITIVE
                if privacy_findings
                else PrivacyClassification.SAFE
            ),
            reason_codes=sorted(hard_codes | (set() if review_approved else review_codes)),
            privacy_findings=privacy_findings,
        )

    @staticmethod
    def _evaluate_authorization(
        proposal: TrainingCandidateProposal,
        authorization: DataUseAuthorization | None,
        hard_codes: set[str],
    ) -> None:
        if authorization is None or not authorization.authorized:
            hard_codes.add("TRAINING_AUTHORIZATION_REQUIRED")
            return
        if authorization.authorized_project.strip().lower() != proposal.project_id.strip().lower():
            hard_codes.add("AUTHORIZED_PROJECT_MISMATCH")
        if authorization.training_purpose is not proposal.training_purpose:
            hard_codes.add("AUTHORIZED_PURPOSE_MISMATCH")
        if authorization.policy_version != TRAINING_ACQUISITION_POLICY_VERSION:
            hard_codes.add("AUTHORIZATION_POLICY_MISMATCH")
        if not authorization.authorized_scope.strip():
            hard_codes.add("AUTHORIZED_SCOPE_REQUIRED")
        evaluation_only = proposal.training_purpose is TrainingPurpose.EVALUATION_ONLY
        if evaluation_only:
            if authorization.basis != "evaluation_only" or authorization.allows_neural_training:
                hard_codes.add("EVALUATION_ONLY_SCOPE_INVALID")
        elif authorization.basis == "evaluation_only" or not authorization.allows_neural_training:
            hard_codes.add("NEURAL_TRAINING_AUTHORIZATION_REQUIRED")


training_eligibility_policy = TrainingEligibilityPolicy()

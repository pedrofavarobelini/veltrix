"""Gate 12 — Dataset Foundation, provenance e privacy fail-closed."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.modules.training_data.schemas import (
    ContentClassification,
    TrainingExampleCandidateDraft,
    TrainingSourceType,
)
from app.modules.training_data.service import dataset_foundation_service


def _signature(character: str = "a") -> str:
    return "sha256:" + character * 64


def _draft(**overrides) -> TrainingExampleCandidateDraft:
    now = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    values = {
        "producer": "alpha-technical-tool",
        "source_type": "interaction_outcome",
        "project_id": "alpha",
        "task_type": "qa_review",
        "input_features": {
            "intent": "Review a technical test result",
            "input_signature": _signature("1"),
        },
        "context_features": {"environment": "development", "language": "pt-BR"},
        "target": {"response_strategy": "explain failures and require evidence"},
        "evidence_refs": [
            {
                "source_type": "interaction_outcome",
                "source_id": "outcome-001",
                "project_id": "alpha",
                "source_schema_version": "1.0",
                "policy_version": "interaction-outcomes-v1",
                "outcome": "accepted",
                "content_signature": _signature("2"),
                "observed_at": now,
                "run_id": "run-001",
                "verified": True,
            }
        ],
        "quality_signals": {
            "provenance_quality": 0.9,
            "evidence_strength": 0.85,
            "completeness": 0.9,
            "outcome_consistent": True,
            "qa_result": "passed",
        },
        "data_use": {
            "authorized": True,
            "allows_neural_training": True,
            "basis": "explicit_human",
            "authorized_by": "reviewer-001",
            "authorized_at": now,
            "authorized_project": "alpha",
            "authorized_scope": "qa_review",
            "training_purpose": "generative_sft",
            "authorization_source": "explicit-stage12-test",
            "content_classification": "internal",
        },
        "created_at": now,
    }
    values.update(overrides)
    return TrainingExampleCandidateDraft.model_validate(values)


def test_all_real_sources_are_mapped_without_automatic_collection():
    definitions = dataset_foundation_service.source_map()
    assert {item.source_type for item in definitions} == set(TrainingSourceType)
    assert len(definitions) == 7
    assert all(item.automatic_collection is False for item in definitions)
    assert all(item.required_provenance for item in definitions)


def test_eligible_candidate_is_deterministic_and_does_not_persist_or_train():
    first = dataset_foundation_service.evaluate(_draft())
    second = dataset_foundation_service.evaluate(_draft())

    assert first.status == "eligible"
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.foundation_policy_version == "dataset-foundation-v1"
    assert first.persisted is False
    assert first.training_started is False
    assert first.automatic_collection_performed is False


@pytest.mark.parametrize(
    ("evidence_update", "expected_code"),
    [
        ({"verified": False}, "UNVERIFIED_PROVENANCE"),
        ({"outcome": "unknown"}, "SOURCE_OUTCOME_UNKNOWN"),
        ({"policy_version": "unknown"}, "SOURCE_POLICY_UNKNOWN"),
        ({"source_type": "qa_evidence"}, "PRIMARY_SOURCE_PROVENANCE_MISSING"),
    ],
)
def test_insufficient_provenance_is_rejected(evidence_update, expected_code):
    payload = _draft().model_dump(mode="json")
    payload["evidence_refs"][0].update(evidence_update)
    decision = dataset_foundation_service.evaluate(
        TrainingExampleCandidateDraft.model_validate(payload)
    )
    assert decision.status == "rejected"
    assert decision.candidate is None
    assert expected_code in decision.rejection_codes


def test_authorization_and_raw_content_fail_closed():
    unauthorized = _draft().model_copy(deep=True)
    unauthorized.data_use.authorized = False
    unauthorized.data_use.allows_neural_training = False
    raw = _draft(derived_content_only=False)

    unauthorized_result = dataset_foundation_service.evaluate(unauthorized)
    raw_result = dataset_foundation_service.evaluate(raw)

    assert "NEURAL_TRAINING_AUTHORIZATION_REQUIRED" in unauthorized_result.rejection_codes
    assert "RAW_CONTENT_NOT_ALLOWED" in raw_result.rejection_codes


@pytest.mark.parametrize(
    ("field", "sensitive", "expected_code"),
    [
        ("instruction", "api_key=sk-super-secret-123456", "SECRET_ASSIGNMENT_DETECTED"),
        ("config", "C:/project/.env.production ", "ENV_REFERENCE_DETECTED"),
        ("contact", "person@example.com", "EMAIL_PII_DETECTED"),
        ("cpf", "123.456.789-00", "CPF_PII_DETECTED"),
        ("account", "chave pix: personal-key", "PERSONAL_FINANCIAL_DATA_DETECTED"),
        ("path", "C:\\Users\\PrivatePerson\\report.txt", "PERSONAL_PATH_DETECTED"),
    ],
)
def test_sensitive_content_is_rejected_without_echo(field, sensitive, expected_code):
    decision = dataset_foundation_service.evaluate(
        _draft(input_features={field: sensitive})
    )
    serialized = decision.model_dump_json()
    assert decision.status == "rejected"
    assert expected_code in decision.rejection_codes
    assert sensitive not in serialized


def test_raw_conversation_field_is_rejected_without_copying_it():
    decision = dataset_foundation_service.evaluate(
        _draft(input_features={"raw_conversation": "private message body"})
    )
    assert decision.status == "rejected"
    assert "RAW_CONVERSATION_FIELD_DETECTED" in decision.rejection_codes
    assert "private message body" not in decision.model_dump_json()


def test_confidential_content_requires_explicit_approval():
    draft = _draft()
    draft.data_use.content_classification = ContentClassification.CONFIDENTIAL
    rejected = dataset_foundation_service.evaluate(draft)
    draft.data_use.confidential_content_approved = True
    accepted = dataset_foundation_service.evaluate(draft)
    assert "CONFIDENTIAL_CONTENT_NOT_APPROVED" in rejected.rejection_codes
    assert accepted.status == "eligible"


def test_source_specific_evidence_is_required():
    qa = _draft(source_type="qa_evidence")
    qa.evidence_refs[0].source_type = TrainingSourceType.QA_EVIDENCE
    qa.quality_signals.qa_result = "not_available"
    human = _draft(source_type="human_feedback")
    human.evidence_refs[0].source_type = TrainingSourceType.HUMAN_FEEDBACK
    risk = _draft(source_type="risk_analysis")
    risk.evidence_refs[0].source_type = TrainingSourceType.RISK_ANALYSIS

    assert "QA_RESULT_REQUIRED" in dataset_foundation_service.evaluate(qa).rejection_codes
    assert "EXPLICIT_HUMAN_FEEDBACK_REQUIRED" in (
        dataset_foundation_service.evaluate(human).rejection_codes
    )
    assert "RISK_METADATA_REQUIRED" in (
        dataset_foundation_service.evaluate(risk).rejection_codes
    )


def test_cross_project_provenance_is_rejected_at_schema_boundary():
    payload = _draft().model_dump(mode="json")
    payload["evidence_refs"][0]["project_id"] = "beta"
    with pytest.raises(ValidationError, match="mesmo projeto"):
        TrainingExampleCandidateDraft.model_validate(payload)

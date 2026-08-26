"""Gate 13A — aquisição opt-in, authorization, lifecycle e readiness."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.caller_identity.service import FLAG_CALLER_REGISTRY
from app.modules.interaction_outcomes.repository import (
    PostgreSQLInteractionOutcomeRepository,
)
from app.modules.interaction_outcomes.schemas import InteractionOutcome
from app.modules.interaction_outcomes.service import interaction_outcome_service
from app.modules.operational_memory.schemas import (
    ConfidenceBreakdown,
    EvidenceEffect,
    EvidenceReference,
    EvidenceSourceType,
    MemoryLifecycle,
    OperationalMemoryEntry,
    OperationalPattern,
    PatternType,
)
from app.modules.operational_memory.service import operational_memory_service
from app.modules.report_intelligence.schemas import ReportSignal
from app.modules.report_memory.repository import apply_postgresql_migrations
from app.modules.report_memory.schemas import ReportMemoryEntry
from app.modules.report_memory.service import (
    FLAG_DATABASE_URL,
    FLAG_PERSISTENCE,
    report_memory_service,
)
from app.modules.training_data.acquisition import (
    FLAG_READINESS_MIN_AUTHORIZED,
    FLAG_TRAINING_DATA_ADMIN_IDS,
    training_candidate_service,
)
from app.modules.training_data.adapters import (
    training_source_adapters,
)
from app.modules.training_data.policy import training_eligibility_policy
from app.modules.training_data.repository import (
    PostgreSQLTrainingCandidateRepository,
)
from app.modules.training_data.service import INTERNAL_ADAPTER_SOURCE_TYPES
from app.modules.training_data.schemas import (
    CandidateLifecycle,
    ContentClassification,
    DataUseAuthorization,
    DatasetReadinessPolicy,
    EligibilityDecision,
    TrainingPurpose,
    TrainingSourceSelection,
    TrainingSourceType,
)

client = TestClient(app)
MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
AUTH_HEADER = "X-PedroCore-Api-Key"
ALPHA_KEY = "alpha-training-candidate-synthetic"
BETA_KEY = "beta-training-candidate-synthetic"
SIGNATURE_A = "sha256:" + "a" * 64
SIGNATURE_B = "sha256:" + "b" * 64


def _registry(*, alpha_role: str = "technical_tool") -> str:
    return json.dumps(
        [
            {
                "credential_id": "alpha-technical-tool",
                "api_key": ALPHA_KEY,
                "project_id": "alpha",
                "role": alpha_role,
                "environment": "development",
                "allowed_origins": ["alpha"],
            },
            {
                "credential_id": "beta-technical-tool",
                "api_key": BETA_KEY,
                "project_id": "beta",
                "role": "technical_tool",
                "environment": "development",
                "allowed_origins": ["beta"],
            },
        ]
    )


def _outcome_payload(
    outcome_id: str = "outcome-alpha-1",
    *,
    project_id: str = "alpha",
    producer: str = "alpha-technical-tool",
    feedback: str = "positive",
    response_strategy: str = "structured_qa",
    quality_signals: list[str] | None = None,
) -> dict:
    return {
        "schema_version": "1.0",
        "outcome_id": outcome_id,
        "producer": producer,
        "project_id": project_id,
        "conversation_id": f"conversation-{outcome_id}",
        "message_id": f"message-{outcome_id}",
        "task_type": "qa_report_analysis",
        "input_signature": SIGNATURE_A,
        "context_signature": SIGNATURE_B,
        "provider": "mock",
        "model": "mock-v1",
        "response_strategy": response_strategy,
        "response_characteristics": {
            "length_bucket": "medium",
            "structured": True,
            "contains_citations": False,
            "safety_disclaimer": True,
            "truncated": False,
        },
        "fallback_used": False,
        "regeneration_used": False,
        "feedback": feedback,
        "accepted": True,
        "rejected": False,
        "quality_signals": quality_signals or ["qa_passed", "useful"],
        "audit_id": f"audit-{outcome_id}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _ingest_outcome(
    outcome_id: str = "outcome-alpha-1",
    *,
    key: str = ALPHA_KEY,
    **overrides,
) -> dict:
    response = client.post(
        "/api/interaction-outcomes",
        headers={AUTH_HEADER: key},
        json=_outcome_payload(outcome_id, **overrides),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _selection(
    source_id: str = "outcome-alpha-1",
    *,
    source_type: str = "interaction_outcome",
    purpose: str = "generative_sft",
    project_id: str = "alpha",
    producer: str = "alpha-technical-tool",
) -> dict:
    return {
        "producer": producer,
        "project_id": project_id,
        "source_type": source_type,
        "source_id": source_id,
        "training_purpose": purpose,
    }


def _select(**kwargs) -> dict:
    response = client.post(
        "/api/training-candidates/select",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_selection(**kwargs),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _authorize(candidate_id: str, *, key: str = ALPHA_KEY) -> dict:
    response = client.post(
        f"/api/training-candidates/{candidate_id}/authorize",
        headers={AUTH_HEADER: key},
        json={
            "project_id": "alpha",
            "authorized_scope": "qa_report_analysis",
            "authorization_source": "explicit-gate-13a-review",
            "basis": "explicit_human",
            "content_classification": "internal",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture(autouse=True)
def clean_services(monkeypatch):
    for name in (
        FLAG_CALLER_REGISTRY,
        FLAG_DATABASE_URL,
        FLAG_PERSISTENCE,
        FLAG_TRAINING_DATA_ADMIN_IDS,
        FLAG_READINESS_MIN_AUTHORIZED,
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    monkeypatch.setenv(FLAG_TRAINING_DATA_ADMIN_IDS, "alpha-technical-tool")
    interaction_outcome_service.reset()
    operational_memory_service.reset()
    report_memory_service.reset()
    training_candidate_service.reset()
    yield
    interaction_outcome_service.reset()
    operational_memory_service.reset()
    report_memory_service.reset()
    training_candidate_service.reset()


@pytest.fixture
def postgres_url() -> Iterator[str]:
    value = (os.environ.get("PEDROCORE_TEST_POSTGRES_URL") or "").strip()
    if not value:
        pytest.skip("PEDROCORE_TEST_POSTGRES_URL não configurada")
    apply_postgresql_migrations(value, MIGRATIONS)
    candidates = PostgreSQLTrainingCandidateRepository(value)
    outcomes = PostgreSQLInteractionOutcomeRepository(value)
    candidates.clear()
    outcomes.clear()
    yield value
    candidates.clear()
    outcomes.clear()


def _stored_outcome(outcome_id: str = "adapter-outcome") -> InteractionOutcome:
    now = datetime.now(timezone.utc)
    payload = _outcome_payload(outcome_id)
    return InteractionOutcome(
        **payload,
        caller_role="technical_tool",
        environment="development",
        stored_at=now,
        retention_until=now + timedelta(days=90),
    )


def _operational_memory() -> OperationalMemoryEntry:
    now = datetime.now(timezone.utc)
    evidence = EvidenceReference(
        source_type=EvidenceSourceType.INTERACTION_OUTCOME,
        source_id="adapter-outcome",
        effect=EvidenceEffect.SUPPORTS,
        source_reliability=0.9,
        evidence_strength=0.9,
        context_match=0.9,
        qa_validated=True,
        human_validated=False,
        observed_at=now,
    )
    return OperationalMemoryEntry(
        memory_id="memory-adapter-1",
        project_id="alpha",
        pattern=OperationalPattern(
            pattern_id="pattern-adapter-1",
            pattern_type=PatternType.SUCCESS_PATTERN,
            pattern_key="qa.structured.success",
            task_type="qa_report_analysis",
            summary="structured success",
        ),
        confidence=0.9,
        confidence_breakdown=ConfidenceBreakdown(
            source_reliability=0.9,
            evidence_strength=0.9,
            frequency=0.8,
            recency=0.9,
            context_match=0.9,
            qa_validation=1.0,
            human_validation=0.0,
            contradiction_penalty=0.0,
        ),
        lifecycle=MemoryLifecycle.ACTIVE,
        candidate_ids=["operational-candidate-1"],
        evidence=[evidence],
        contradictions=[],
        sample_size=3,
        policy_version="operational-memory-v1",
        created_at=now,
        updated_at=now,
        retention_until=now + timedelta(days=90),
    )


def _report(report_id: str, report_type: str) -> ReportMemoryEntry:
    now = datetime.now(timezone.utc).isoformat()
    signal_type = "qa_passed" if report_type == "qa_evidence" else "release_gate_passed"
    return ReportMemoryEntry(
        memory_id=f"memory-{report_id}",
        report_id=report_id,
        schema_version="2.0",
        producer="alpha-technical-tool",
        project_id="alpha",
        report_type=report_type,
        source_run_id=f"run-{report_id}",
        status="passed",
        signals=[
            ReportSignal(
                project_id="alpha",
                report_type=report_type,
                signal_type=signal_type,
                severity="info",
                summary="validated",
                confidence=0.9,
            )
        ],
        created_at=now,
        updated_at=now,
        retention_until=(datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
    )


def test_internal_source_adapters_use_existing_domain_records(monkeypatch):
    """Cobre todas as origens com adapter interno.

    Origens submetidas por consumer externo (Stage 13 da Elyra) ficam fora por
    construcao: o PedroCore nao alcanca a base delas.
    """
    outcome = _stored_outcome()
    memory = _operational_memory()
    reports = {
        "report-general": _report("report-general", "interaction_quality"),
        "report-qa": _report("report-qa", "qa_evidence"),
        "report-risk": _report("report-risk", "risk_analysis"),
        "report-execution": _report("report-execution", "execution_outcome"),
    }
    monkeypatch.setattr(interaction_outcome_service, "get", lambda *_args: outcome)
    monkeypatch.setattr(operational_memory_service, "get_memory", lambda *_args: memory)
    monkeypatch.setattr(
        report_memory_service,
        "get_report",
        lambda _project, source_id: reports.get(source_id),
    )
    selections = [
        (TrainingSourceType.INTERACTION_OUTCOME, "adapter-outcome", TrainingPurpose.GENERATIVE_SFT),
        (TrainingSourceType.OPERATIONAL_PATTERN, "memory-adapter-1", TrainingPurpose.GENERATIVE_SFT),
        (TrainingSourceType.REPORT_INTELLIGENCE_V2, "report-general", TrainingPurpose.GENERATIVE_SFT),
        (TrainingSourceType.QA_EVIDENCE, "report-qa", TrainingPurpose.GENERATIVE_SFT),
        (TrainingSourceType.RISK_ANALYSIS, "report-risk", TrainingPurpose.RISK),
        (TrainingSourceType.EXECUTION_OUTCOME, "report-execution", TrainingPurpose.RISK),
        (TrainingSourceType.HUMAN_FEEDBACK, "adapter-outcome", TrainingPurpose.PREFERENCE),
    ]

    proposals = [
        training_source_adapters.select(
            TrainingSourceSelection(
                producer="alpha-technical-tool",
                project_id="alpha",
                source_type=source_type,
                source_id=source_id,
                training_purpose=purpose,
            )
        )
        for source_type, source_id, purpose in selections
    ]

    assert {item.source_type for item in proposals} == INTERNAL_ADAPTER_SOURCE_TYPES
    assert all(all(ref.verified for ref in item.evidence_refs) for item in proposals)
    assert all(not hasattr(item, "data_use") for item in proposals)
    assert training_source_adapters.automatic_collection is False
    risk_as_sft = proposals[4].model_copy(
        update={"training_purpose": TrainingPurpose.GENERATIVE_SFT}
    )
    purpose_decision = training_eligibility_policy.pre_screen(risk_as_sft)
    assert purpose_decision.decision is EligibilityDecision.NOT_ELIGIBLE
    assert "SOURCE_PURPOSE_MISMATCH" in purpose_decision.reason_codes


def test_eligibility_requires_authorization_and_reviews_weak_evidence():
    _ingest_outcome()
    proposal = _select()["record"]["proposal"]
    parsed = training_source_adapters.select(
        TrainingSourceSelection(**_selection())
    )
    now = datetime.now(timezone.utc)
    authorization = DataUseAuthorization(
        authorized=True,
        allows_neural_training=True,
        basis="explicit_human",
        authorized_by="alpha-technical-tool",
        authorized_at=now,
        authorized_project="alpha",
        authorized_scope="qa_report_analysis",
        training_purpose=TrainingPurpose.GENERATIVE_SFT,
        authorization_source="explicit-gate-13a-review",
        content_classification=ContentClassification.INTERNAL,
    )
    weak = parsed.model_copy(
        update={
            "quality_signals": parsed.quality_signals.model_copy(
                update={"evidence_strength": 0.4}
            )
        }
    )
    unverified = parsed.model_copy(deep=True)
    unverified.evidence_refs[0].verified = False

    assert proposal is not None
    assert training_eligibility_policy.evaluate(parsed, None).decision is (
        EligibilityDecision.NOT_ELIGIBLE
    )
    assert training_eligibility_policy.evaluate(parsed, authorization).decision is (
        EligibilityDecision.ELIGIBLE
    )
    assert training_eligibility_policy.evaluate(weak, authorization).decision is (
        EligibilityDecision.REQUIRES_REVIEW
    )
    assert training_eligibility_policy.evaluate(unverified, authorization).decision is (
        EligibilityDecision.NOT_ELIGIBLE
    )


def test_idempotent_selection_and_explicit_authorization_lifecycle():
    _ingest_outcome()
    first = _select()
    second = _select()
    candidate_id = first["record"]["candidate_id"]

    assert first["record"]["lifecycle"] == "proposed"
    assert first["record"]["eligibility"] == "not_eligible"
    assert first["record"]["authorization"] is None
    assert first["stored"] is True
    assert second["duplicate"] is True
    assert second["record"]["candidate_id"] == candidate_id

    authorized = _authorize(candidate_id)
    assert authorized["record"]["lifecycle"] == "authorized"
    assert authorized["record"]["eligibility"] == "eligible"
    assert authorized["record"]["authorization"]["authorized_by"] == "alpha-technical-tool"
    assert authorized["record"]["authorization"]["authorized_project"] == "alpha"
    assert authorized["record"]["authorization"]["training_purpose"] == "generative_sft"
    assert authorized["record"]["candidate"]["candidate_id"] == candidate_id

    page = client.get(
        "/api/training-candidates/alpha",
        headers={AUTH_HEADER: ALPHA_KEY},
    )
    assert page.status_code == 200
    assert page.json()["total"] == 1


def test_review_approve_exclude_and_direct_exclusion(monkeypatch):
    _ingest_outcome("weak-review")
    original_select = training_source_adapters.select

    def weak_select(selection):
        proposal = original_select(selection)
        return proposal.model_copy(
            update={
                "quality_signals": proposal.quality_signals.model_copy(
                    update={"evidence_strength": 0.4}
                )
            }
        )

    monkeypatch.setattr(training_source_adapters, "select", weak_select)
    candidate = _select(source_id="weak-review")["record"]
    assert candidate["lifecycle"] == "review_required"
    approved = client.post(
        f"/api/training-candidates/{candidate['candidate_id']}/review",
        headers={AUTH_HEADER: ALPHA_KEY},
        json={"project_id": "alpha", "decision": "approve", "reason_code": "HUMAN_VERIFIED"},
    )
    assert approved.status_code == 200
    assert approved.json()["record"]["lifecycle"] == "proposed"
    assert approved.json()["record"]["review_approved"] is True
    assert _authorize(candidate["candidate_id"])["record"]["lifecycle"] == "authorized"

    _ingest_outcome("weak-exclude")
    review_excluded = _select(source_id="weak-exclude")["record"]
    excluded = client.post(
        f"/api/training-candidates/{review_excluded['candidate_id']}/review",
        headers={AUTH_HEADER: ALPHA_KEY},
        json={"project_id": "alpha", "decision": "exclude", "reason_code": "LOW_VALUE"},
    )
    assert excluded.status_code == 200
    assert excluded.json()["record"]["lifecycle"] == "excluded"

    monkeypatch.setattr(training_source_adapters, "select", original_select)
    _ingest_outcome("direct-exclude")
    proposed = _select(source_id="direct-exclude")["record"]
    direct = client.post(
        f"/api/training-candidates/{proposed['candidate_id']}/exclude",
        headers={AUTH_HEADER: ALPHA_KEY},
        json={"project_id": "alpha", "reason_code": "OUT_OF_SCOPE"},
    )
    assert direct.status_code == 200
    assert direct.json()["record"]["lifecycle"] == "excluded"


def test_consumed_lineage_revocation_and_reauthorization_bypass_are_blocked():
    _ingest_outcome()
    candidate_id = _select()["record"]["candidate_id"]
    _authorize(candidate_id)
    consumed = training_candidate_service.mark_consumed(
        "alpha", candidate_id, "canonical-dataset-future-1"
    )
    assert consumed.lifecycle is CandidateLifecycle.CONSUMED
    assert consumed.consumed_dataset_ids == ["canonical-dataset-future-1"]

    revoked = client.post(
        f"/api/training-candidates/{candidate_id}/revoke",
        headers={AUTH_HEADER: ALPHA_KEY},
        json={"project_id": "alpha", "reason_code": "CONSENT_REVOKED"},
    )
    reauthorize = client.post(
        f"/api/training-candidates/{candidate_id}/authorize",
        headers={AUTH_HEADER: ALPHA_KEY},
        json={
            "project_id": "alpha",
            "authorized_scope": "qa_report_analysis",
            "authorization_source": "retry",
            "basis": "explicit_human",
            "content_classification": "internal",
        },
    )
    assert revoked.status_code == 200
    assert revoked.json()["record"]["lifecycle"] == "revoked"
    assert revoked.json()["record"]["consumed_dataset_ids"] == [
        "canonical-dataset-future-1"
    ]
    assert reauthorize.status_code == 409


@pytest.mark.parametrize("feedback", ["positive", "negative"])
def test_human_feedback_is_quality_evidence_but_never_authorization(feedback):
    source_id = f"feedback-{feedback}"
    _ingest_outcome(source_id, feedback=feedback)
    selected = _select(
        source_id=source_id,
        source_type="human_feedback",
        purpose="preference",
    )["record"]
    assert selected["lifecycle"] == "proposed"
    assert selected["eligibility"] == "not_eligible"
    assert selected["authorization"] is None
    assert selected["proposal"]["quality_signals"]["human_feedback_present"] is True
    assert selected["reason_codes"] == ["TRAINING_AUTHORIZATION_REQUIRED"]


def test_privacy_rejection_never_enters_store_or_echoes_secret():
    secret = "api_key=sk-super-secret-123456789"
    _ingest_outcome("privacy-source", response_strategy=secret)
    selected = _select(source_id="privacy-source")
    serialized = json.dumps(selected)
    record = selected["record"]

    assert record["lifecycle"] == "excluded"
    assert record["privacy_classification"] == "rejected_sensitive"
    assert record["source_id"] is None
    assert record["proposal"] is None
    assert record["candidate"] is None
    assert secret not in serialized
    assert "SECRET_ASSIGNMENT_DETECTED" in {
        item["code"] for item in record["privacy_findings"]
    }


def test_authentication_capability_project_isolation_and_mass_assignment(monkeypatch):
    _ingest_outcome()
    candidate_id = _select()["record"]["candidate_id"]

    invalid = client.get(
        "/api/training-candidates/alpha",
        headers={AUTH_HEADER: "invalid-training-credential"},
    )
    cross_project = client.get(
        "/api/training-candidates/alpha",
        headers={AUTH_HEADER: BETA_KEY},
    )
    forged_selection = _selection()
    forged_selection["training_authorized"] = True
    mass_assignment = client.post(
        "/api/training-candidates/select",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=forged_selection,
    )
    forged_auth = client.post(
        f"/api/training-candidates/{candidate_id}/authorize",
        headers={AUTH_HEADER: ALPHA_KEY},
        json={
            "project_id": "alpha",
            "authorized_scope": "qa_report_analysis",
            "authorization_source": "forged",
            "basis": "explicit_human",
            "content_classification": "internal",
            "authorized_by": "attacker",
            "authorized_project": "beta",
            "training_authorized": True,
        },
    )
    wrong_scope = client.post(
        f"/api/training-candidates/{candidate_id}/authorize",
        headers={AUTH_HEADER: ALPHA_KEY},
        json={
            "project_id": "alpha",
            "authorized_scope": "different_task",
            "authorization_source": "explicit-review",
            "basis": "explicit_human",
            "content_classification": "internal",
        },
    )

    monkeypatch.setenv(FLAG_TRAINING_DATA_ADMIN_IDS, "")
    inadequate_capability = client.post(
        f"/api/training-candidates/{candidate_id}/authorize",
        headers={AUTH_HEADER: ALPHA_KEY},
        json={
            "project_id": "alpha",
            "authorized_scope": "qa_report_analysis",
            "authorization_source": "explicit-review",
            "basis": "explicit_human",
            "content_classification": "internal",
        },
    )

    assert invalid.status_code == 401
    assert cross_project.status_code == 403
    assert mass_assignment.status_code == 422
    assert forged_auth.status_code == 422
    assert wrong_scope.status_code == 409
    assert "AUTHORIZED_SCOPE_MISMATCH" in wrong_scope.json()["reason_codes"]
    assert inadequate_capability.status_code == 403
    assert inadequate_capability.json()["error_code"] == (
        "TRAINING_CANDIDATE_ADMIN_REQUIRED"
    )


def test_local_unregistered_identity_never_becomes_training_admin(monkeypatch):
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.setenv(FLAG_TRAINING_DATA_ADMIN_IDS, "local-unauthenticated")
    response = client.get("/api/training-candidates/alpha")

    assert response.status_code == 403
    assert response.json()["error_code"] == "TRAINING_CANDIDATE_ADMIN_REQUIRED"


def test_source_and_project_spoofing_cannot_manipulate_provenance():
    _ingest_outcome(
        "beta-only",
        key=BETA_KEY,
        project_id="beta",
        producer="beta-technical-tool",
    )
    cross_selection = client.post(
        "/api/training-candidates/select",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_selection(source_id="beta-only"),
    )
    payload_spoof = client.post(
        "/api/training-candidates/select",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_selection(project_id="beta"),
    )
    provenance_injection = _selection(source_id="beta-only")
    provenance_injection["evidence_refs"] = [
        {"project_id": "alpha", "verified": True, "source_id": "beta-only"}
    ]
    injected = client.post(
        "/api/training-candidates/select",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=provenance_injection,
    )

    assert cross_selection.status_code == 404
    assert payload_spoof.status_code == 403
    assert injected.status_code == 422


def test_readiness_uses_diversity_quality_and_governance_not_only_count():
    _ingest_outcome()
    candidate_id = _select()["record"]["candidate_id"]
    _authorize(candidate_id)
    policy = DatasetReadinessPolicy(
        minimum_authorized_candidates=1,
        minimum_source_types=2,
        minimum_task_types=2,
        minimum_training_purposes=2,
    )
    report = training_candidate_service.readiness("alpha", policy)
    endpoint = client.get(
        "/api/training-candidates/alpha/readiness",
        headers={AUTH_HEADER: ALPHA_KEY},
    )

    assert report.metrics.authorized_candidates == 1
    assert report.readiness == "DATASET_NOT_READY"
    assert "INSUFFICIENT_SOURCE_DIVERSITY" in report.blocker_codes
    assert "INSUFFICIENT_TASK_DIVERSITY" in report.blocker_codes
    assert "INSUFFICIENT_PURPOSE_COVERAGE" in report.blocker_codes
    assert endpoint.status_code == 200
    assert endpoint.json()["readiness"] == "DATASET_NOT_READY"
    assert "READINESS_VOLUME_POLICY_NOT_CONFIGURED" in endpoint.json()["blocker_codes"]
    assert endpoint.json()["canonical_dataset_created"] is False
    assert endpoint.json()["training_started"] is False


def test_postgresql_candidate_store_reconnects_and_preserves_revocation(
    postgres_url,
    monkeypatch,
):
    monkeypatch.setenv(FLAG_PERSISTENCE, "postgresql")
    monkeypatch.setenv(FLAG_DATABASE_URL, postgres_url)
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    monkeypatch.setenv(FLAG_TRAINING_DATA_ADMIN_IDS, "alpha-technical-tool")
    interaction_outcome_service.reset()
    training_candidate_service.reset()

    _ingest_outcome("postgres-source")
    selected = _select(source_id="postgres-source")
    candidate_id = selected["record"]["candidate_id"]
    _authorize(candidate_id)
    training_candidate_service.reset()
    page = client.get(
        "/api/training-candidates/alpha",
        headers={AUTH_HEADER: ALPHA_KEY},
    )
    revoked = client.post(
        f"/api/training-candidates/{candidate_id}/revoke",
        headers={AUTH_HEADER: ALPHA_KEY},
        json={"project_id": "alpha", "reason_code": "SOURCE_WITHDRAWN"},
    )
    repository = PostgreSQLTrainingCandidateRepository(postgres_url)

    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["lifecycle"] == "authorized"
    assert revoked.status_code == 200
    persisted = repository.get("alpha", candidate_id)
    assert persisted is not None
    assert persisted.lifecycle is CandidateLifecycle.REVOKED
    assert repository.count("beta") == 0

"""Learning governado Elyra V1 (Stage 13): fail-closed, sintetico e sem rede.

Esta capability nao treina nada. Ela existe para garantir que, se um dia um dado
puder ser usado para evolucao, ele so chegue ao Dataset Foundation depois de
consentimento, elegibilidade, minimizacao, proveniencia e quality gate.

Por isso a suite e majoritariamente **negativa**: o valor esta em provar o que
NAO passa. Nenhum provider participa — nem real, nem mock.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
)
from app.modules.contracts import codes
from app.modules.elyra_learning.schemas import (
    ELYRA_LEARNING_CONTRACT_VERSION,
    ELYRA_LEARNING_EXPORT_SCHEMA_VERSION,
    ELYRA_LEARNING_INPUT_SCHEMA_VERSION,
    ELYRA_LEARNING_MESSAGE,
    ELYRA_LEARNING_OUTPUT_SCHEMA_VERSION,
    ELYRA_LEARNING_POLICY_VERSION,
    ELYRA_LEARNING_TASK_TYPE,
    REVOKE_OPERATION,
    SUBMIT_OPERATION,
)
from app.modules.elyra_learning.service import canonical_fingerprint
from app.modules.elyra_textual.idempotency import elyra_idempotency_service
from app.modules.report_memory.service import FLAG_PERSISTENCE
from app.modules.training_data.acquisition import (
    external_candidate_id,
    training_candidate_service,
)
from app.modules.training_data.schemas import (
    CandidateLifecycle,
    EligibilityDecision,
    TrainingPurpose,
    TrainingSourceType,
)

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
ELYRA_CREDENTIAL = "elyra-learning-test-credential"
ELYRA_TECHNICAL_CREDENTIAL = "elyra-learning-technical-denied"
STRUCTA_CREDENTIAL = "structa-learning-denied"

PRODUCED_AT = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
CONSENT_AT = PRODUCED_AT - timedelta(days=3)


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch):
    elyra_idempotency_service.clear()
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    monkeypatch.setenv("PEDROCORE_PROVIDER_ROUTING_MODE", "legacy")
    training_candidate_service.reset()
    yield
    training_candidate_service.reset()
    elyra_idempotency_service.clear()


@pytest.fixture
def elyra_registry(monkeypatch):
    registry = [
        {
            "credential_id": "elyra-learning-v1",
            "api_key": ELYRA_CREDENTIAL,
            "project_id": "elyra",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["elyra"],
        },
        {
            "credential_id": "elyra-learning-technical",
            "api_key": ELYRA_TECHNICAL_CREDENTIAL,
            "project_id": "elyra",
            "role": "technical_tool",
            "environment": "development",
            "allowed_origins": ["elyra"],
        },
        {
            "credential_id": "structa-learning-denied",
            "api_key": STRUCTA_CREDENTIAL,
            "project_id": "structa",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["structa"],
        },
    ]
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, json.dumps(registry))
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    return registry


# --------------------------------------------------------------------------
# Construcao do payload governado
# --------------------------------------------------------------------------


def _aggregate(mean, delta, trend, samples) -> dict:
    return {"mean": mean, "delta": delta, "trend": trend, "samples": samples}


def _payload(**overrides) -> dict:
    payload = {
        "daysInWindow": 28,
        "mood": _aggregate(7.0, 0.5, "up", 28),
        "anxiety": _aggregate(3.0, -0.5, "down", 28),
        "energy": _aggregate(6.0, 0.0, "stable", 28),
        "sleepDurationMinutes": _aggregate(450.0, 20.0, "up", 27),
        "daysWithMood": 28,
        "daysWithAnxiety": 28,
        "daysWithEnergy": 28,
        "daysWithSleep": 27,
        "cycleEnabled": False,
    }
    payload.update(overrides)
    return payload


def _quality_checks() -> list[dict]:
    return [
        {"name": name, "passed": True}
        for name in (
            "minimum_days_with_data",
            "window_completeness",
            "no_free_text",
            "no_direct_identifier",
            "value_domains",
        )
    ]


def _submission(**overrides) -> dict:
    payload = overrides.pop("payload", None) or _payload()
    context = {
        "contractVersion": ELYRA_LEARNING_CONTRACT_VERSION,
        "inputSchemaVersion": ELYRA_LEARNING_INPUT_SCHEMA_VERSION,
        "operation": SUBMIT_OPERATION,
        "eligibility": {
            "eligible": True,
            "policyVersion": ELYRA_LEARNING_POLICY_VERSION,
            "evaluatedAt": PRODUCED_AT.isoformat(),
        },
        "consent": {
            "trainingConsentGranted": True,
            "consentVersion": "v1",
            "grantedAt": CONSENT_AT.isoformat(),
        },
        "provenance": {
            "sourceKind": "report_snapshot",
            "sourceSchemaVersion": "report_snapshot/v1",
            "analyticsVersion": "elyra-analytics/v1",
            "exportSchemaVersion": ELYRA_LEARNING_EXPORT_SCHEMA_VERSION,
            "producedAt": PRODUCED_AT.isoformat(),
        },
        "quality": {"passed": True, "checks": _quality_checks()},
        "fingerprint": canonical_fingerprint(payload),
        "payload": payload,
    }
    context.update(overrides)
    return context


def _revocation(fingerprint: str, **overrides) -> dict:
    context = {
        "contractVersion": ELYRA_LEARNING_CONTRACT_VERSION,
        "inputSchemaVersion": ELYRA_LEARNING_INPUT_SCHEMA_VERSION,
        "operation": REVOKE_OPERATION,
        "fingerprint": fingerprint,
        "reasonCode": "training_consent_revoked",
        "revokedAt": PRODUCED_AT.isoformat(),
    }
    context.update(overrides)
    return context


def _request(**overrides) -> dict:
    request = {
        "message": ELYRA_LEARNING_MESSAGE,
        "mode": "tecnico",
        "provider": "mock",
        "task_type": ELYRA_LEARNING_TASK_TYPE,
        "origin_system": "elyra",
        "allow_real_provider": False,
        "allow_mock_fallback": False,
        "correlation_id": "elyra-stage13-request-001",
        "idempotency_key": "elyra-stage13-idempotency-001",
        "context": _submission(),
    }
    request.update(overrides)
    return request


def _post(credential: str | None = ELYRA_CREDENTIAL, **overrides):
    headers = {AUTH_HEADER: credential} if credential else {}
    return client.post("/api/orchestrate", json=_request(**overrides), headers=headers)


def _candidate_id_for(payload: dict) -> str:
    return external_candidate_id(
        "elyra",
        TrainingSourceType.ELYRA_REPORT_SNAPSHOT,
        TrainingPurpose.EVALUATION_ONLY,
        canonical_fingerprint(payload),
    )


def _stored(payload: dict):
    return training_candidate_service._required_repository().get(
        "elyra", _candidate_id_for(payload)
    )


# --------------------------------------------------------------------------
# Caminho autorizado
# --------------------------------------------------------------------------


def test_authorized_submission_creates_a_proposed_candidate(elyra_registry):
    response = _post()
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["project_id"] == "elyra"
    assert body["task_allowed_for_project"] is True

    receipt = body["elyra_learning"]
    assert receipt is not None
    assert receipt["contractVersion"] == ELYRA_LEARNING_CONTRACT_VERSION
    assert receipt["outputSchemaVersion"] == ELYRA_LEARNING_OUTPUT_SCHEMA_VERSION
    assert receipt["operation"] == SUBMIT_OPERATION
    assert receipt["correlationId"] == "elyra-stage13-request-001"
    assert receipt["policyVersion"] == ELYRA_LEARNING_POLICY_VERSION
    assert receipt["duplicate"] is False
    assert receipt["lifecycle"] == CandidateLifecycle.PROPOSED.value


def test_submission_never_starts_training_or_touches_weights(elyra_registry):
    receipt = _post().json()["elyra_learning"]

    assert receipt["trainingStarted"] is False
    assert receipt["modelWeightsUpdated"] is False


def test_no_provider_participates_in_learning(elyra_registry):
    body = _post().json()

    assert body["provider_used"] == "none"
    assert body["model"] == "none"
    assert body["fallback_used"] is False
    # Nem a capability textual nem a multimodal sao preenchidas.
    assert body["elyra"] is None
    assert body["elyra_multimodal"] is None


def test_candidate_is_not_eligible_until_an_admin_authorizes_it(elyra_registry):
    _post()
    record = _stored(_payload())

    assert record is not None
    assert record.lifecycle is CandidateLifecycle.PROPOSED
    assert record.eligibility is EligibilityDecision.NOT_ELIGIBLE
    assert "TRAINING_AUTHORIZATION_REQUIRED" in record.reason_codes
    assert record.candidate is None
    assert record.authorization is None


def test_candidate_reuses_the_existing_store_and_source_type(elyra_registry):
    _post()
    record = _stored(_payload())

    assert record is not None
    assert record.source_type is TrainingSourceType.ELYRA_REPORT_SNAPSHOT
    assert record.training_purpose is TrainingPurpose.EVALUATION_ONLY
    # Consumer externo nao expoe id interno: a referencia e o fingerprint.
    assert record.source_id is None
    assert record.fingerprint == "sha256:" + canonical_fingerprint(_payload())


def test_receipt_never_returns_the_submitted_payload(elyra_registry):
    body = _post().json()
    blob = json.dumps(body["elyra_learning"], ensure_ascii=False)

    for leaked in ("daysWithMood", "sleepDurationMinutes", "mean", "cycleEnabled"):
        assert leaked not in blob


# --------------------------------------------------------------------------
# Caller, origem e task
# --------------------------------------------------------------------------


def test_missing_credential_is_denied(elyra_registry):
    response = _post(credential=None)
    body = response.json()

    assert response.status_code >= 400 or body.get("status") == "blocked"
    assert body.get("elyra_learning") is None


def test_unknown_credential_is_denied(elyra_registry):
    body = _post(credential="credencial-inexistente").json()

    assert body.get("elyra_learning") is None
    assert _stored(_payload()) is None


def test_technical_tool_role_is_denied(elyra_registry):
    body = _post(credential=ELYRA_TECHNICAL_CREDENTIAL).json()

    assert body["status"] == "blocked"
    assert body["elyra_learning"] is None
    assert _stored(_payload()) is None


def test_other_project_credential_is_denied(elyra_registry):
    body = _post(credential=STRUCTA_CREDENTIAL).json()

    assert body["status"] == "blocked"
    assert body["elyra_learning"] is None
    assert _stored(_payload()) is None


def test_wrong_origin_system_is_denied(elyra_registry):
    body = _post(origin_system="structa").json()

    assert body["status"] == "blocked"
    assert body["elyra_learning"] is None
    assert _stored(_payload()) is None


def test_learning_task_is_not_allowed_for_other_projects():
    from app.modules.project_context.service import project_context_resolver

    for project_id in ("pedrocore", "finguard", "finguard-local", "structa"):
        project = project_context_resolver.resolve(project_id)
        assert ELYRA_LEARNING_TASK_TYPE not in project.allowed_tasks


def test_wrong_canonical_message_is_denied(elyra_registry):
    body = _post(message="submeter_dados_para_treino").json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID
    assert _stored(_payload()) is None


def test_multimodal_payload_does_not_satisfy_learning_contract(elyra_registry):
    body = _post(context={"contractVersion": "elyra-multimodal/v1"}).json()

    assert body["status"] == "blocked"
    assert body["elyra_learning"] is None


# --------------------------------------------------------------------------
# Requisitos de governanca — cada ausencia e um DENY nominal
# --------------------------------------------------------------------------


def test_missing_training_consent_is_denied(elyra_registry):
    context = _submission()
    del context["consent"]
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_TRAINING_CONSENT_REQUIRED
    assert _stored(_payload()) is None


def test_training_consent_declared_false_is_denied(elyra_registry):
    context = _submission()
    context["consent"]["trainingConsentGranted"] = False
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_TRAINING_CONSENT_REQUIRED
    assert _stored(_payload()) is None


def test_ineligible_submission_is_denied(elyra_registry):
    context = _submission()
    context["eligibility"]["eligible"] = False
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_NOT_ELIGIBLE
    assert _stored(_payload()) is None


def test_missing_eligibility_is_denied(elyra_registry):
    context = _submission()
    del context["eligibility"]
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_NOT_ELIGIBLE


def test_missing_policy_version_is_denied(elyra_registry):
    context = _submission()
    del context["eligibility"]["policyVersion"]
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_NOT_ELIGIBLE


def test_missing_provenance_is_denied(elyra_registry):
    context = _submission()
    del context["provenance"]
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_PROVENANCE_REQUIRED
    assert _stored(_payload()) is None


def test_incomplete_provenance_is_denied(elyra_registry):
    context = _submission()
    del context["provenance"]["analyticsVersion"]
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_PROVENANCE_REQUIRED


def test_missing_quality_gate_is_denied(elyra_registry):
    context = _submission()
    del context["quality"]
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_QUALITY_GATE_FAILED
    assert _stored(_payload()) is None


def test_failed_quality_gate_is_denied(elyra_registry):
    context = _submission()
    context["quality"]["passed"] = False
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_QUALITY_GATE_FAILED


def test_partial_quality_checks_are_denied(elyra_registry):
    context = _submission()
    context["quality"]["checks"] = _quality_checks()[:3]
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_QUALITY_GATE_FAILED


def test_single_failed_check_is_denied(elyra_registry):
    context = _submission()
    context["quality"]["checks"][2]["passed"] = False
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_QUALITY_GATE_FAILED


def test_missing_fingerprint_is_denied(elyra_registry):
    context = _submission()
    del context["fingerprint"]
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID
    assert _stored(_payload()) is None


def test_fingerprint_that_does_not_match_the_payload_is_denied(elyra_registry):
    context = _submission()
    context["fingerprint"] = "0" * 64
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_FINGERPRINT_MISMATCH
    assert _stored(_payload()) is None


def test_tampered_payload_invalidates_the_fingerprint(elyra_registry):
    """Trocar o conteudo depois de assinar nao passa despercebido."""
    context = _submission()
    context["payload"]["mood"]["mean"] = 9.5
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_FINGERPRINT_MISMATCH


def test_wrong_schema_version_is_denied(elyra_registry):
    body = _post(context=_submission(inputSchemaVersion="elyra-learning-input/v2")).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID


def test_wrong_contract_version_is_denied(elyra_registry):
    body = _post(context=_submission(contractVersion="elyra-learning/v2")).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID


def test_consent_granted_after_the_data_was_produced_is_denied(elyra_registry):
    """Consentimento precisa existir ANTES de o dado ser exportado."""
    context = _submission()
    context["consent"]["grantedAt"] = (PRODUCED_AT + timedelta(days=1)).isoformat()
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert _stored(_payload()) is None


def test_unsupported_operation_is_denied_by_name(elyra_registry):
    body = _post(context=_submission(operation="train_model")).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_OPERATION_NOT_SUPPORTED


def test_fine_tune_operation_does_not_exist(elyra_registry):
    body = _post(context=_submission(operation="fine_tune")).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_OPERATION_NOT_SUPPORTED


def test_generic_dataset_write_does_not_exist(elyra_registry):
    body = _post(context=_submission(operation="dataset_write")).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_OPERATION_NOT_SUPPORTED


# --------------------------------------------------------------------------
# Conteudo bruto — estruturalmente impossivel
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        "journal",
        "journalEntries",
        "transcript",
        "rawTranscript",
        "audio",
        "video",
        "screenRecording",
        "mediaAssets",
        "storagePath",
        "signedUrl",
        "userId",
        "email",
        "professionalNote",
        "pedrocoreOutput",
        "rawPrompt",
    ],
)
def test_raw_or_identifying_field_is_structurally_rejected(elyra_registry, field):
    context = _submission()
    context["payload"][field] = "conteudo que nao pode atravessar"
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID
    assert _stored(_payload()) is None


def test_extra_field_at_the_submission_root_is_rejected(elyra_registry):
    context = _submission()
    context["rawReport"] = {"journal": "texto"}
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID


def test_the_payload_schema_has_no_text_field_at_all():
    """A ausencia de campo de texto e uma propriedade do TIPO, nao da politica."""
    from app.modules.elyra_learning.schemas import SanitizedLearningPayloadV1

    for name, field in SanitizedLearningPayloadV1.model_fields.items():
        assert field.annotation is not str, name


def test_aggregate_without_samples_cannot_carry_a_value(elyra_registry):
    """Ausencia de dado nao e zero."""
    payload = _payload(
        sleepDurationMinutes=_aggregate(450.0, None, "insufficient_data", 0),
        daysWithSleep=0,
    )
    body = _post(context=_submission(payload=payload)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID


def test_value_out_of_domain_is_denied(elyra_registry):
    payload = _payload(mood=_aggregate(42.0, 0.5, "up", 28))
    body = _post(context=_submission(payload=payload)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID


def test_samples_exceeding_days_with_data_is_denied(elyra_registry):
    payload = _payload(daysWithMood=10)
    body = _post(context=_submission(payload=payload)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID


# --------------------------------------------------------------------------
# Fingerprint, deduplicacao e idempotencia
# --------------------------------------------------------------------------


def test_same_governed_content_produces_the_same_fingerprint():
    first = canonical_fingerprint(_payload())
    reordered = dict(reversed(list(_payload().items())))

    assert canonical_fingerprint(reordered) == first


def test_semantic_change_produces_a_different_fingerprint():
    changed = _payload(mood=_aggregate(7.1, 0.5, "up", 28))

    assert canonical_fingerprint(changed) != canonical_fingerprint(_payload())


def test_duplicate_fingerprint_does_not_create_a_second_candidate(elyra_registry):
    first = _post().json()
    second = _post(
        correlation_id="elyra-stage13-request-002",
        idempotency_key="elyra-stage13-idempotency-002",
    ).json()

    assert first["elyra_learning"]["duplicate"] is False
    assert second["elyra_learning"]["duplicate"] is True
    assert (
        second["elyra_learning"]["candidateId"]
        == first["elyra_learning"]["candidateId"]
    )

    repository = training_candidate_service._required_repository()
    assert repository.count("elyra") == 1


def test_same_idempotency_key_and_request_replays(elyra_registry):
    first = _post().json()
    second = _post().json()

    assert second["idempotency_replayed"] is True
    assert second["elyra_learning"] == first["elyra_learning"]
    assert training_candidate_service._required_repository().count("elyra") == 1


def test_same_key_with_different_request_is_a_conflict(elyra_registry):
    assert _post().json()["status"] == "ok"

    payload = _payload(daysWithSleep=26, sleepDurationMinutes=_aggregate(440.0, 10.0, "up", 26))
    body = _post(context=_submission(payload=payload)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_IDEMPOTENCY_CONFLICT
    assert body["elyra_learning"] is None


def test_learning_idempotency_scope_does_not_collide_with_other_capabilities(
    elyra_registry,
):
    learning = _post().json()
    assert learning["status"] == "ok"

    textual = client.post(
        "/api/orchestrate",
        json={
            "message": "interpretar_relatorio_deterministico",
            "mode": "tecnico",
            "provider": "mock",
            "task_type": "wellbeing_report_interpretation",
            "origin_system": "elyra",
            "allow_real_provider": False,
            "allow_mock_fallback": True,
            "correlation_id": "elyra-stage13-request-001",
            "idempotency_key": "elyra-stage13-idempotency-001",
            "context": {"contractVersion": "elyra-textual/v1"},
        },
        headers={AUTH_HEADER: ELYRA_CREDENTIAL},
    ).json()

    assert textual["idempotency_replayed"] is False
    assert textual.get("elyra_learning") is None


# --------------------------------------------------------------------------
# Revogacao
# --------------------------------------------------------------------------


def _revoke(fingerprint: str, **overrides):
    request_overrides = {
        "context": _revocation(fingerprint, **overrides.pop("context_overrides", {})),
        "correlation_id": "elyra-stage13-revoke-001",
        "idempotency_key": "elyra-stage13-revoke-key-001",
    }
    request_overrides.update(overrides)
    return _post(**request_overrides)


def test_revocation_of_a_proposed_candidate_excludes_it(elyra_registry):
    _post()
    fingerprint = canonical_fingerprint(_payload())

    body = _revoke(fingerprint).json()
    receipt = body["elyra_learning"]

    assert body["status"] == "ok"
    assert receipt["operation"] == REVOKE_OPERATION
    assert receipt["lifecycle"] == CandidateLifecycle.EXCLUDED.value
    assert receipt["duplicate"] is False


def test_revoked_candidate_is_no_longer_eligible(elyra_registry):
    _post()
    _revoke(canonical_fingerprint(_payload()))
    record = _stored(_payload())

    assert record is not None
    assert record.lifecycle is CandidateLifecycle.EXCLUDED
    assert record.eligibility is EligibilityDecision.NOT_ELIGIBLE
    # O material submetido deixa de existir no store.
    assert record.proposal is None
    assert record.candidate is None
    assert record.excluded_reason == "training_consent_revoked"


def test_revocation_retry_is_idempotent(elyra_registry):
    _post()
    fingerprint = canonical_fingerprint(_payload())

    first = _revoke(fingerprint).json()
    elyra_idempotency_service.clear()
    second = _revoke(
        fingerprint,
        correlation_id="elyra-stage13-revoke-002",
        idempotency_key="elyra-stage13-revoke-key-002",
    ).json()

    assert first["status"] == "ok"
    assert second["status"] == "ok"
    assert second["elyra_learning"]["duplicate"] is True
    assert (
        second["elyra_learning"]["lifecycle"] == CandidateLifecycle.EXCLUDED.value
    )
    assert training_candidate_service._required_repository().count("elyra") == 1


def test_revocation_of_an_unknown_fingerprint_is_typed_and_fail_closed(elyra_registry):
    body = _revoke("f" * 64).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_CANDIDATE_NOT_FOUND
    assert body["elyra_learning"] is None


def test_revocation_with_malformed_fingerprint_is_denied(elyra_registry):
    body = _revoke("nao-e-um-fingerprint").json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID


def test_revocation_with_unknown_reason_code_is_denied(elyra_registry):
    _post()
    body = _revoke(
        canonical_fingerprint(_payload()),
        context_overrides={"reasonCode": "mudei_de_ideia"},
    ).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID


def test_revocation_from_another_project_is_denied(elyra_registry):
    _post()
    body = _revoke(
        canonical_fingerprint(_payload()), credential=STRUCTA_CREDENTIAL
    ).json()

    assert body["status"] == "blocked"
    assert _stored(_payload()).lifecycle is CandidateLifecycle.PROPOSED


def test_resubmitting_after_revocation_does_not_resurrect_the_candidate(elyra_registry):
    _post()
    _revoke(canonical_fingerprint(_payload()))
    elyra_idempotency_service.clear()

    _post(
        correlation_id="elyra-stage13-request-003",
        idempotency_key="elyra-stage13-idempotency-003",
    )
    record = _stored(_payload())

    assert record is not None
    assert record.lifecycle is CandidateLifecycle.EXCLUDED
    assert record.proposal is None


# --------------------------------------------------------------------------
# Regressao do Dataset Foundation
# --------------------------------------------------------------------------


def test_learning_capability_does_not_create_a_second_store(elyra_registry):
    _post()
    repository = training_candidate_service._required_repository()

    assert repository.count("elyra") == 1
    assert repository.get("elyra", _candidate_id_for(_payload())) is not None


def test_submission_does_not_authorize_any_candidate(elyra_registry):
    _post()
    repository = training_candidate_service._required_repository()

    assert repository.count("elyra", lifecycle=CandidateLifecycle.AUTHORIZED) == 0
    assert repository.count("elyra", lifecycle=CandidateLifecycle.CONSUMED) == 0

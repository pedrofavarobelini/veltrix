"""Contrato multimodal Elyra V1 (Stage 12): fail-closed, sintetico e sem rede.

Nenhum teste desta suite toca provider real, midia, Storage ou banco. O objetivo
e provar NEGATIVAMENTE que a fronteira recusa tudo o que nao foi autorizado, e
que a capability textual continua intacta ao lado dela.
"""

from __future__ import annotations

import copy
import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
)
from app.modules.contracts import codes
from app.modules.elyra_multimodal.schemas import (
    ELYRA_MULTIMODAL_CANONICAL_MESSAGE,
    ELYRA_MULTIMODAL_CONTRACT_VERSION,
    ELYRA_MULTIMODAL_DISCLAIMER,
    ELYRA_MULTIMODAL_INPUT_SCHEMA_VERSION,
    ELYRA_MULTIMODAL_OPERATION,
    ELYRA_MULTIMODAL_OUTPUT_SCHEMA_VERSION,
    ELYRA_MULTIMODAL_TASK_TYPE,
    ElyraMultimodalInputV1,
)
from app.modules.elyra_multimodal.service import elyra_multimodal_service
from app.modules.elyra_textual.idempotency import elyra_idempotency_service
from app.modules.provider_health.service import provider_health_service

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
ELYRA_CREDENTIAL = "elyra-multimodal-test-credential"
ELYRA_TECHNICAL_CREDENTIAL = "elyra-multimodal-technical-denied"
STRUCTA_CREDENTIAL = "structa-multimodal-denied"
FAKE_GEMINI_KEY = "elyra-offline-key-never-dispatched"


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch):
    elyra_idempotency_service.clear()
    provider_health_service.reset()
    monkeypatch.setenv("PEDROCORE_PROVIDER_ROUTING_MODE", "legacy")
    monkeypatch.delenv("PEDROCORE_REAL_FALLBACK_ENABLED", raising=False)
    yield
    provider_health_service.reset()
    elyra_idempotency_service.clear()


@pytest.fixture
def elyra_registry(monkeypatch):
    registry = [
        {
            "credential_id": "elyra-multimodal-v1",
            "api_key": ELYRA_CREDENTIAL,
            "project_id": "elyra",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["elyra"],
        },
        {
            "credential_id": "elyra-multimodal-technical",
            "api_key": ELYRA_TECHNICAL_CREDENTIAL,
            "project_id": "elyra",
            "role": "technical_tool",
            "environment": "development",
            "allowed_origins": ["elyra"],
        },
        {
            "credential_id": "structa-multimodal-denied",
            "api_key": STRUCTA_CREDENTIAL,
            "project_id": "structa",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["structa"],
        },
    ]
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, json.dumps(registry))
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_GEMINI_KEY)
    return registry


def _signal(
    name: str,
    unit: str,
    value: float | None,
    *,
    status: str = "available",
    baseline: float | None = None,
    samples: int = 12,
    delta: float | None = None,
) -> dict:
    return {
        "name": name,
        "value": value,
        "unit": unit,
        "personalBaselineMean": baseline,
        "personalBaselineSamples": samples,
        "deltaVsPersonalBaseline": delta,
        "status": status,
    }


def _session(**overrides) -> dict:
    session = {
        "signalsSchemaVersion": "multimodal_signals/v1",
        "featureExtractorVersion": "elyra-signals/v1",
        "sessionKind": "guided",
        "capturedResources": ["microphone", "camera"],
        "durationMs": 300_000,
        "transcript": {
            "language": "pt-BR",
            "text": "Hoje falei sobre a semana e sobre o que me cansou.",
            "wordCount": 11,
            "voicedDurationMs": 240_000,
            "truncated": False,
        },
        "signals": [
            _signal(
                "speech_rate", "words_per_minute", 132.0, baseline=120.0, delta=12.0
            ),
            _signal("pause_count", "count", 18.0, baseline=15.0, delta=3.0),
            _signal(
                "vocal_variation",
                "index",
                0.42,
                status="insufficient_baseline",
                baseline=None,
                samples=0,
            ),
            _signal(
                "movement_frequency", "index", 0.31, baseline=0.28, delta=0.03
            ),
        ],
    }
    session.update(overrides)
    return session


def _context(**overrides) -> dict:
    context = {
        "contractVersion": ELYRA_MULTIMODAL_CONTRACT_VERSION,
        "inputSchemaVersion": ELYRA_MULTIMODAL_INPUT_SCHEMA_VERSION,
        "operation": ELYRA_MULTIMODAL_OPERATION,
        "aiInferenceConsent": True,
        "multimodalAnalysisConsent": True,
        "transcriptAnalysisConsent": True,
        "session": _session(),
    }
    context.update(overrides)
    return context


def _payload(**overrides) -> dict:
    payload = {
        "message": ELYRA_MULTIMODAL_CANONICAL_MESSAGE,
        "mode": "tecnico",
        "provider": "mock",
        "task_type": ELYRA_MULTIMODAL_TASK_TYPE,
        "origin_system": "elyra",
        "allow_real_provider": False,
        "allow_mock_fallback": True,
        "correlation_id": "elyra-stage12-request-001",
        "idempotency_key": "elyra-stage12-idempotency-001",
        "context": _context(),
    }
    payload.update(overrides)
    return payload


def _post(credential: str | None = ELYRA_CREDENTIAL, **overrides):
    headers = {AUTH_HEADER: credential} if credential else {}
    return client.post("/api/orchestrate", json=_payload(**overrides), headers=headers)


# --------------------------------------------------------------------------
# Caminho autorizado
# --------------------------------------------------------------------------


def test_authorized_multimodal_request_returns_typed_projection(elyra_registry):
    response = _post()
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["project_id"] == "elyra"
    assert body["task_allowed_for_project"] is True
    assert body["provider_used"] == "mock"
    assert body["fallback_used"] is False

    projection = body["elyra_multimodal"]
    assert projection is not None
    assert projection["contractVersion"] == ELYRA_MULTIMODAL_CONTRACT_VERSION
    assert projection["outputSchemaVersion"] == ELYRA_MULTIMODAL_OUTPUT_SCHEMA_VERSION
    assert projection["correlationId"] == "elyra-stage12-request-001"
    assert projection["disclaimer"] == ELYRA_MULTIMODAL_DISCLAIMER
    assert projection["language"] == "pt-BR"
    assert projection["safety"] == {
        "diagnosticClaim": False,
        "prescription": False,
        "causalClaim": False,
        "facialEmotionAsFact": False,
        "fictitiousEmotionPercentage": False,
        "emotionInferredFromSignal": False,
        "rawMediaAccessed": False,
        "populationNormComparison": False,
    }
    # A capability textual nao e preenchida por uma request multimodal.
    assert body["elyra"] is None


def test_multimodal_projection_never_claims_emotion_or_population_norm(elyra_registry):
    """O conteudo interpretativo nao afirma emocao, diagnostico ou norma.

    O disclaimer legitimamente usa a palavra "diagnostico" para NEGA-LO; por
    isso a varredura cobre summary, observations e limitations, que sao o texto
    que a pessoa usuaria le como leitura da sessao.
    """
    projection = _post().json()["elyra_multimodal"]
    interpretive = " ".join(
        [projection["summary"], *projection["limitations"]]
        + [item["text"] for item in projection["observations"]]
    ).lower()

    for forbidden in (
        "diagnóstic",
        "depress",
        "transtorno",
        "ansiedade detectada",
        "emoção detectada",
        "tristeza",
        "%",
        "média da população",
        "norma populacional",
    ):
        assert forbidden not in interpretive, forbidden

    assert "média pessoal" in interpretive


def test_insufficient_baseline_signal_is_reported_without_comparison(elyra_registry):
    projection = _post().json()["elyra_multimodal"]
    texts = {item["evidencePath"]: item["text"] for item in projection["observations"]}

    assert "histórico pessoal suficiente" in texts["signals.vocal_variation"]


def test_not_captured_signal_is_not_treated_as_zero(elyra_registry):
    session = _session(
        capturedResources=["microphone"],
        signals=[
            _signal(
                "speech_rate", "words_per_minute", 132.0, baseline=120.0, delta=12.0
            ),
            _signal(
                "movement_frequency",
                "index",
                None,
                status="not_captured",
                baseline=None,
                samples=0,
            ),
        ],
    )
    projection = _post(context=_context(session=session)).json()["elyra_multimodal"]
    texts = {item["evidencePath"]: item["text"] for item in projection["observations"]}

    assert "não é valor zero" in texts["signals.movement_frequency"]


# --------------------------------------------------------------------------
# Caller, origem e capability
# --------------------------------------------------------------------------


def test_missing_credential_is_denied(elyra_registry):
    """Sem credencial a recusa acontece ANTES do boundary multimodal."""
    response = _post(credential=None)
    body = response.json()

    assert response.status_code >= 400 or body.get("status") == "blocked"
    assert body.get("elyra_multimodal") is None
    assert json.dumps(body, ensure_ascii=False).count("observable_signal") == 0


def test_technical_tool_role_is_denied(elyra_registry):
    body = _post(credential=ELYRA_TECHNICAL_CREDENTIAL).json()

    assert body["status"] == "blocked"
    assert body["elyra_multimodal"] is None


def test_other_project_credential_is_denied(elyra_registry):
    body = _post(credential=STRUCTA_CREDENTIAL).json()

    assert body["status"] == "blocked"
    assert body["elyra_multimodal"] is None


def test_wrong_origin_system_is_denied(elyra_registry):
    body = _post(origin_system="structa").json()

    assert body["status"] == "blocked"
    assert body["elyra_multimodal"] is None


def test_unauthorized_task_for_elyra_is_not_allowed(elyra_registry):
    body = _post(task_type="code_help").json()

    assert body["task_allowed_for_project"] is False
    assert body["elyra_multimodal"] is None


def test_canonical_message_is_required(elyra_registry):
    body = _post(message="me diga como estou").json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID
    assert body["elyra_multimodal"] is None


def test_textual_message_does_not_satisfy_multimodal_contract(elyra_registry):
    body = _post(message="interpretar_relatorio_deterministico").json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID


# --------------------------------------------------------------------------
# Consentimento
# --------------------------------------------------------------------------


def test_missing_ai_inference_consent_is_denied(elyra_registry):
    body = _post(context=_context(aiInferenceConsent=False)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_CONSENT_REQUIRED
    assert body["elyra_multimodal"] is None


def test_missing_multimodal_consent_is_denied(elyra_registry):
    body = _post(context=_context(multimodalAnalysisConsent=False)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_CONSENT_REQUIRED


def test_transcript_without_transcript_consent_is_rejected(elyra_registry):
    """Consentimento de IA nao substitui consentimento de transcricao."""
    body = _post(context=_context(transcriptAnalysisConsent=False)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID
    assert body["elyra_multimodal"] is None


def test_session_without_transcript_is_accepted_when_consent_absent(elyra_registry):
    session = _session(transcript=None)
    body = _post(
        context=_context(session=session, transcriptAnalysisConsent=False)
    ).json()

    assert body["status"] == "ok"
    paths = {item["evidencePath"] for item in body["elyra_multimodal"]["observations"]}
    assert "transcript" not in paths


# --------------------------------------------------------------------------
# Minimizacao e schema
# --------------------------------------------------------------------------


def test_raw_media_reference_is_structurally_rejected(elyra_registry):
    session = _session()
    session["storagePath"] = "elyra-private/user/session/camera.webm"
    body = _post(context=_context(session=session)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID


def test_user_identifier_is_structurally_rejected(elyra_registry):
    context = _context()
    context["userId"] = "5f1b6f6e-0000-4000-8000-000000000000"
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID


def test_emotion_signal_is_structurally_rejected(elyra_registry):
    """O vocabulario fechado impede que emocao entre como 'sinal'."""
    session = _session()
    session["signals"].append(
        _signal("sadness_score", "index", 0.8, baseline=0.5, delta=0.3)
    )
    body = _post(context=_context(session=session)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID


def test_signal_out_of_domain_is_rejected(elyra_registry):
    session = _session(
        signals=[
            _signal(
                "speech_rate", "words_per_minute", 9_000.0, baseline=120.0, delta=1.0
            )
        ]
    )
    body = _post(context=_context(session=session)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID


def test_audio_signal_without_microphone_capture_is_rejected(elyra_registry):
    session = _session(
        capturedResources=["camera"],
        transcript=None,
        signals=[
            _signal(
                "speech_rate", "words_per_minute", 132.0, baseline=120.0, delta=12.0
            )
        ],
    )
    body = _post(context=_context(session=session)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID


def test_movement_signal_without_camera_capture_is_rejected(elyra_registry):
    session = _session(
        capturedResources=["microphone"],
        signals=[_signal("movement_frequency", "index", 0.31, baseline=0.28, delta=0.03)],
    )
    body = _post(context=_context(session=session)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID


def test_available_signal_without_personal_baseline_is_rejected(elyra_registry):
    session = _session(
        capturedResources=["microphone"],
        transcript=None,
        signals=[
            _signal(
                "speech_rate",
                "words_per_minute",
                132.0,
                baseline=None,
                samples=0,
                delta=None,
            )
        ],
    )
    body = _post(context=_context(session=session)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID


def test_wrong_unit_for_signal_is_rejected(elyra_registry):
    session = _session(
        capturedResources=["microphone"],
        transcript=None,
        signals=[_signal("speech_rate", "index", 0.5, baseline=0.4, delta=0.1)],
    )
    body = _post(context=_context(session=session)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID


def test_wrong_contract_version_is_rejected(elyra_registry):
    body = _post(context=_context(contractVersion="elyra-multimodal/v2")).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID


def test_textual_context_does_not_satisfy_multimodal_contract(elyra_registry):
    context = {
        "contractVersion": "elyra-textual/v1",
        "inputSchemaVersion": "elyra-textual-input/v1",
        "operation": "interpret_deterministic_report",
        "aiInferenceConsent": True,
        "report": {},
    }
    body = _post(context=context).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID


# --------------------------------------------------------------------------
# Provider policy
# --------------------------------------------------------------------------


def test_mock_with_real_provider_flag_is_denied(elyra_registry):
    body = _post(provider="mock", allow_real_provider=True).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_PROVIDER_POLICY_DENIED


def test_auto_with_mock_fallback_is_denied(elyra_registry):
    """Sem fallback silencioso: provider real nao pode cair em mock."""
    body = _post(
        provider="auto", allow_real_provider=True, allow_mock_fallback=True
    ).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_PROVIDER_POLICY_DENIED


def test_explicit_third_party_provider_is_denied(elyra_registry):
    """O caller Elyra nunca escolhe provider: a recusa vem da identidade."""
    body = _post(provider="openai", allow_real_provider=True).json()

    assert body["status"] == "blocked"
    assert body["error_code"] in {
        codes.CALLER_PROVIDER_SELECTION_NOT_ALLOWED,
        codes.ELYRA_MULTIMODAL_PROVIDER_POLICY_DENIED,
    }
    assert body.get("elyra_multimodal") is None


def test_local_model_is_denied(elyra_registry):
    body = _post(allow_local_model=True).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID


# --------------------------------------------------------------------------
# Idempotencia e correlacao
# --------------------------------------------------------------------------


def test_same_key_and_payload_replays_without_new_dispatch(elyra_registry):
    first = _post().json()
    second = _post().json()

    assert first["status"] == "ok"
    assert second["status"] == "ok"
    assert second["idempotency_replayed"] is True
    assert second["elyra_multimodal"] == first["elyra_multimodal"]


def test_same_key_with_different_payload_is_a_conflict(elyra_registry):
    assert _post().json()["status"] == "ok"

    session = _session(durationMs=299_000)
    body = _post(context=_context(session=session)).json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_IDEMPOTENCY_CONFLICT
    assert body["elyra_multimodal"] is None


def test_multimodal_and_textual_idempotency_scopes_do_not_collide(elyra_registry):
    """Mesma chave em capabilities diferentes nao pode ser tratada como replay."""
    multimodal = _post().json()
    assert multimodal["status"] == "ok"

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
            "correlation_id": "elyra-stage12-request-001",
            "idempotency_key": "elyra-stage12-idempotency-001",
            "context": {"contractVersion": "elyra-textual/v1"},
        },
        headers={AUTH_HEADER: ELYRA_CREDENTIAL},
    ).json()

    # Recusado pelo proprio contrato textual, nunca por replay do multimodal.
    assert textual["idempotency_replayed"] is False
    assert textual["elyra_multimodal"] is None


def test_correlation_id_is_echoed_in_the_projection(elyra_registry):
    body = _post(correlation_id="elyra-stage12-correlacao-abc").json()

    assert body["correlation_id"] == "elyra-stage12-correlacao-abc"
    assert body["elyra_multimodal"]["correlationId"] == "elyra-stage12-correlacao-abc"


def test_malformed_correlation_id_is_rejected(elyra_registry):
    body = _post(correlation_id="!!").json()

    assert body["status"] == "blocked"
    assert body["error_code"] == codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID


# --------------------------------------------------------------------------
# Validacao de output (nivel de servico, sem rede)
# --------------------------------------------------------------------------


def _valid_output(correlation_id: str = "elyra-stage12-request-001") -> dict:
    request = ElyraMultimodalInputV1.model_validate(_context())
    output = elyra_multimodal_service.deterministic_mock(request, correlation_id)
    return json.loads(elyra_multimodal_service.serialize_output(output))


def _validate(raw: str, *, context: dict | None = None, correlation: str | None = None):
    request = ElyraMultimodalInputV1.model_validate(context or _context())
    return elyra_multimodal_service.validate_output(
        raw, request, correlation or "elyra-stage12-request-001"
    )


def test_deterministic_mock_round_trips_through_validation():
    assert _validate(json.dumps(_valid_output())).valid is True


def test_non_json_output_is_rejected():
    result = _validate("resposta em texto livre")

    assert result.valid is False
    assert result.error_code == codes.ELYRA_MULTIMODAL_OUTPUT_INVALID


def test_output_with_mismatched_correlation_is_rejected():
    result = _validate(json.dumps(_valid_output("outra-correlacao-999")))

    assert result.valid is False
    assert result.error_code == codes.ELYRA_MULTIMODAL_OUTPUT_INVALID


def test_output_missing_safety_declaration_is_rejected():
    payload = _valid_output()
    del payload["safety"]

    assert _validate(json.dumps(payload)).valid is False


def test_output_claiming_emotion_inference_is_rejected():
    payload = _valid_output()
    payload["safety"]["emotionInferredFromSignal"] = True

    assert _validate(json.dumps(payload)).valid is False


def test_output_claiming_raw_media_access_is_rejected():
    payload = _valid_output()
    payload["safety"]["rawMediaAccessed"] = True

    assert _validate(json.dumps(payload)).valid is False


def test_output_with_wrong_disclaimer_is_rejected():
    payload = _valid_output()
    payload["disclaimer"] = "Isto e apenas informativo."

    assert _validate(json.dumps(payload)).valid is False


def test_output_citing_a_signal_that_was_not_sent_is_rejected():
    session = _session(
        capturedResources=["microphone"],
        transcript=None,
        signals=[
            _signal(
                "speech_rate", "words_per_minute", 132.0, baseline=120.0, delta=12.0
            )
        ],
    )
    payload = _valid_output()
    payload["observations"] = [
        {
            "category": "observable_signal",
            "evidencePath": "signals.movement_frequency",
            "text": "Movimento acima da média pessoal.",
        }
    ]
    result = _validate(
        json.dumps(payload),
        context=_context(session=session, transcriptAnalysisConsent=False),
    )

    assert result.valid is False
    assert result.error_code == codes.ELYRA_MULTIMODAL_OUTPUT_INVALID


def test_output_citing_transcript_without_consent_is_rejected():
    session = _session(transcript=None)
    payload = _valid_output()
    payload["observations"] = [
        {
            "category": "transcript",
            "evidencePath": "transcript",
            "text": "A transcrição indicou cansaço.",
        }
    ]
    result = _validate(
        json.dumps(payload),
        context=_context(session=session, transcriptAnalysisConsent=False),
    )

    assert result.valid is False
    assert result.error_code == codes.ELYRA_MULTIMODAL_OUTPUT_INVALID


def test_output_with_extra_field_is_rejected():
    payload = _valid_output()
    payload["emotionScore"] = 0.87

    assert _validate(json.dumps(payload)).valid is False


def test_truncated_output_is_rejected():
    raw = json.dumps(_valid_output())

    assert _validate(raw[: len(raw) // 2]).valid is False


# --------------------------------------------------------------------------
# Regressao dos callers existentes
# --------------------------------------------------------------------------


def test_multimodal_capability_does_not_leak_into_other_projects():
    from app.modules.project_context.service import project_context_resolver

    for project_id in ("pedrocore", "finguard", "finguard-local", "structa"):
        project = project_context_resolver.resolve(project_id)
        assert ELYRA_MULTIMODAL_TASK_TYPE not in project.allowed_tasks


def test_multimodal_input_model_forbids_unknown_fields():
    context = _context()
    context["trainingEligibility"] = True

    with pytest.raises(Exception):
        ElyraMultimodalInputV1.model_validate(context)


def test_deterministic_mock_is_stable_for_the_same_input():
    request = ElyraMultimodalInputV1.model_validate(_context())
    first = elyra_multimodal_service.serialize_output(
        elyra_multimodal_service.deterministic_mock(request, "corr-estavel-001")
    )
    second = elyra_multimodal_service.serialize_output(
        elyra_multimodal_service.deterministic_mock(
            copy.deepcopy(request), "corr-estavel-001"
        )
    )

    assert first == second

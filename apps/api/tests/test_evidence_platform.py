"""Evidence Platform — ingestao universal (Era 4).

Estes testes cobrem o GATE 4 caso a caso. Como nos contratos, a maioria prova
que o caminho DESONESTO ou ACIDENTAL falha: segredo no payload, token, PII,
projeto trocado, producer trocado, timestamp impossivel, payload gigante,
referencia inconsistente e — o mais importante — Learning Source que NAO vira
Training Candidate.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.evidence_platform.repository import InMemoryEvidenceRepository
from app.modules.evidence_platform.schemas import (
    MAX_EVIDENCE_PAYLOAD_BYTES,
    EvidenceKind,
    EvidenceRecord,
    IngestionDecision,
)
from app.modules.evidence_platform.service import (
    EVIDENCE_IDEMPOTENCY_CONFLICT,
    EVIDENCE_PAYLOAD_TOO_LARGE,
    EVIDENCE_PRIVACY_REJECTED,
    evidence_ingestion_service,
)
from app.modules.project_context.manifests import PROJECT_MANIFESTS
from app.modules.report_memory.repository import ReportMemoryRepositoryConfigurationError
from app.modules.universal_contracts.versioning import (
    EXECUTION_OUTCOME_V1,
    INTEGRATION_ENVELOPE_V1,
    LEARNING_SOURCE_V1,
    QUALITY_EVIDENCE_V1,
)

NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)

# `pedrocore` declara `quality_evidence` e `execution_outcome`; `elyra` declara
# `learning_source`. Usar os manifests REAIS, e nao fixtures, faz estes testes
# falharem se o registro perder uma capability.
PEDROCORE = "pedrocore"
ELYRA = "elyra"


@pytest.fixture(autouse=True)
def isolated_registry():
    """Cada teste com seu proprio store; nada vaza entre casos nem para disco."""
    repository = InMemoryEvidenceRepository()
    evidence_ingestion_service.set_repository(repository)
    yield repository
    evidence_ingestion_service.set_repository(None)


def _caller(project_id: str = PEDROCORE, credential_id: str | None = None):
    return AuthenticatedCallerContext(
        credential_id=credential_id or f"{project_id}-ci",
        caller_role=CallerRole.TECHNICAL_TOOL,
        environment="test",
        identity_strength=IdentityStrength.REGISTERED,
        authenticated=True,
        project_id=project_id,
        # Credencial registrada precisa declarar origens permitidas — a
        # identidade e estrita por design, e o teste respeita isso.
        allowed_origins=(project_id,),
    )


def _quality(**overrides) -> dict:
    payload = {
        "contract_version": QUALITY_EVIDENCE_V1,
        "evidence_id": "ev-1",
        "outcome": "passed",
        "environment": "ci",
        "observed_at": NOW.isoformat(),
        "suites": [{"suite_id": "unit", "outcome": "passed", "total": 5, "passed": 5}],
    }
    payload.update(overrides)
    return payload


def _learning(**overrides) -> dict:
    payload = {
        "contract_version": LEARNING_SOURCE_V1,
        "source_id": "src-1",
        "provenance": {
            "source_kind": "execution_outcome",
            "source_schema_version": "run/v1",
            "producer_policy_version": "elyra-policy/v1",
            "produced_at": NOW.isoformat(),
            "content_signature": "sha256:" + "b" * 64,
        },
        "producer_asserted_outcome": "successful",
        "derived_features": {"score": 7},
    }
    payload.update(overrides)
    return payload


def _envelope(payload: dict, payload_type: str, project_id: str, **overrides) -> dict:
    envelope = {
        "envelope_version": INTEGRATION_ENVELOPE_V1,
        "event_id": "evt-1",
        "payload_type": payload_type,
        "project_id": project_id,
        "producer_id": f"{project_id}-ci",
        "submitted_at": NOW.isoformat(),
        "payload": payload,
    }
    envelope.update(overrides)
    return envelope


def _ingest(envelope: dict, caller=None):
    return evidence_ingestion_service.ingest(envelope, caller=caller or _caller())


# ---------------------------------------------------------------------------
# Caminho valido
# ---------------------------------------------------------------------------


def test_valid_quality_evidence_is_registered():
    result = _ingest(_envelope(_quality(), "quality_evidence", PEDROCORE))
    assert result.decision is IngestionDecision.ACCEPTED, result.reason
    assert result.fingerprint.startswith("sha256:")
    assert result.training_candidate_created is False
    assert result.automatic_collection_performed is False


def test_registered_evidence_is_retrievable_and_counted():
    _ingest(_envelope(_quality(), "quality_evidence", PEDROCORE))
    records = evidence_ingestion_service.list_evidence(PEDROCORE)
    assert len(records) == 1
    assert records[0].kind is EvidenceKind.QUALITY_EVIDENCE
    assert evidence_ingestion_service.count_evidence(PEDROCORE) == 1


def test_fingerprint_is_derived_by_the_server_not_accepted_from_producer():
    """Fingerprint enviado pelo produtor nao existe no contrato e nao e usado."""
    first = _ingest(_envelope(_quality(), "quality_evidence", PEDROCORE))
    assert "fingerprint" not in _quality()
    assert first.fingerprint == (
        _ingest(_envelope(_quality(), "quality_evidence", PEDROCORE)).fingerprint
    )


# ---------------------------------------------------------------------------
# Idempotencia e dedup
# ---------------------------------------------------------------------------


def test_identical_evidence_is_deduplicated_by_fingerprint():
    first = _ingest(_envelope(_quality(), "quality_evidence", PEDROCORE))
    second = _ingest(_envelope(_quality(), "quality_evidence", PEDROCORE))
    assert first.decision is IngestionDecision.ACCEPTED
    assert second.decision is IngestionDecision.DUPLICATE
    assert second.evidence_record_id == first.evidence_record_id
    assert evidence_ingestion_service.count_evidence(PEDROCORE) == 1


def test_retry_with_the_same_idempotency_key_is_a_duplicate_not_an_error():
    """Retry por timeout precisa ser distinguivel de falha."""
    envelope = _envelope(_quality(), "quality_evidence", PEDROCORE, idempotency_key="k1")
    first = _ingest(envelope)
    second = _ingest(envelope)
    assert first.decision is IngestionDecision.ACCEPTED
    assert second.decision is IngestionDecision.DUPLICATE
    assert second.error_code is None


def test_reused_idempotency_key_with_different_content_is_a_conflict():
    """Mesma chave, conteudo diferente nao e retry: e colisao.

    Aceitar sobrescreveria em silencio um fato ja gravado.
    """
    _ingest(_envelope(_quality(), "quality_evidence", PEDROCORE, idempotency_key="k1"))
    result = _ingest(
        _envelope(
            _quality(evidence_id="ev-2"), "quality_evidence", PEDROCORE,
            idempotency_key="k1",
        )
    )
    assert result.decision is IngestionDecision.REJECTED
    assert result.error_code == EVIDENCE_IDEMPOTENCY_CONFLICT


def test_different_evidence_is_not_deduplicated():
    _ingest(_envelope(_quality(), "quality_evidence", PEDROCORE))
    result = _ingest(
        _envelope(_quality(evidence_id="ev-2"), "quality_evidence", PEDROCORE)
    )
    assert result.decision is IngestionDecision.ACCEPTED
    assert evidence_ingestion_service.count_evidence(PEDROCORE) == 2


# ---------------------------------------------------------------------------
# Binding de identidade
# ---------------------------------------------------------------------------


def test_project_mismatch_is_rejected():
    envelope = _envelope(_quality(), "quality_evidence", "outro-projeto")
    result = _ingest(envelope, _caller(PEDROCORE))
    assert result.decision is IngestionDecision.REJECTED
    assert result.error_code == "CONTRACT_PROJECT_BINDING_MISMATCH"


def test_producer_mismatch_is_rejected():
    envelope = _envelope(
        _quality(), "quality_evidence", PEDROCORE, producer_id="outro-ci"
    )
    result = _ingest(envelope, _caller(PEDROCORE))
    assert result.decision is IngestionDecision.REJECTED
    assert result.error_code == "CONTRACT_PRODUCER_BINDING_MISMATCH"


def test_capability_not_declared_is_rejected():
    """`structa` nao declara `quality_evidence` — e o manifesto real que decide."""
    assert not PROJECT_MANIFESTS["structa"].declares(
        __import__(
            "app.modules.universal_contracts.capability_manifest",
            fromlist=["ProjectCapability"],
        ).ProjectCapability.QUALITY_EVIDENCE
    )
    envelope = _envelope(_quality(), "quality_evidence", "structa")
    result = _ingest(envelope, _caller("structa"))
    assert result.decision is IngestionDecision.REJECTED
    assert result.error_code == "CONTRACT_CAPABILITY_NOT_DECLARED"


def test_unregistered_project_has_no_manifest_and_is_rejected():
    envelope = _envelope(_quality(), "quality_evidence", "projeto-fantasma")
    result = _ingest(envelope, _caller("projeto-fantasma"))
    assert result.decision is IngestionDecision.REJECTED
    assert result.error_code == "CONTRACT_MANIFEST_MISSING"


# ---------------------------------------------------------------------------
# Contrato e versao
# ---------------------------------------------------------------------------


def test_unknown_contract_version_is_rejected():
    envelope = _envelope(
        _quality(), "quality_evidence", PEDROCORE,
        envelope_version="pedrocore-integration/v9",
    )
    result = _ingest(envelope)
    assert result.decision is IngestionDecision.REJECTED
    assert result.error_code == "CONTRACT_VERSION_UNKNOWN"


def test_invalid_timestamp_is_rejected():
    """Sem timezone o instante e ambiguo, e correlacao temporal vira ficcao."""
    envelope = _envelope(
        _quality(observed_at="2026-08-29T12:00:00"), "quality_evidence", PEDROCORE
    )
    result = _ingest(envelope)
    assert result.decision is IngestionDecision.REJECTED
    assert result.error_code == "CONTRACT_PAYLOAD_INVALID"


def test_execution_outcome_with_impossible_timestamps_is_rejected():
    payload = {
        "contract_version": EXECUTION_OUTCOME_V1,
        "outcome_id": "run-1",
        "operation": "deploy",
        "result": "succeeded",
        "started_at": NOW.isoformat(),
        "finished_at": (NOW - timedelta(minutes=5)).isoformat(),
    }
    result = _ingest(_envelope(payload, "execution_outcome", PEDROCORE))
    assert result.decision is IngestionDecision.REJECTED
    assert result.error_code == "CONTRACT_PAYLOAD_INVALID"


def test_inconsistent_evidence_reference_is_rejected():
    """Referencia com assinatura fora do formato nao e rastreavel."""
    payload = _quality(
        references=[
            {
                "reference_id": "r1",
                "kind": "report",
                "locator": "opaque-1",
                "content_signature": "nao-e-sha256",
            }
        ]
    )
    result = _ingest(_envelope(payload, "quality_evidence", PEDROCORE))
    assert result.decision is IngestionDecision.REJECTED
    assert result.error_code == "CONTRACT_PAYLOAD_INVALID"


def test_oversized_payload_is_rejected_before_parsing():
    payload = _quality(summary="x" * (MAX_EVIDENCE_PAYLOAD_BYTES + 1000))
    result = _ingest(_envelope(payload, "quality_evidence", PEDROCORE))
    assert result.decision is IngestionDecision.REJECTED
    assert result.error_code == EVIDENCE_PAYLOAD_TOO_LARGE


# ---------------------------------------------------------------------------
# Privacidade — segredo, token, PII
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "summary, expected_code",
    [
        ("api_key=AKIAIOSFODNN7EXAMPLE", "SECRET_ASSIGNMENT_DETECTED"),
        ("ghp_abcdefghijklmnopqrstuvwxyz012345", "PROVIDER_TOKEN_DETECTED"),
        ("contato: pessoa@exemplo.com", "EMAIL_PII_DETECTED"),
        ("CPF 123.456.789-01", "CPF_PII_DETECTED"),
        ("-----BEGIN RSA PRIVATE KEY-----", "PRIVATE_KEY_DETECTED"),
        ("postgresql://user:senha@host/db", "CREDENTIAL_URL_DETECTED"),
        ("veja C:\\Users\\Pedro\\segredo.txt", "PERSONAL_PATH_DETECTED"),
    ],
)
def test_sensitive_content_is_rejected_before_persistence(summary, expected_code):
    """Um segredo gravado ja vazou, mesmo que apagado em seguida."""
    result = _ingest(_envelope(_quality(summary=summary), "quality_evidence", PEDROCORE))
    assert result.decision is IngestionDecision.REJECTED
    assert result.error_code == EVIDENCE_PRIVACY_REJECTED
    assert expected_code in {item.code for item in result.privacy_findings}
    assert evidence_ingestion_service.count_evidence(PEDROCORE) == 0


def test_privacy_findings_never_expose_the_detected_value():
    secreto = "api_key=SUPERSECRETO12345"
    result = _ingest(_envelope(_quality(summary=secreto), "quality_evidence", PEDROCORE))
    rendered = result.model_dump_json()
    assert "SUPERSECRETO12345" not in rendered
    assert result.privacy_findings and result.privacy_findings[0].field_path


# ---------------------------------------------------------------------------
# Learning Source — sem promocao automatica
# ---------------------------------------------------------------------------


def test_learning_source_is_registered_as_operational_source_only():
    """O invariante central da Era 4.

    Uma fonte de aprendizado recebida vira registro operacional. Nenhum
    Training Candidate e criado, e o Candidate Store nem e tocado.
    """
    from app.modules.training_data.acquisition import training_candidate_service

    result = _ingest(
        _envelope(_learning(), "learning_source", ELYRA), _caller(ELYRA)
    )
    assert result.decision is IngestionDecision.ACCEPTED, result.reason
    assert result.training_candidate_created is False
    assert result.automatic_collection_performed is False

    records = evidence_ingestion_service.list_evidence(ELYRA)
    assert len(records) == 1
    assert records[0].kind is EvidenceKind.LEARNING_SOURCE
    assert records[0].promoted_to_training_candidate is False

    # O Candidate Store continua desabilitado: ingerir evidencia nao o acorda.
    with pytest.raises(ReportMemoryRepositoryConfigurationError):
        training_candidate_service.readiness(project_id=ELYRA)


def test_evidence_record_has_no_candidate_governance_fields():
    fields = set(EvidenceRecord.model_fields)
    forbidden = {
        "eligibility", "authorized", "training_purpose", "candidate_id",
        "lifecycle", "readiness",
    }
    assert not (fields & forbidden)


def test_learning_source_attempting_authority_escalation_is_rejected():
    payload = _learning(eligibility="eligible")
    result = _ingest(_envelope(payload, "learning_source", ELYRA), _caller(ELYRA))
    assert result.decision is IngestionDecision.REJECTED
    assert result.error_code == "CONTRACT_AUTHORITY_VIOLATION"


def test_learning_source_cannot_enable_automatic_collection():
    payload = _learning(automatic_collection=True)
    result = _ingest(_envelope(payload, "learning_source", ELYRA), _caller(ELYRA))
    assert result.decision is IngestionDecision.REJECTED
    assert result.error_code == "CONTRACT_AUTHORITY_VIOLATION"


# ---------------------------------------------------------------------------
# Fail-closed do registry
# ---------------------------------------------------------------------------


def test_registry_disabled_fails_closed_without_memory_fallback():
    """Store efemero lido como real faria a auditoria reportar o que nao houve."""
    evidence_ingestion_service.set_repository(None)
    with pytest.raises(ReportMemoryRepositoryConfigurationError):
        evidence_ingestion_service.ingest(
            _envelope(_quality(), "quality_evidence", PEDROCORE), caller=_caller()
        )


def test_project_isolation_between_consumers():
    _ingest(_envelope(_quality(), "quality_evidence", PEDROCORE))
    _ingest(_envelope(_learning(), "learning_source", ELYRA), _caller(ELYRA))
    assert evidence_ingestion_service.count_evidence(PEDROCORE) == 1
    assert evidence_ingestion_service.count_evidence(ELYRA) == 1
    assert evidence_ingestion_service.list_evidence(PEDROCORE)[0].project_id == PEDROCORE

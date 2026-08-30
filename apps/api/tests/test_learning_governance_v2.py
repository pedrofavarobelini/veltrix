"""Learning Governance V2 — promocao governada de evidencia (Era 5).

A Era 4 provou que evidencia registrada NAO vira candidato sozinha. Esta suite
prova o outro lado: quando um administrador seleciona explicitamente uma
evidencia, ela atravessa a governanca inteira — e continua sem ser elegivel ate
que alguem autorize.

O lifecycle oficial e o que ja existia, sem migracao de estado:

    PROPOSED · AUTHORIZED · REVIEW_REQUIRED · EXCLUDED · REVOKED · CONSUMED
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.evidence_platform.schemas import EvidenceKind, EvidenceRecord
from app.modules.evidence_platform.service import evidence_ingestion_service
from app.modules.training_data.acquisition import (
    TrainingCandidateTransitionError,
    training_candidate_service,
)
from app.modules.training_data.adapters import (
    TrainingSourceSelectionError,
    training_source_adapters,
)
from app.modules.training_data.policy import training_eligibility_policy
from app.modules.training_data.schemas import (
    CandidateLifecycle,
    ContentClassification,
    EligibilityDecision,
    TrainingAuthorizationRequest,
    TrainingCandidateStatusRequest,
    TrainingPurpose,
    TrainingSourceSelection,
    TrainingSourceType,
)
from app.modules.training_data.service import (
    EXTERNALLY_SUBMITTED_SOURCE_TYPES,
    INTERNAL_ADAPTER_SOURCE_TYPES,
    dataset_foundation_service,
)

NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "alpha"
ADMIN = "alpha-admin"


@pytest.fixture(autouse=True)
def isolated_candidate_store(monkeypatch):
    """Store em memoria, limpo antes e depois — nada vaza entre casos.

    Usa o mesmo mecanismo das suites existentes (`persistence_mode` + `reset`)
    em vez de injetar um repositorio por dentro: um segundo jeito de configurar
    persistencia no mesmo processo e exatamente o que a Era 4 evitou.
    """
    monkeypatch.setenv("PEDROCORE_TRAINING_DATA_ADMIN_IDS", ADMIN)
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "memory")
    training_candidate_service.reset()
    yield
    training_candidate_service.reset()


def _admin_caller() -> AuthenticatedCallerContext:
    return AuthenticatedCallerContext(
        credential_id=ADMIN,
        caller_role=CallerRole.TECHNICAL_TOOL,
        environment="test",
        identity_strength=IdentityStrength.REGISTERED,
        authenticated=True,
        project_id=PROJECT,
        allowed_origins=(PROJECT,),
    )


def _evidence(kind: EvidenceKind = EvidenceKind.QUALITY_EVIDENCE, **overrides):
    payload = {
        EvidenceKind.QUALITY_EVIDENCE: {
            "outcome": "passed",
            "environment": "ci",
            "suites": [{"suite_id": "unit", "outcome": "passed", "total": 6, "passed": 6}],
        },
        EvidenceKind.EXECUTION_OUTCOME: {
            "operation": "deploy",
            "result": "succeeded",
            "final_state": "stable",
            "diagnostics": [],
        },
        EvidenceKind.LEARNING_SOURCE: {
            "producer_asserted_outcome": "successful",
            "derived_features": {"score": 3},
            "provenance": {"source_kind": "execution_outcome"},
        },
    }[kind]
    record = EvidenceRecord(
        evidence_record_id="evidence-gov-1",
        project_id=PROJECT,
        producer_id="alpha-technical-tool",
        kind=kind,
        event_id="evt-gov-1",
        correlation_id="corr-gov-1",
        contract_version=f"pedrocore-{kind.value.replace('_', '-')}/v1",
        fingerprint="sha256:" + "d" * 64,
        submitted_at=NOW,
        received_at=NOW,
        payload=payload,
    )
    return record.model_copy(update=overrides)


def _bind_evidence(monkeypatch, record: EvidenceRecord | None):
    monkeypatch.setattr(
        evidence_ingestion_service,
        "get_evidence",
        lambda _project, source_id: (
            record
            if record is not None and source_id == record.evidence_record_id
            else None
        ),
    )


def _select(purpose=TrainingPurpose.GENERATIVE_SFT, source_id="evidence-gov-1"):
    return training_candidate_service.select(
        TrainingSourceSelection(
            producer="ignored-the-caller-decides",
            project_id=PROJECT,
            source_type=TrainingSourceType.EVIDENCE_RECORD,
            source_id=source_id,
            training_purpose=purpose,
        ),
        _admin_caller(),
    )


# ---------------------------------------------------------------------------
# Selecao governada
# ---------------------------------------------------------------------------


def test_selected_evidence_is_proposed_but_never_eligible(monkeypatch):
    """O coracao da governanca: selecionar nao autoriza.

    Mesmo com fonte real, proveniencia verificada e privacidade limpa, o
    candidato nasce PROPOSED e NOT_ELIGIBLE, aguardando autorizacao explicita.
    """
    _bind_evidence(monkeypatch, _evidence())
    record, duplicated = _select()
    assert not duplicated
    assert record.lifecycle is CandidateLifecycle.PROPOSED
    assert record.eligibility is EligibilityDecision.NOT_ELIGIBLE
    assert "TRAINING_AUTHORIZATION_REQUIRED" in record.reason_codes


def test_producer_comes_from_the_credential_not_from_the_request(monkeypatch):
    """O campo `producer` do payload e ignorado; vale a credencial autenticada."""
    _bind_evidence(monkeypatch, _evidence())
    record, _ = _select()
    assert record.proposal is not None
    assert record.proposal.producer == ADMIN


def test_selection_of_missing_evidence_is_rejected(monkeypatch):
    _bind_evidence(monkeypatch, None)
    with pytest.raises(TrainingSourceSelectionError) as error:
        _select()
    assert error.value.code == "OPERATIONAL_SOURCE_NOT_FOUND"


def test_selection_is_idempotent_and_does_not_duplicate(monkeypatch):
    _bind_evidence(monkeypatch, _evidence())
    first, first_dup = _select()
    second, second_dup = _select()
    assert not first_dup and second_dup
    assert first.candidate_id == second.candidate_id


def test_provenance_points_back_to_the_evidence_record(monkeypatch):
    """Sem rastro ate a evidencia, o candidato nao seria auditavel."""
    _bind_evidence(monkeypatch, _evidence())
    record, _ = _select()
    reference = record.proposal.evidence_refs[0]
    assert reference.source_type is TrainingSourceType.EVIDENCE_RECORD
    assert reference.source_id == "evidence-gov-1"
    assert reference.content_signature == "sha256:" + "d" * 64
    assert reference.verified is True


def test_candidate_carries_only_derived_features(monkeypatch):
    """Copiar o payload bruto faria a evidencia virar atalho para dado nao minimizado."""
    _bind_evidence(monkeypatch, _evidence())
    record, _ = _select()
    features = record.proposal.input_features
    assert set(features) == {
        "evidence_kind",
        "contract_version",
        "suite_count",
        "total_cases",
        "failed_cases",
        "environment",
    }
    assert record.proposal.derived_content_only is True


# ---------------------------------------------------------------------------
# Purpose por tipo de evidencia
# ---------------------------------------------------------------------------


def test_learning_source_evidence_allows_only_evaluation_only(monkeypatch):
    """A origem mais sensivel nao treina pesos — teto estreito, por tabela."""
    _bind_evidence(monkeypatch, _evidence(EvidenceKind.LEARNING_SOURCE))
    with pytest.raises(TrainingSourceSelectionError) as error:
        _select(TrainingPurpose.GENERATIVE_SFT)
    assert error.value.code == "EVIDENCE_PURPOSE_NOT_ALLOWED_FOR_KIND"

    record, _ = _select(TrainingPurpose.EVALUATION_ONLY)
    assert record.lifecycle is CandidateLifecycle.PROPOSED


def test_execution_outcome_evidence_cannot_be_used_for_generative_training(monkeypatch):
    _bind_evidence(monkeypatch, _evidence(EvidenceKind.EXECUTION_OUTCOME))
    with pytest.raises(TrainingSourceSelectionError):
        _select(TrainingPurpose.GENERATIVE_SFT)
    record, _ = _select(TrainingPurpose.RISK)
    assert record.proposal.training_purpose is TrainingPurpose.RISK


def test_policy_rejects_purpose_outside_the_source_ceiling(monkeypatch):
    """A policy e a autoridade final, mesmo que o adapter deixasse passar."""
    _bind_evidence(monkeypatch, _evidence())
    record, _ = _select()
    smuggled = record.proposal.model_copy(
        update={"training_purpose": TrainingPurpose.PREFERENCE}
    )
    decision = training_eligibility_policy.pre_screen(smuggled)
    assert decision.decision is EligibilityDecision.NOT_ELIGIBLE
    assert "SOURCE_PURPOSE_MISMATCH" in decision.reason_codes


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_official_lifecycle_has_exactly_the_six_declared_states():
    assert {item.value for item in CandidateLifecycle} == {
        "proposed",
        "authorized",
        "review_required",
        "excluded",
        "revoked",
        "consumed",
    }


def test_authorize_then_revoke_closes_the_candidate_for_good(monkeypatch):
    """Ciclo completo, com a governanca recusando o atalho em cada ponta.

    Um candidato PROPOSED nao e revogavel — so o e depois de autorizado. E,
    uma vez revogado, nao volta: ressuscita-lo apagaria a decisao de quem o
    revogou, que e a unica coisa que a revogacao existe para preservar.
    """
    _bind_evidence(monkeypatch, _evidence())
    record, _ = _select(TrainingPurpose.EVALUATION_ONLY)

    # PROPOSED ainda nao e revogavel.
    with pytest.raises(TrainingCandidateTransitionError):
        training_candidate_service.revoke(
            record.candidate_id,
            TrainingCandidateStatusRequest(project_id=PROJECT, reason_code="CEDO_DEMAIS"),
            _admin_caller(),
        )

    # O escopo autorizado precisa nomear EXATAMENTE o `task_type` do candidato.
    # Uma autorizacao generica ("avaliacao-interna") seria uma procuracao aberta:
    # valeria para qualquer coisa que o candidato viesse a ser.
    authorized = training_candidate_service.authorize(
        record.candidate_id,
        TrainingAuthorizationRequest(
            project_id=PROJECT,
            authorized_scope="evidence_quality_evidence",
            authorization_source="gate-era5",
            basis="evaluation_only",
            content_classification=ContentClassification.INTERNAL,
        ),
        _admin_caller(),
    )
    assert authorized.lifecycle is CandidateLifecycle.AUTHORIZED

    revoked = training_candidate_service.revoke(
        record.candidate_id,
        TrainingCandidateStatusRequest(project_id=PROJECT, reason_code="REVOGACAO_MANUAL"),
        _admin_caller(),
    )
    assert revoked.lifecycle is CandidateLifecycle.REVOKED
    assert revoked.eligibility is EligibilityDecision.NOT_ELIGIBLE

    # Revogado nao volta a ser autorizavel nem excluivel.
    for action in ("authorize", "exclude"):
        with pytest.raises(TrainingCandidateTransitionError):
            if action == "authorize":
                training_candidate_service.authorize(
                    record.candidate_id,
                    TrainingAuthorizationRequest(
                        project_id=PROJECT,
                        authorized_scope="evidence_quality_evidence",
                        authorization_source="gate-era5",
                        basis="evaluation_only",
                        content_classification=ContentClassification.INTERNAL,
                    ),
                    _admin_caller(),
                )
            else:
                training_candidate_service.exclude(
                    record.candidate_id,
                    TrainingCandidateStatusRequest(
                        project_id=PROJECT, reason_code="TARDE_DEMAIS"
                    ),
                    _admin_caller(),
                )


def test_authorization_basis_must_match_the_training_purpose(monkeypatch):
    """`evaluation_only` e proposito e base ao mesmo tempo; misturar e recusado."""
    _bind_evidence(monkeypatch, _evidence())
    record, _ = _select(TrainingPurpose.EVALUATION_ONLY)
    with pytest.raises(TrainingCandidateTransitionError) as error:
        training_candidate_service.authorize(
            record.candidate_id,
            TrainingAuthorizationRequest(
                project_id=PROJECT,
                authorized_scope="evidence_quality_evidence",
                authorization_source="gate-era5",
                basis="explicit_human",
                content_classification=ContentClassification.INTERNAL,
            ),
            _admin_caller(),
        )
    assert "MISMATCH" in str(error.value)


def test_admin_capability_is_required_for_selection(monkeypatch):
    """Sem capability administrativa, nada e selecionado."""
    _bind_evidence(monkeypatch, _evidence())
    stranger = _admin_caller().model_copy(update={"credential_id": "quem-sou-eu"})
    assert not training_candidate_service.admin_authorized(stranger)


# ---------------------------------------------------------------------------
# Invariantes preservados
# ---------------------------------------------------------------------------


def test_evidence_record_is_an_internal_adapter_source():
    """O registro e DO PedroCore — nao exige alcancar base de consumidor."""
    assert TrainingSourceType.EVIDENCE_RECORD in INTERNAL_ADAPTER_SOURCE_TYPES
    assert TrainingSourceType.EVIDENCE_RECORD not in EXTERNALLY_SUBMITTED_SOURCE_TYPES


def test_evidence_source_is_declared_in_the_dataset_foundation():
    definitions = {item.source_type: item for item in dataset_foundation_service.source_map()}
    definition = definitions[TrainingSourceType.EVIDENCE_RECORD]
    assert definition.module == "evidence_platform"
    assert definition.automatic_collection is False


def test_automatic_collection_remains_false_for_every_source():
    assert all(
        item.automatic_collection is False
        for item in dataset_foundation_service.source_map()
    )
    assert training_source_adapters.automatic_collection is False


def test_consumer_cannot_declare_the_final_governance_outcome(monkeypatch):
    """O resultado final e derivado pela policy, nunca copiado da proposta."""
    _bind_evidence(monkeypatch, _evidence())
    record, _ = _select()
    assert not hasattr(record.proposal, "eligibility")
    assert not hasattr(record.proposal, "data_use")
    assert record.eligibility is EligibilityDecision.NOT_ELIGIBLE

"""Risk Engine V2 — Stages R4 e R5.

R4 resolve P5: o Risk Engine nasceu antes dos Universal Contracts e recebia
submissao por um caminho que nao passava pela fronteira de autoridade.

R5 resolve P2: a simulacao emitia uma lista fixa de cenarios, relevantes ou
nao. Cenario irrelevante emitido para completar lista treina quem le a ignorar
a lista inteira.

O foco, como no resto do motor, e o caminho desonesto: consumidor tentando
declarar o proprio veredito.
"""

from __future__ import annotations

import pytest

from app.modules.retrieval.schemas import RetrievalResponse
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_engine.pre_execution_service import pre_execution_risk_service
from app.modules.risk_engine.schemas import RiskRequest, RiskSeverity
from app.modules.risk_engine.universal_contract import (
    RISK_CONTRACT_AUTHORITY_VIOLATION,
    RISK_CONTRACT_CAPABILITY_NOT_DECLARED,
    RISK_CONTRACT_MANIFEST_MISSING,
    RISK_CONTRACT_PAYLOAD_INVALID,
    RISK_CONTRACT_VERSION_UNKNOWN,
    RISK_REQUEST_CONTRACT_V1,
    RiskRequestContractV1,
    validate_risk_contract,
)

PROJECT = "pedrocore"
PRODUCER = "pedrocore-ci"


@pytest.fixture(autouse=True)
def quiet_retrieval(monkeypatch):
    monkeypatch.setattr(
        retrieval_service,
        "retrieve",
        lambda query, **_: RetrievalResponse(
            query_id=query.query_id, project_id=query.project_id
        ),
    )
    yield


def _contract(**overrides) -> dict:
    payload = {
        "contract_version": RISK_REQUEST_CONTRACT_V1,
        "request_id": "risk-contract-001",
        "environment": "development",
        "agent_id": "codex-local",
        "request_text": "Edit the billing module within the approved scope.",
        "permissions": ["write:billing"],
        "requested_operation": {
            "kind": "WRITE",
            "targets": ["module:billing"],
            "expected_changes": ["bounded edit"],
        },
        "context": {"allowed_scope": ["module:billing"], "required_tests": ["billing"]},
    }
    payload.update(overrides)
    return payload


def _validate(payload, project_id=PROJECT, producer=PRODUCER):
    return validate_risk_contract(
        payload,
        authenticated_project_id=project_id,
        authenticated_producer_id=producer,
    )


# ---------------------------------------------------------------------------
# R4 — contrato universal de risco
# ---------------------------------------------------------------------------


def test_a_valid_risk_contract_is_accepted():
    result = _validate(_contract())
    assert result.accepted, result.reason
    assert result.contract is not None
    assert result.gate_decided is False


def test_the_consumer_cannot_declare_the_gate():
    """O ataque que o contrato existe para impedir.

    Aceitar `gate` do payload transformaria o motor de risco em carimbo.
    """
    result = _validate(_contract(gate="PASS"))
    assert not result.accepted
    assert result.error_code == RISK_CONTRACT_AUTHORITY_VIOLATION


@pytest.mark.parametrize(
    "field", ["safe", "approved", "risk_level", "risk_severity", "override", "bypass"]
)
def test_no_verdict_field_is_accepted(field):
    result = _validate(_contract(**{field: True}))
    assert not result.accepted
    assert result.error_code == RISK_CONTRACT_AUTHORITY_VIOLATION


def test_a_verdict_hidden_deep_in_the_payload_is_still_refused():
    """Esconder o campo fundo nao pode ser mais eficaz do que envia-lo no topo."""
    result = _validate(_contract(context={"allowed_scope": ["m"], "gate": "PASS"}))
    assert not result.accepted
    assert result.error_code == RISK_CONTRACT_AUTHORITY_VIOLATION


def test_the_contract_has_nowhere_to_put_a_verdict():
    """A protecao e a ausencia de campo, nao so a varredura."""
    forbidden = {"gate", "severity", "risk_level", "safe", "approved", "override"}
    assert not (set(RiskRequestContractV1.model_fields) & forbidden)


def test_an_unknown_version_is_refused():
    result = _validate(_contract(contract_version="pedrocore-risk-request/v9"))
    assert not result.accepted
    assert result.error_code == RISK_CONTRACT_VERSION_UNKNOWN


def test_a_malformed_payload_is_refused_without_echoing_the_value():
    secret = "TOKEN-QUE-NAO-PODE-VAZAR-987654"
    result = _validate(_contract(request_id={"nested": secret}))
    assert not result.accepted
    assert result.error_code == RISK_CONTRACT_PAYLOAD_INVALID
    assert secret not in (result.reason or "")


def test_a_non_object_payload_is_refused():
    assert _validate("nao sou um contrato").error_code == RISK_CONTRACT_PAYLOAD_INVALID


def test_an_unknown_project_has_no_manifest():
    result = _validate(_contract(), project_id="projeto-fantasma")
    assert not result.accepted
    assert result.error_code == RISK_CONTRACT_MANIFEST_MISSING


def test_a_project_without_the_capability_is_refused():
    """`structa` nao declara `risk_analysis` — e o manifesto real que decide."""
    result = _validate(_contract(), project_id="structa")
    assert not result.accepted
    assert result.error_code == RISK_CONTRACT_CAPABILITY_NOT_DECLARED


def test_identity_comes_from_the_credential_not_from_the_payload():
    """O consumidor declara; a credencial decide — como nos demais contratos."""
    contract = RiskRequestContractV1.model_validate(_contract())
    adapted = contract.to_risk_request_payload(producer=PRODUCER, project_id=PROJECT)
    assert adapted["producer"] == PRODUCER
    assert adapted["project_id"] == PROJECT
    # E o payload adaptado e aceito pelo motor V1 sem qualquer alteracao nele.
    assert RiskRequest.model_validate(adapted).project_id == PROJECT


def test_the_adapted_request_reaches_the_v1_engine_unchanged():
    """O contrato novo e uma porta nova para a mesma sala."""
    contract = RiskRequestContractV1.model_validate(_contract())
    analysis = pre_execution_risk_service.analyze(
        RiskRequest.model_validate(
            contract.to_risk_request_payload(producer=PRODUCER, project_id=PROJECT)
        )
    )
    assert analysis.project_id == PROJECT
    assert analysis.target_operation_executed is False
    assert analysis.provider_called is False


# ---------------------------------------------------------------------------
# R5 — Scenario Simulation V2
# ---------------------------------------------------------------------------


def _analyze(**context) -> list:
    payload = _contract(context=context)
    contract = RiskRequestContractV1.model_validate(payload)
    analysis = pre_execution_risk_service.analyze(
        RiskRequest.model_validate(
            contract.to_risk_request_payload(producer=PRODUCER, project_id=PROJECT)
        )
    )
    return analysis.simulations


def test_scenarios_never_execute_the_target_operation():
    """A garantia que nao pode cair: simular nao e executar."""
    for scenario in _analyze(allowed_scope=["module:billing"]):
        assert scenario.mode == "analytical_dry_run"
        assert scenario.target_operation_executed is False


def test_the_six_base_scenarios_are_always_present():
    names = [item.scenario for item in _analyze(allowed_scope=["module:billing"])]
    for base in (
        "success",
        "partial_failure",
        "scope_deviation",
        "dependency_failure",
        "rollback_requirement",
        "security_impact",
    ):
        assert base in names


def test_irrelevant_scenarios_are_not_emitted():
    """Sem testes exigidos e sem integracao externa, os dois nao aparecem.

    Emitir cenario irrelevante para completar lista treina quem le a ignorar a
    lista inteira.
    """
    names = [item.scenario for item in _analyze(allowed_scope=["module:billing"])]
    assert "test_failure" not in names
    assert "external_service_failure" not in names


def test_declared_tests_bring_the_test_failure_scenario():
    names = [
        item.scenario
        for item in _analyze(allowed_scope=["module:billing"], required_tests=["unit"])
    ]
    assert "test_failure" in names


def test_declared_integrations_bring_the_external_failure_scenario():
    scenarios = _analyze(
        allowed_scope=["module:billing"], external_integrations=["stripe"]
    )
    external = next(
        item for item in scenarios if item.scenario == "external_service_failure"
    )
    assert external.affected_scope == ["stripe"]
    # Efeito externo nao volta com rollback local — e isso fica dito.
    assert "rollback local" in (external.containment or "")


def test_every_scenario_explains_how_to_act():
    """Severidade sozinha nao ajuda ninguem a agir.

    O que ajuda e o que dispara, o que atinge, como conter e o que verificar.
    """
    for scenario in _analyze(allowed_scope=["module:billing"], required_tests=["unit"]):
        assert scenario.expected_effect
        assert scenario.preconditions
        assert scenario.containment
        assert scenario.rollback_requirement in {"none", "recommended", "required"}
        assert 0.0 <= scenario.confidence <= 1.0


def test_residual_risk_is_declared_separately_from_severity():
    """O que sobra depois da contencao nao e o mesmo que o impacto bruto."""
    scenarios = _analyze(allowed_scope=["module:billing"])
    success = next(item for item in scenarios if item.scenario == "success")
    assert success.severity is RiskSeverity.INFO
    assert success.residual_risk is RiskSeverity.INFO
    deviation = next(item for item in scenarios if item.scenario == "scope_deviation")
    assert deviation.residual_risk is not None


def test_a_missing_rollback_plan_raises_the_rollback_scenario():
    scenarios = _analyze(allowed_scope=["module:billing"], rollback_plan_present=False)
    rollback = next(
        item for item in scenarios if item.scenario == "rollback_requirement"
    )
    assert "ausente" in " ".join(rollback.preconditions)
    assert rollback.rollback_requirement == "required"


def test_confidence_distinguishes_deterministic_from_heuristic():
    """Cenario derivado de regra vale mais que cenario derivado de palpite.

    Apresentar os dois com o mesmo peso esconderia a diferenca.
    """
    scenarios = _analyze(allowed_scope=["module:billing"])
    success = next(item for item in scenarios if item.scenario == "success")
    dependency = next(
        item for item in scenarios if item.scenario == "dependency_failure"
    )
    assert success.confidence > dependency.confidence

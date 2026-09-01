"""Stage R4 — porta operacional do contrato universal de risco.

O contrato ja era validado e testado; o que faltava era a rota. Estes casos
cobrem a rota, e o foco continua sendo o caminho desonesto: consumidor
tentando declarar o proprio veredito, usar credencial de outro projeto ou
submeter versao que ninguem reconhece.

Nenhum caso executa a operacao analisada, e nenhum provider e chamado.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.caller_identity.service import FLAG_CALLER_REGISTRY
from app.modules.retrieval.schemas import RetrievalResponse
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_engine.universal_contract import (
    RISK_CONTRACT_AUTHORITY_VIOLATION,
    RISK_CONTRACT_CAPABILITY_NOT_DECLARED,
    RISK_CONTRACT_PAYLOAD_INVALID,
    RISK_CONTRACT_VERSION_UNKNOWN,
    RISK_REQUEST_CONTRACT_V1,
)

client = TestClient(app)
AUTH_HEADER = "X-PedroCore-Api-Key"

# `pedrocore` e o projeto que declara a capability `risk_analysis`. `structa`
# existe no manifesto e NAO a declara — e por isso serve de caso negativo real
# em vez de um projeto inventado para o teste.
CORE_KEY = "risk-universal-core-key-synthetic"
OTHER_KEY = "risk-universal-other-key-synthetic"
CORE_PRODUCER = "pedrocore-technical-tool"
OTHER_PRODUCER = "structa-technical-tool"

ENDPOINT = "/api/risk/universal/analyze"


def _registry() -> str:
    return json.dumps(
        [
            {
                "credential_id": CORE_PRODUCER,
                "api_key": CORE_KEY,
                "project_id": "pedrocore",
                "role": "technical_tool",
                "environment": "development",
                "allowed_origins": ["pedrocore"],
            },
            {
                "credential_id": OTHER_PRODUCER,
                "api_key": OTHER_KEY,
                "project_id": "structa",
                "role": "technical_tool",
                "environment": "development",
                "allowed_origins": ["structa"],
            },
        ]
    )


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    monkeypatch.setattr(
        retrieval_service,
        "retrieve",
        lambda query, **_: RetrievalResponse(
            query_id=query.query_id, project_id=query.project_id
        ),
    )


def _contract(**overrides) -> dict:
    payload = {
        "contract_version": RISK_REQUEST_CONTRACT_V1,
        "request_id": "risk-http-001",
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


def _post(contract, *, key=CORE_KEY, producer=CORE_PRODUCER, project="pedrocore"):
    return client.post(
        ENDPOINT,
        headers={AUTH_HEADER: key},
        json={"producer": producer, "project_id": project, "contract": contract},
    )


def test_a_valid_contract_is_analysed():
    response = _post(_contract())
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["contract_version"] == RISK_REQUEST_CONTRACT_V1
    assert body["gate_decided_by_consumer"] is False


def test_the_route_never_executes_the_target_operation():
    """A garantia que nao pode cair, agora tambem pela porta HTTP."""
    analysis = _post(_contract()).json()["analysis"]
    assert analysis["target_operation_executed"] is False
    assert analysis["provider_called"] is False
    assert analysis["operational_memory_created"] is False
    assert all(item["mode"] == "analytical_dry_run" for item in analysis["simulations"])


def test_the_consumer_cannot_declare_the_gate_over_http():
    """O ataque que a porta existe para nao abrir."""
    response = _post(_contract(gate="PASS"))
    assert response.status_code == 403
    body = response.json()
    assert body["error_code"] == RISK_CONTRACT_AUTHORITY_VIOLATION
    assert body["authority_violations"]


@pytest.mark.parametrize("field", ["safe", "approved", "risk_level", "override", "bypass"])
def test_no_verdict_field_passes_the_route(field):
    response = _post(_contract(**{field: True}))
    assert response.status_code == 403
    assert response.json()["error_code"] == RISK_CONTRACT_AUTHORITY_VIOLATION


def test_a_verdict_nested_deep_is_refused_over_http():
    response = _post(
        _contract(context={"allowed_scope": ["module:billing"], "gate": "PASS"})
    )
    assert response.status_code == 403
    assert response.json()["error_code"] == RISK_CONTRACT_AUTHORITY_VIOLATION


def test_an_unknown_contract_version_is_refused():
    response = _post(_contract(contract_version="pedrocore-risk-request/v9"))
    assert response.status_code == 422
    assert response.json()["error_code"] == RISK_CONTRACT_VERSION_UNKNOWN


def test_a_malformed_contract_does_not_echo_the_value():
    secret = "TOKEN-QUE-NAO-PODE-VAZAR-123456"
    response = _post(_contract(request_id={"nested": secret}))
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == RISK_CONTRACT_PAYLOAD_INVALID
    assert secret not in json.dumps(body)


def test_a_project_without_the_capability_is_refused():
    """Quem decide e o Capability Manifest real, nao uma lista no router."""
    response = _post(_contract(), key=OTHER_KEY, producer=OTHER_PRODUCER, project="structa")
    assert response.status_code == 403
    assert response.json()["error_code"] == RISK_CONTRACT_CAPABILITY_NOT_DECLARED


def test_a_credential_cannot_submit_for_another_project():
    """Identidade vem da credencial; declarar outro projeto nao a muda."""
    response = _post(_contract(), key=OTHER_KEY, producer=OTHER_PRODUCER, project="pedrocore")
    assert response.status_code == 403


def test_the_producer_cannot_be_forged_in_the_envelope():
    response = _post(_contract(), key=CORE_KEY, producer=OTHER_PRODUCER)
    assert response.status_code == 403


def test_the_route_requires_authentication():
    response = client.post(
        ENDPOINT,
        json={"producer": CORE_PRODUCER, "project_id": "pedrocore", "contract": _contract()},
    )
    assert response.status_code == 401


def test_the_envelope_refuses_unknown_fields():
    """`extra='forbid'` no envelope: campo desconhecido nao passa despercebido."""
    response = client.post(
        ENDPOINT,
        headers={AUTH_HEADER: CORE_KEY},
        json={
            "producer": CORE_PRODUCER,
            "project_id": "pedrocore",
            "contract": _contract(),
            "gate": "PASS",
        },
    )
    assert response.status_code == 422

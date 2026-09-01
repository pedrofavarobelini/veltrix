"""Risk Engine V2 — Stage R1: o gate recusa o que promete recusar.

Por que esta suíte existe
-------------------------

O baseline R0 ([[RISK_ENGINE_V2_BASELINE]]) registrou como problema P4 que os
gates do V1 são calculados e testados no caminho feliz, mas **não havia prova
estrutural de que um `BLOCK` não pode ser contornado**. Isso era garantido por
revisão de código, não por teste.

Este projeto já viu essa distinção custar caro: a fronteira de autoridade da
Era 3 nasceu porque "ninguém tentou ainda" tinha sido confundido com "é
impossível". Um gate de risco que não recusa é um comentário caro.

Nenhuma linha de produção foi alterada por esta suíte. Ela é o primeiro estágio
do V2 justamente por isso: aumenta a confiança em tudo que vier depois, sem
mudar comportamento. Antes de mexer no motor de risco, é preciso provar que o
motor atual recusa o que diz recusar.

O que se testa aqui
-------------------

Só o caminho **desonesto**: escopo proibido, permissão ausente, operação
desconhecida, segredo em produção, assinatura adulterada, contrato expirado,
contexto trocado, projeto trocado e revisor não autorizado.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.retrieval.schemas import RetrievalResponse
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_engine.execution_contract_schemas import (
    ContractValidationRequest,
    HumanOverrideRequest,
    HumanReviewDecision,
    RiskGate,
)
from app.modules.risk_engine.execution_contract_service import (
    FLAG_CONTRACT_SIGNING_KEY,
    FLAG_REVIEWER_IDS,
    ContractConfigurationError,
    execution_contract_service,
)
from app.modules.risk_engine.schemas import RiskRequest

SIGNING_KEY = "synthetic-contract-signing-key-with-more-than-32-characters"
REVIEWER = "alpha-reviewer"
PRODUCER = "alpha-technical-tool"


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setenv(FLAG_CONTRACT_SIGNING_KEY, SIGNING_KEY)
    monkeypatch.setenv(FLAG_REVIEWER_IDS, REVIEWER)
    # Retrieval vazio: o histórico não deve influenciar os casos determinísticos.
    monkeypatch.setattr(
        retrieval_service,
        "retrieve",
        lambda query, **_: RetrievalResponse(
            query_id=query.query_id, project_id=query.project_id
        ),
    )
    yield


def _payload(**overrides) -> dict:
    values = {
        "request_id": "gate-bypass-001",
        "producer": "alpha-technical-tool",
        "project_id": "alpha",
        "request_text": "Change the billing module within approved scope.",
        "environment": "development",
        "agent_id": "codex-local",
        "permissions": ["read:billing", "write:billing"],
        "context": {
            "allowed_scope": ["module:billing", "file:billing/service.py"],
            "forbidden_scope": ["module:auth", "file:auth/service.py"],
            "known_modules": ["billing"],
            "constraints": ["local only"],
            "acceptance_criteria": ["tests pass"],
            "required_tests": ["billing unit"],
            "rollback_plan_present": True,
        },
        "requested_operation": {
            "kind": "WRITE",
            "targets": ["module:billing", "file:billing/service.py"],
            "expected_changes": ["bounded edit"],
        },
    }
    values.update(overrides)
    return values


def _request(**overrides) -> RiskRequest:
    return RiskRequest.model_validate(_payload(**overrides))


def _issue(request: RiskRequest | None = None):
    return execution_contract_service.issue(request or _request())


def _caller(credential_id: str = REVIEWER) -> AuthenticatedCallerContext:
    return AuthenticatedCallerContext(
        credential_id=credential_id,
        caller_role=CallerRole.TECHNICAL_TOOL,
        environment="test",
        identity_strength=IdentityStrength.REGISTERED,
        authenticated=True,
        project_id="alpha",
        allowed_origins=("alpha",),
    )


# ---------------------------------------------------------------------------
# O gate BLOQUEIA o que deve bloquear
# ---------------------------------------------------------------------------


def test_forbidden_scope_blocks():
    """Tocar alvo explicitamente proibido é bloqueio, não aviso."""
    issued = _issue(
        _request(
            requested_operation={
                "kind": "WRITE",
                "targets": ["module:auth"],
                "expected_changes": ["editar auth"],
            }
        )
    )
    assert issued.gate is RiskGate.BLOCK
    assert "FORBIDDEN_SCOPE" in issued.reason_codes


def test_missing_permission_blocks():
    """Escrever sem permissão de escrita é bloqueio."""
    issued = _issue(_request(permissions=["read:billing"]))
    assert issued.gate is RiskGate.BLOCK
    assert "PERMISSION_CONFLICT" in issued.reason_codes


def test_unknown_operation_blocks():
    """Operação desconhecida não é tratada como inofensiva.

    Fail-closed: o que o motor não sabe classificar, ele não libera.
    """
    issued = _issue(
        _request(
            requested_operation={
                "kind": "UNKNOWN",
                "targets": ["module:billing"],
                "expected_changes": ["?"],
            }
        )
    )
    assert issued.gate is RiskGate.BLOCK
    assert "OPERATION_UNKNOWN" in issued.reason_codes


def test_secret_change_in_production_blocks():
    """Segredo em produção é a combinação que o motor existe para barrar."""
    issued = _issue(
        _request(
            environment="production",
            request_text="Rotate the API_KEY in the .env of the billing module.",
            requested_operation={
                "kind": "WRITE",
                "targets": ["file:billing/.env"],
                "expected_changes": ["rotate secret"],
            },
        )
    )
    assert issued.gate is RiskGate.BLOCK
    assert "PRODUCTION_SECRET_CHANGE" in issued.reason_codes


# ---------------------------------------------------------------------------
# Um BLOCK não pode ser contornado
# ---------------------------------------------------------------------------


def test_blocked_contract_never_validates():
    """A recusa sobrevive à validação: gate BLOCK nunca devolve `valid=True`."""
    issued = _issue(_request(permissions=["read:billing"]))
    assert issued.gate is RiskGate.BLOCK

    validation = execution_contract_service.validate(
        ContractValidationRequest(producer=PRODUCER, contract=issued, current_request=_request(
            permissions=["read:billing"]
        ))
    )
    assert validation.valid is False
    assert "CONTRACT_BLOCKED" in validation.reason_codes


def test_consumer_cannot_flip_the_gate_by_editing_the_contract():
    """O ataque mais direto: reescrever `gate` para PASS no objeto devolvido.

    A assinatura cobre o conteúdo, então adulterar o gate quebra a integridade —
    e o contrato adulterado é recusado por assinatura, não por gentileza.
    """
    issued = _issue(_request(permissions=["read:billing"]))
    forged = issued.model_copy(
        update={"gate": RiskGate.PASS, "reason_codes": ["POLICY_REQUIREMENTS_SATISFIED"]}
    )

    validation = execution_contract_service.validate(
        ContractValidationRequest(
            producer=PRODUCER,
            contract=forged,
            current_request=_request(permissions=["read:billing"]),
        )
    )
    assert validation.valid is False
    assert validation.integrity_valid is False
    assert "CONTRACT_INTEGRITY_INVALID" in validation.reason_codes


def test_tampered_scope_breaks_integrity():
    """Ampliar o escopo permitido depois de assinado é adulteração."""
    issued = _issue()
    forged = issued.model_copy(
        update={"allowed_scope": [*issued.allowed_scope, "module:auth"]}
    )
    validation = execution_contract_service.validate(
        ContractValidationRequest(producer=PRODUCER, contract=forged, current_request=_request())
    )
    assert validation.integrity_valid is False
    assert validation.valid is False


def test_expired_contract_is_refused_even_when_it_passed():
    """Contrato vale pelo tempo que declarou. Depois disso, não vale."""
    issued = _issue()
    assert issued.gate in {RiskGate.PASS, RiskGate.PASS_WITH_WARNINGS}

    future = issued.expires_at + timedelta(minutes=1)
    validation = execution_contract_service.validate(
        ContractValidationRequest(producer=PRODUCER, contract=issued, current_request=_request()),
        now=future,
    )
    assert validation.expired is True
    assert validation.valid is False
    assert "CONTRACT_EXPIRED" in validation.reason_codes


def test_contract_does_not_transfer_to_a_changed_request():
    """Contrato aprovado para uma coisa não autoriza outra.

    Sem isto, bastaria pedir algo inofensivo, receber o contrato e executar
    outra operação sob a mesma assinatura.
    """
    issued = _issue()
    other = _request(
        requested_operation={
            "kind": "DELETE",
            "targets": ["module:billing"],
            "expected_changes": ["remover módulo"],
        }
    )
    validation = execution_contract_service.validate(
        ContractValidationRequest(producer=PRODUCER, contract=issued, current_request=other)
    )
    assert validation.context_valid is False
    assert validation.valid is False
    assert "CONTEXT_CHANGED" in validation.reason_codes


def test_contract_does_not_transfer_across_projects():
    """Isolamento de projeto atravessa também o contrato assinado."""
    issued = _issue()
    other_project = _request(project_id="beta")
    validation = execution_contract_service.validate(
        ContractValidationRequest(
            producer=PRODUCER, contract=issued, current_request=other_project
        )
    )
    assert validation.context_valid is False
    assert validation.valid is False


def test_review_required_is_not_valid_without_review():
    """`REVIEW_REQUIRED` não é `PASS` silencioso: sem revisão, não vale."""
    issued = _issue(
        _request(
            context={
                "allowed_scope": ["module:billing"],
                "forbidden_scope": [],
                "known_modules": [],
                "constraints": [],
                "acceptance_criteria": [],
                "required_tests": [],
                "rollback_plan_present": False,
            },
            request_text="Refactor the entire billing module without tests.",
        )
    )
    if issued.gate is RiskGate.REVIEW_REQUIRED:
        validation = execution_contract_service.validate(
            ContractValidationRequest(
                producer=PRODUCER,
                contract=issued,
                current_request=_request(
                    context={
                        "allowed_scope": ["module:billing"],
                        "forbidden_scope": [],
                        "known_modules": [],
                        "constraints": [],
                        "acceptance_criteria": [],
                        "required_tests": [],
                        "rollback_plan_present": False,
                    },
                    request_text="Refactor the entire billing module without tests.",
                ),
            )
        )
        assert validation.valid is False
        assert "HUMAN_REVIEW_REQUIRED" in validation.reason_codes


# ---------------------------------------------------------------------------
# Assinatura e autorização
# ---------------------------------------------------------------------------


def test_issuing_without_a_signing_key_fails_closed(monkeypatch):
    """Sem chave, não se emite contrato — não se emite contrato sem assinatura."""
    monkeypatch.delenv(FLAG_CONTRACT_SIGNING_KEY, raising=False)
    with pytest.raises(ContractConfigurationError):
        _issue()


def test_a_weak_signing_key_is_refused(monkeypatch):
    """Chave curta é recusada: assinatura fraca é pior que ausência declarada."""
    monkeypatch.setenv(FLAG_CONTRACT_SIGNING_KEY, "curta-demais")
    with pytest.raises(ContractConfigurationError):
        _issue()


def test_a_contract_signed_with_another_key_is_refused(monkeypatch):
    """Assinatura de outra chave não vale aqui — é o ponto de ter chave."""
    issued = _issue()
    monkeypatch.setenv(FLAG_CONTRACT_SIGNING_KEY, "outra-chave-sintetica-com-mais-de-32-chars")
    validation = execution_contract_service.validate(
        ContractValidationRequest(producer=PRODUCER, contract=issued, current_request=_request())
    )
    assert validation.integrity_valid is False
    assert validation.valid is False


def test_only_registered_reviewers_can_override():
    """Override é poder de revisor, não de qualquer credencial autenticada."""
    assert execution_contract_service.reviewer_authorized(_caller(REVIEWER)) is True
    assert execution_contract_service.reviewer_authorized(_caller("quem-sou-eu")) is False


def test_override_by_an_unauthorized_caller_is_refused():
    """Override e poder de revisor registrado, nao de quem se declara revisor."""
    issued = _issue(_request(permissions=["read:billing"]))
    payload = HumanOverrideRequest(
        producer=PRODUCER,
        contract=issued,
        current_request=_request(permissions=["read:billing"]),
        decision=HumanReviewDecision.APPROVE,
        reason="quero passar mesmo assim, sem autorizacao",
    )
    with pytest.raises(PermissionError):
        execution_contract_service.override(payload, _caller("quem-sou-eu"))


def test_an_authorized_reviewer_cannot_rescue_an_invalid_contract():
    """Nem revisor legitimo salva contrato adulterado.

    Override existe para decidir sobre RISCO, nao para consertar integridade:
    aceitar um contrato com assinatura quebrada transformaria a revisao humana
    no bypass que a assinatura existia para impedir.
    """
    issued = _issue()
    forged = issued.model_copy(
        update={"allowed_scope": [*issued.allowed_scope, "module:auth"]}
    )
    record = execution_contract_service.override(
        HumanOverrideRequest(
            producer=PRODUCER,
            contract=forged,
            current_request=_request(),
            decision=HumanReviewDecision.APPROVE,
            reason="aprovando apesar da integridade quebrada",
        ),
        _caller(REVIEWER),
    )
    assert record.resulting_gate is RiskGate.BLOCK
    assert "INVALID_CONTRACT_CANNOT_BE_OVERRIDDEN" in record.reason_codes


# ---------------------------------------------------------------------------
# O gate não é decorativo
# ---------------------------------------------------------------------------


def test_gate_reasons_are_never_empty():
    """Toda decisão carrega o porquê — decisão sem motivo não é auditável."""
    for request in (
        _request(),
        _request(permissions=["read:billing"]),
        _request(
            requested_operation={
                "kind": "WRITE",
                "targets": ["module:auth"],
                "expected_changes": ["x"],
            }
        ),
    ):
        assert _issue(request).reason_codes


def test_the_consumer_cannot_send_a_field_that_relaxes_the_gate():
    """Nenhum campo do `RiskRequest` liga PASS por conta própria.

    O gate é derivado de escopo, permissão, operação e ambiente. Um consumidor
    que pudesse declarar o próprio veredito tornaria o motor decorativo.
    """
    blocked = _issue(_request(permissions=["read:billing"]))
    assert blocked.gate is RiskGate.BLOCK

    fields = set(RiskRequest.model_fields)
    for forbidden in ("gate", "risk_gate", "approved", "override", "force", "bypass"):
        assert forbidden not in fields

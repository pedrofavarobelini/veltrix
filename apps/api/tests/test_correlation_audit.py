"""E9 — trilha unificada e correlacao.

O foco: seguir uma operacao inteira, provar que a trilha nao carrega conteudo
nem segredo, e que um projeto nao alcanca a trilha de outro.
"""

from __future__ import annotations

import pytest

from app.modules.correlation.schemas import AuditEvent, AuditOutcome, AuditStage
from app.modules.correlation.service import (
    AuditTrailService,
    CorrelationError,
    audit_trail_service,
    derive_correlation_id,
    new_correlation_id,
)

ALPHA = "pedrocore"
BETA = "structa"


@pytest.fixture(autouse=True)
def limpa():
    audit_trail_service.reset()
    yield
    audit_trail_service.reset()


def _record(service, correlacao, stage, *, project=ALPHA, outcome=AuditOutcome.OK, **kw):
    return service.record(
        correlation_id=correlacao,
        stage=stage,
        action=kw.pop("action", "acao"),
        outcome=outcome,
        project_id=project,
        producer=kw.pop("producer", "pedrocore-ci"),
        environment=kw.pop("environment", "development"),
        **kw,
    )


# --- seguir a operacao -----------------------------------------------------


def test_one_operation_can_be_followed_across_every_stage():
    """A pergunta que a trilha existe para responder."""
    service = AuditTrailService()
    correlacao = new_correlation_id()
    for stage in (
        AuditStage.CONSUMER,
        AuditStage.POLICY,
        AuditStage.RUNTIME,
        AuditStage.ROUTING,
        AuditStage.PROVIDER,
        AuditStage.RISK,
        AuditStage.CONTRACT,
        AuditStage.EVIDENCE,
    ):
        _record(service, correlacao, stage)

    trilha = service.trail(ALPHA, correlacao)
    assert len(trilha.events) == 8
    assert trilha.stages[0] is AuditStage.CONSUMER
    assert trilha.stages[-1] is AuditStage.EVIDENCE


def test_the_trail_preserves_the_order_things_happened():
    service = AuditTrailService()
    correlacao = new_correlation_id()
    for acao in ("primeira", "segunda", "terceira"):
        _record(service, correlacao, AuditStage.RUNTIME, action=acao)
    assert [item.action for item in service.trail(ALPHA, correlacao).events] == [
        "primeira",
        "segunda",
        "terceira",
    ]


def test_a_blocked_stage_marks_the_whole_trail():
    service = AuditTrailService()
    correlacao = new_correlation_id()
    _record(service, correlacao, AuditStage.POLICY, outcome=AuditOutcome.BLOCKED)
    trilha = service.trail(ALPHA, correlacao)
    assert trilha.blocked is True
    assert trilha.failed is False


def test_an_unknown_correlation_returns_an_empty_trail_not_an_error():
    trilha = audit_trail_service.trail(ALPHA, "corr-que-nao-existe-12345")
    assert trilha.events == []


# --- correlacao ------------------------------------------------------------


def test_a_derived_correlation_is_stable_across_retries():
    """Um retry não pode fragmentar a operação em duas trilhas."""
    primeiro = derive_correlation_id("pedrocore", "request-001")
    segundo = derive_correlation_id("pedrocore", "request-001")
    assert primeiro == segundo


def test_different_operations_derive_different_correlations():
    assert derive_correlation_id("pedrocore", "a") != derive_correlation_id(
        "pedrocore", "b"
    )


def test_a_generated_correlation_is_accepted_by_the_contract():
    _record(AuditTrailService(), new_correlation_id(), AuditStage.RUNTIME)


@pytest.mark.parametrize("invalido", ["curto", "", "com espaço aqui", "x" * 200])
def test_a_correlation_that_is_not_an_identifier_is_refused(invalido):
    with pytest.raises(Exception):
        _record(AuditTrailService(), invalido, AuditStage.RUNTIME)


# --- privacidade -----------------------------------------------------------


@pytest.mark.parametrize(
    "chave", ["prompt", "request_text", "payload", "api_key", "token", "database_url"]
)
def test_content_and_secret_keys_are_refused_at_the_door(chave):
    """A recusa é na entrada: a trilha é armazenamento de longa duração."""
    with pytest.raises(CorrelationError) as erro:
        _record(
            AuditTrailService(),
            new_correlation_id(),
            AuditStage.RUNTIME,
            references={chave: "qualquer coisa"},
        )
    assert "ponteiro" in str(erro.value) or "segredo" in str(erro.value)


def test_a_value_shaped_like_a_secret_is_refused_even_under_a_harmless_key():
    with pytest.raises(CorrelationError):
        _record(
            AuditTrailService(),
            new_correlation_id(),
            AuditStage.RUNTIME,
            references={"origem": "postgresql://user:supersecret@host:5432/db"},
        )


def test_a_reference_that_is_too_long_to_be_a_pointer_is_refused():
    """Um prompt inteiro não cabe num campo de ponteiro — de propósito."""
    with pytest.raises(Exception):
        AuditEvent(
            event_id="audit_" + "a" * 16,
            correlation_id=new_correlation_id(),
            stage=AuditStage.RUNTIME,
            action="a",
            outcome=AuditOutcome.OK,
            project_id=ALPHA,
            producer="ci",
            environment="development",
            occurred_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
            references={"conteudo": "x" * 500},
        )


def test_every_event_declares_it_carries_no_raw_payload():
    evento = _record(AuditTrailService(), new_correlation_id(), AuditStage.RUNTIME)
    assert evento.contains_raw_payload is False


def test_legitimate_pointers_are_accepted():
    evento = _record(
        AuditTrailService(),
        new_correlation_id(),
        AuditStage.RISK,
        references={"analysis_id": "analysis_abc123", "contract_id": "contract_xyz"},
    )
    assert evento.references["analysis_id"] == "analysis_abc123"


# --- isolamento ------------------------------------------------------------


def test_a_project_cannot_read_another_projects_trail():
    """A chave é composta: o namespace do outro simplesmente não existe."""
    service = AuditTrailService()
    correlacao = new_correlation_id()
    _record(service, correlacao, AuditStage.RUNTIME, project=ALPHA)

    assert service.trail(ALPHA, correlacao).events
    assert service.trail(BETA, correlacao).events == []


def test_the_same_correlation_in_two_projects_stays_separate():
    service = AuditTrailService()
    correlacao = new_correlation_id()
    _record(service, correlacao, AuditStage.RUNTIME, project=ALPHA, action="alfa")
    _record(service, correlacao, AuditStage.RUNTIME, project=BETA, action="beta")

    assert [item.action for item in service.trail(ALPHA, correlacao).events] == ["alfa"]
    assert [item.action for item in service.trail(BETA, correlacao).events] == ["beta"]


def test_listing_correlations_is_scoped_to_the_project():
    service = AuditTrailService()
    _record(service, new_correlation_id(), AuditStage.RUNTIME, project=ALPHA)
    _record(service, new_correlation_id(), AuditStage.RUNTIME, project=BETA)
    assert len(service.correlations(ALPHA)) == 1
    assert len(service.correlations(BETA)) == 1


# --- limites ---------------------------------------------------------------


def test_a_looping_operation_is_refused_instead_of_eating_memory():
    """Trilha ilimitada é vazamento de memória com aparência de recurso."""
    service = AuditTrailService(max_events_per_trail=5)
    correlacao = new_correlation_id()
    for _ in range(5):
        _record(service, correlacao, AuditStage.RUNTIME)
    with pytest.raises(CorrelationError) as erro:
        _record(service, correlacao, AuditStage.RUNTIME)
    assert "laço" in str(erro.value)


def test_the_policy_decision_travels_with_the_event():
    evento = _record(
        AuditTrailService(),
        new_correlation_id(),
        AuditStage.POLICY,
        outcome=AuditOutcome.BLOCKED,
        policy_id="policy_abc",
        policy_version="policy-engine-v1",
        reason_codes=("EXECUTION_IS_NEVER_DELEGATED",),
    )
    assert evento.policy_id == "policy_abc"
    assert evento.reason_codes == ("EXECUTION_IS_NEVER_DELEGATED",)

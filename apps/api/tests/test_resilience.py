"""Resiliencia de integracao (Era 6).

O GATE 6 exige simular o ciclo inteiro: PedroCore disponivel, indisponivel,
envio armazenado, retry, recuperacao, retry duplicado, reconciliacao e falha
permanente. Cada cenario e um teste aqui, com transporte simulado — nenhuma
chamada de rede.

A propriedade que estes testes protegem:

    PedroCore fora do ar NAO derruba a funcionalidade do consumidor,
    e nada se perde nem se duplica logicamente quando ele volta.
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
from app.modules.evidence_platform.service import evidence_ingestion_service
from app.modules.resilience.outbox import (
    DEFAULT_MAX_ATTEMPTS,
    DeliveryOutcome,
    DeliveryState,
    OutboxDispatcher,
    OutboxStore,
    backoff_delay,
)
from app.modules.resilience.reconciliation import (
    ReconciliationRequest,
    reconciliation_service,
)
from app.modules.universal_contracts.versioning import (
    INTEGRATION_ENVELOPE_V1,
    QUALITY_EVIDENCE_V1,
)

NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "pedrocore"


@pytest.fixture(autouse=True)
def isolated_registry():
    evidence_ingestion_service.set_repository(InMemoryEvidenceRepository())
    yield
    evidence_ingestion_service.set_repository(None)


@pytest.fixture
def store() -> OutboxStore:
    return OutboxStore()


def _caller() -> AuthenticatedCallerContext:
    return AuthenticatedCallerContext(
        credential_id=f"{PROJECT}-ci",
        caller_role=CallerRole.TECHNICAL_TOOL,
        environment="test",
        identity_strength=IdentityStrength.REGISTERED,
        authenticated=True,
        project_id=PROJECT,
        allowed_origins=(PROJECT,),
    )


def _envelope(evidence_id: str = "ev-1", idempotency_key: str = "k1") -> dict:
    return {
        "envelope_version": INTEGRATION_ENVELOPE_V1,
        "event_id": f"evt-{evidence_id}",
        "payload_type": "quality_evidence",
        "project_id": PROJECT,
        "producer_id": f"{PROJECT}-ci",
        "idempotency_key": idempotency_key,
        "submitted_at": NOW.isoformat(),
        "payload": {
            "contract_version": QUALITY_EVIDENCE_V1,
            "evidence_id": evidence_id,
            "outcome": "passed",
            "observed_at": NOW.isoformat(),
            "environment": "ci",
            "suites": [{"suite_id": "unit", "outcome": "passed", "total": 3, "passed": 3}],
        },
    }


def _enqueue(store: OutboxStore, entry_id="out-1", key="k1", evidence_id="ev-1", **kw):
    return store.enqueue(
        entry_id=entry_id,
        project_id=PROJECT,
        idempotency_key=key,
        payload=_envelope(evidence_id, key),
        now=NOW,
        **kw,
    )


# --- transportes simulados -------------------------------------------------


def _online_transport(entry):
    """PedroCore disponivel: entrega de verdade, pela ingestao real."""
    result = evidence_ingestion_service.ingest(entry.payload, caller=_caller())
    if result.decision.value == "accepted":
        return DeliveryOutcome.DELIVERED, None
    if result.decision.value == "duplicate":
        return DeliveryOutcome.DUPLICATE, None
    return DeliveryOutcome.PERMANENT, result.error_code


def _offline_transport(_entry):
    """PedroCore indisponivel: falha de rede, retentavel."""
    raise ConnectionError("PedroCore indisponível")


# ---------------------------------------------------------------------------
# 1 e 2 — disponivel e indisponivel
# ---------------------------------------------------------------------------


def test_delivery_succeeds_while_pedrocore_is_available(store):
    _enqueue(store)
    [entry] = OutboxDispatcher(store).dispatch_once(_online_transport, now=NOW)
    assert entry.state is DeliveryState.DELIVERED
    assert evidence_ingestion_service.count_evidence(PROJECT) == 1


def test_consumer_keeps_working_while_pedrocore_is_unavailable(store):
    """A propriedade central: gravar no outbox nunca falha por causa do servidor."""
    entry = _enqueue(store)
    assert entry.state is DeliveryState.PENDING

    [attempted] = OutboxDispatcher(store).dispatch_once(_offline_transport, now=NOW)
    assert attempted.state is DeliveryState.PENDING
    assert attempted.attempts == 1
    assert attempted.last_error_code == "ConnectionError"
    # Nada se perdeu: continua na fila, esperando o servidor voltar.
    assert store.pending_count() == 1


# ---------------------------------------------------------------------------
# 3 e 4 — envio armazenado e retry com backoff
# ---------------------------------------------------------------------------


def test_retry_waits_for_exponential_backoff(store):
    _enqueue(store)
    dispatcher = OutboxDispatcher(store)

    [first] = dispatcher.dispatch_once(_offline_transport, now=NOW)
    assert first.next_attempt_at == NOW + timedelta(seconds=2)

    # Antes da hora, nao ha nada devido: o backoff e respeitado de verdade.
    assert dispatcher.dispatch_once(_offline_transport, now=NOW + timedelta(seconds=1)) == []

    [second] = dispatcher.dispatch_once(
        _offline_transport, now=NOW + timedelta(seconds=2)
    )
    assert second.attempts == 2
    # Segunda falha: o proximo intervalo dobra (2s -> 4s).
    assert second.next_attempt_at == NOW + timedelta(seconds=2) + timedelta(seconds=4)


def test_backoff_grows_exponentially_and_is_capped():
    """Sem teto, a oitava tentativa cairia em horas."""
    assert backoff_delay(0) == 0.0
    assert backoff_delay(1) == 2.0
    assert backoff_delay(2) == 4.0
    assert backoff_delay(3) == 8.0
    assert backoff_delay(20) == 300.0


# ---------------------------------------------------------------------------
# 5 e 6 — recuperacao e retry duplicado
# ---------------------------------------------------------------------------


def test_recovery_delivers_everything_that_was_waiting(store):
    _enqueue(store, entry_id="out-1", key="k1", evidence_id="ev-1")
    _enqueue(store, entry_id="out-2", key="k2", evidence_id="ev-2")
    dispatcher = OutboxDispatcher(store)

    dispatcher.dispatch_once(_offline_transport, now=NOW)
    assert store.pending_count() == 2
    assert evidence_ingestion_service.count_evidence(PROJECT) == 0

    later = NOW + timedelta(seconds=10)
    results = dispatcher.dispatch_once(_online_transport, now=later)
    assert {item.state for item in results} == {DeliveryState.DELIVERED}
    assert store.pending_count() == 0
    assert evidence_ingestion_service.count_evidence(PROJECT) == 2


def test_duplicate_retry_is_success_and_never_double_registers(store):
    """At-least-once do lado do cliente + dedup do lado do servidor.

    O caso classico: a entrega chegou, a RESPOSTA se perdeu, o cliente tenta de
    novo. O servidor reconhece a chave e o cliente marca como entregue — sem um
    segundo registro do mesmo fato.
    """
    dispatcher = OutboxDispatcher(store)
    _enqueue(store, entry_id="out-1", key="k1")
    dispatcher.dispatch_once(_online_transport, now=NOW)
    assert evidence_ingestion_service.count_evidence(PROJECT) == 1

    # Mesma chave, mesmo conteudo, reenviado por um cliente que nao viu a resposta.
    _enqueue(store, entry_id="out-1-retry", key="k1")
    [retried] = dispatcher.dispatch_once(_online_transport, now=NOW + timedelta(seconds=5))
    assert retried.state is DeliveryState.DELIVERED
    assert evidence_ingestion_service.count_evidence(PROJECT) == 1


def test_enqueueing_the_same_entry_twice_does_not_create_two_deliveries(store):
    first = _enqueue(store, entry_id="out-1")
    second = _enqueue(store, entry_id="out-1")
    assert first.entry_id == second.entry_id
    assert len(store.all_entries()) == 1


# ---------------------------------------------------------------------------
# 7 — reconciliacao
# ---------------------------------------------------------------------------


def test_reconciliation_reports_exactly_what_must_be_resent(store):
    """A terceira saida: nem reenviar tudo, nem perder dado."""
    dispatcher = OutboxDispatcher(store)
    _enqueue(store, entry_id="out-1", key="k1", evidence_id="ev-1")
    dispatcher.dispatch_once(_online_transport, now=NOW)

    report = reconciliation_service.reconcile(
        PROJECT, ReconciliationRequest(idempotency_keys=["k1", "k2", "k3"])
    )
    assert report.requested == 3
    assert report.known == 1
    assert report.missing == 2
    assert report.missing_keys == ["k2", "k3"]
    assert next(item for item in report.entries if item.known).evidence_record_id


def test_reconciliation_deduplicates_repeated_keys():
    report = reconciliation_service.reconcile(
        PROJECT, ReconciliationRequest(idempotency_keys=["k1", "k1", "k1"])
    )
    assert report.requested == 1


def test_reconciliation_never_registers_anything():
    """Perguntar nunca pode ser a forma de fazer o servidor passar a ter."""
    reconciliation_service.reconcile(
        PROJECT, ReconciliationRequest(idempotency_keys=["k1", "k2"])
    )
    assert evidence_ingestion_service.count_evidence(PROJECT) == 0


def test_reconciliation_is_isolated_by_project(store):
    _enqueue(store)
    OutboxDispatcher(store).dispatch_once(_online_transport, now=NOW)
    report = reconciliation_service.reconcile(
        "elyra", ReconciliationRequest(idempotency_keys=["k1"])
    )
    assert report.known == 0


# ---------------------------------------------------------------------------
# 8 — falha permanente vira dead-letter
# ---------------------------------------------------------------------------


def test_permanent_rejection_goes_straight_to_dead_letter(store):
    """Reenviar nao conserta contrato invalido; insistir so gera carga."""
    dispatcher = OutboxDispatcher(store)
    store.enqueue(
        entry_id="out-bad",
        project_id=PROJECT,
        idempotency_key="bad",
        payload={"envelope_version": "pedrocore-integration/v9"},
        now=NOW,
    )
    [entry] = dispatcher.dispatch_once(_online_transport, now=NOW)
    assert entry.state is DeliveryState.DEAD_LETTER
    assert entry.attempts == 1
    assert entry.last_error_code == "CONTRACT_VERSION_UNKNOWN"


def test_retryable_failure_becomes_dead_letter_after_max_attempts(store):
    dispatcher = OutboxDispatcher(store)
    _enqueue(store, max_attempts=3)
    moment = NOW
    entry = None
    for _ in range(3):
        [entry] = dispatcher.dispatch_once(_offline_transport, now=moment)
        if entry.state is DeliveryState.PENDING:
            moment = entry.next_attempt_at
    assert entry is not None
    assert entry.state is DeliveryState.DEAD_LETTER
    assert entry.attempts == 3
    assert store.dead_letters()


def test_dead_letter_is_visible_for_review_not_silently_lost(store):
    """Item que some nao gera alarme; dead-letter e pergunta esperando resposta."""
    dispatcher = OutboxDispatcher(store)
    _enqueue(store, max_attempts=1)
    dispatcher.dispatch_once(_offline_transport, now=NOW)
    dead = store.dead_letters()
    assert len(dead) == 1
    assert dead[0].entry_id == "out-1"
    assert dead[0].last_error_code


def test_reviewed_dead_letter_can_be_requeued_and_delivered(store):
    """Volta com o contador zerado: alguem olhou e corrigiu a causa."""
    dispatcher = OutboxDispatcher(store)
    _enqueue(store, max_attempts=1)
    dispatcher.dispatch_once(_offline_transport, now=NOW)

    requeued = dispatcher.requeue_dead_letter("out-1", now=NOW + timedelta(minutes=5))
    assert requeued is not None
    assert requeued.state is DeliveryState.PENDING
    assert requeued.attempts == 0

    [delivered] = dispatcher.dispatch_once(
        _online_transport, now=NOW + timedelta(minutes=5)
    )
    assert delivered.state is DeliveryState.DELIVERED
    assert evidence_ingestion_service.count_evidence(PROJECT) == 1


def test_requeue_only_applies_to_dead_letters(store):
    _enqueue(store)
    assert OutboxDispatcher(store).requeue_dead_letter("out-1") is None
    assert OutboxDispatcher(store).requeue_dead_letter("nao-existe") is None


# ---------------------------------------------------------------------------
# Robustez do despachante
# ---------------------------------------------------------------------------


def test_transport_exception_does_not_kill_the_worker(store):
    """Uma entrada ruim nao pode travar a fila inteira."""
    dispatcher = OutboxDispatcher(store)
    _enqueue(store, entry_id="out-boom", key="kb")
    _enqueue(store, entry_id="out-ok", key="ko", evidence_id="ev-ok")

    def flaky(entry):
        if entry.entry_id == "out-boom":
            raise RuntimeError("transporte quebrado")
        return _online_transport(entry)

    results = dispatcher.dispatch_once(flaky, now=NOW)
    states = {item.entry_id: item.state for item in results}
    assert states["out-boom"] is DeliveryState.PENDING
    assert states["out-ok"] is DeliveryState.DELIVERED


def test_default_max_attempts_is_bounded():
    assert 1 <= DEFAULT_MAX_ATTEMPTS <= 10

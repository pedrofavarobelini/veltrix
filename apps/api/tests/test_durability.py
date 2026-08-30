"""Durabilidade através de restart (Final Hardening).

Por que esta suíte existe
-------------------------

A Era 6 provou que o PedroCore fora do ar não derruba o consumidor. Mas provou
só metade da propriedade: o outbox em memória protege contra o SERVIDOR cair, e
não contra o CONSUMIDOR cair. O processo grava a entrega pendente, morre antes
de entregar, e a fila some com ele — o consumidor volta achando que enviou.

Um outbox que não sobrevive ao próprio processo é um buffer, não um outbox.

O que conta como restart
------------------------

**Instância nova, mesmo armazenamento.** Reutilizar o mesmo objeto em memória
não prova nada: ele nunca perdeu o estado. Todo teste aqui descarta a instância
e constrói outra apontando para o mesmo diretório — que é o que acontece quando
o processo volta.

Um dos testes vai além e grava em um **subprocesso separado**, que morre de
verdade antes de o teste ler o arquivo. Nem a memória do intérprete é
compartilhada nesse caso.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.dataset_registry.repository import LocalJsonDatasetRegistryRepository
from app.modules.dataset_registry.schemas import (
    DatasetDefinition,
    DatasetScope,
    DatasetStatus,
)
from app.modules.dataset_registry.service import dataset_registry_service
from app.modules.evidence_platform.repository import InMemoryEvidenceRepository
from app.modules.evidence_platform.service import evidence_ingestion_service
from app.modules.resilience.durable_outbox import DurableOutboxStore
from app.modules.resilience.outbox import (
    DeliveryOutcome,
    DeliveryState,
    OutboxDispatcher,
)
from app.modules.resilience.reconciliation import (
    ReconciliationRequest,
    reconciliation_service,
)
from app.modules.training_data.acquisition import training_candidate_service
from app.modules.training_data.schemas import TrainingPurpose, TrainingSourceType
from app.modules.universal_contracts.versioning import (
    INTEGRATION_ENVELOPE_V1,
    QUALITY_EVIDENCE_V1,
)

NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "pedrocore"
ADMIN = "alpha-admin"


@pytest.fixture(autouse=True)
def isolated_registry():
    evidence_ingestion_service.set_repository(InMemoryEvidenceRepository())
    yield
    evidence_ingestion_service.set_repository(None)


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


def _envelope(evidence_id="ev-1", key="k1") -> dict:
    return {
        "envelope_version": INTEGRATION_ENVELOPE_V1,
        "event_id": f"evt-{evidence_id}",
        "payload_type": "quality_evidence",
        "project_id": PROJECT,
        "producer_id": f"{PROJECT}-ci",
        "idempotency_key": key,
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


def _online(entry):
    result = evidence_ingestion_service.ingest(entry.payload, caller=_caller())
    if result.decision.value == "accepted":
        return DeliveryOutcome.DELIVERED, None
    if result.decision.value == "duplicate":
        return DeliveryOutcome.DUPLICATE, None
    return DeliveryOutcome.PERMANENT, result.error_code


def _offline(_entry):
    raise ConnectionError("PedroCore indisponível")


def _restart(directory: Path) -> DurableOutboxStore:
    """Simula o processo voltando: instância NOVA, mesmo diretório."""
    return DurableOutboxStore(directory)


# ---------------------------------------------------------------------------
# 1 e 2 — enqueue e persistência
# ---------------------------------------------------------------------------


def test_enqueue_writes_to_disk(tmp_path):
    store = DurableOutboxStore(tmp_path)
    store.enqueue(
        entry_id="out-1",
        project_id=PROJECT,
        idempotency_key="k1",
        payload=_envelope(),
        now=NOW,
    )
    target = tmp_path / "outbox.json"
    assert target.exists()
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert [item["entry_id"] for item in saved] == ["out-1"]


def test_write_is_atomic_leaving_no_temporary_behind(tmp_path):
    """Escrita direta tem janela em que o arquivo está truncado.

    Se o processo morre exatamente ali, o outbox volta corrompido — e o modo de
    falha que ele existe para resolver seria a causa da perda.
    """
    store = DurableOutboxStore(tmp_path)
    store.enqueue(
        entry_id="out-1", project_id=PROJECT, idempotency_key="k1",
        payload=_envelope(), now=NOW,
    )
    assert not list(tmp_path.glob("*.tmp"))
    assert (tmp_path / "outbox.json").exists()


# ---------------------------------------------------------------------------
# 3, 4 e 5 — restart, sobrevivência e retry
# ---------------------------------------------------------------------------


def test_pending_entry_survives_restart(tmp_path):
    """O caso que o outbox em memória perdia por completo."""
    first = DurableOutboxStore(tmp_path)
    first.enqueue(
        entry_id="out-1", project_id=PROJECT, idempotency_key="k1",
        payload=_envelope(), now=NOW,
    )
    OutboxDispatcher(first).dispatch_once(_offline, now=NOW)
    assert first.pending_count() == 1

    del first
    revived = _restart(tmp_path)

    assert revived.pending_count() == 1
    entry = revived.get("out-1")
    assert entry is not None
    assert entry.state is DeliveryState.PENDING
    assert entry.attempts == 1
    assert entry.last_error_code == "ConnectionError"


def test_retry_after_restart_delivers_the_pending_entry(tmp_path):
    first = DurableOutboxStore(tmp_path)
    first.enqueue(
        entry_id="out-1", project_id=PROJECT, idempotency_key="k1",
        payload=_envelope(), now=NOW,
    )
    OutboxDispatcher(first).dispatch_once(_offline, now=NOW)
    del first

    revived = _restart(tmp_path)
    later = NOW + timedelta(seconds=30)
    [delivered] = OutboxDispatcher(revived).dispatch_once(_online, now=later)

    assert delivered.state is DeliveryState.DELIVERED
    assert evidence_ingestion_service.count_evidence(PROJECT) == 1


def test_backoff_schedule_survives_restart(tmp_path):
    """O relógio do retry não pode reiniciar junto com o processo.

    Se `next_attempt_at` se perdesse, um consumidor que reinicia em laço
    marteleria um servidor que já está em dificuldade.
    """
    first = DurableOutboxStore(tmp_path)
    first.enqueue(
        entry_id="out-1", project_id=PROJECT, idempotency_key="k1",
        payload=_envelope(), now=NOW,
    )
    OutboxDispatcher(first).dispatch_once(_offline, now=NOW)
    scheduled = first.get("out-1").next_attempt_at
    del first

    revived = _restart(tmp_path)
    assert revived.get("out-1").next_attempt_at == scheduled
    # Antes da hora, continua não sendo devido — mesmo depois do restart.
    assert OutboxDispatcher(revived).dispatch_once(_offline, now=NOW) == []


def test_a_real_separate_process_writes_and_dies_before_we_read(tmp_path):
    """Restart de verdade: o processo que gravou já não existe mais.

    Instância nova no mesmo intérprete já seria prova suficiente; este teste
    remove até essa dúvida, porque o escritor morre antes da leitura.
    """
    probe = textwrap.dedent(
        f"""
        from datetime import datetime, timezone
        from app.modules.resilience.durable_outbox import DurableOutboxStore

        store = DurableOutboxStore(r"{tmp_path}")
        store.enqueue(
            entry_id="out-from-dead-process",
            project_id="{PROJECT}",
            idempotency_key="k-dead",
            payload={{"hello": "world"}},
            now=datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc),
        )
        print("WRITTEN")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "WRITTEN" in result.stdout

    # O processo escritor terminou. Este intérprete nunca viu o objeto.
    revived = DurableOutboxStore(tmp_path)
    entry = revived.get("out-from-dead-process")
    assert entry is not None
    assert entry.idempotency_key == "k-dead"
    assert entry.state is DeliveryState.PENDING


# ---------------------------------------------------------------------------
# 6 e 7 — acknowledgement e duplicata
# ---------------------------------------------------------------------------


def test_acknowledgement_survives_restart(tmp_path):
    """Entregue continua entregue: reenviar depois seria duplicar."""
    first = DurableOutboxStore(tmp_path)
    first.enqueue(
        entry_id="out-1", project_id=PROJECT, idempotency_key="k1",
        payload=_envelope(), now=NOW,
    )
    OutboxDispatcher(first).dispatch_once(_online, now=NOW)
    del first

    revived = _restart(tmp_path)
    entry = revived.get("out-1")
    assert entry.state is DeliveryState.DELIVERED
    assert entry.delivered_at is not None
    assert revived.pending_count() == 0
    # Nada devido: um restart não pode ressuscitar uma entrega concluída.
    assert OutboxDispatcher(revived).dispatch_once(_online, now=NOW) == []


def test_duplicate_delivery_after_restart_does_not_double_register(tmp_path):
    """At-least-once do cliente + dedup do servidor, atravessando o restart."""
    first = DurableOutboxStore(tmp_path)
    first.enqueue(
        entry_id="out-1", project_id=PROJECT, idempotency_key="k1",
        payload=_envelope(), now=NOW,
    )
    OutboxDispatcher(first).dispatch_once(_online, now=NOW)
    assert evidence_ingestion_service.count_evidence(PROJECT) == 1
    del first

    # O consumidor volta e reenvia o MESMO fato sob a mesma chave.
    revived = _restart(tmp_path)
    revived.enqueue(
        entry_id="out-1-retry", project_id=PROJECT, idempotency_key="k1",
        payload=_envelope(), now=NOW,
    )
    [retried] = OutboxDispatcher(revived).dispatch_once(
        _online, now=NOW + timedelta(seconds=5)
    )
    assert retried.state is DeliveryState.DELIVERED
    assert evidence_ingestion_service.count_evidence(PROJECT) == 1


# ---------------------------------------------------------------------------
# 8 — dead-letter
# ---------------------------------------------------------------------------


def test_dead_letter_survives_restart_and_stays_reviewable(tmp_path):
    """Item que some não gera alarme; dead-letter é pergunta esperando resposta."""
    first = DurableOutboxStore(tmp_path)
    first.enqueue(
        entry_id="out-bad", project_id=PROJECT, idempotency_key="bad",
        payload={"envelope_version": "pedrocore-integration/v9"},
        now=NOW, max_attempts=1,
    )
    OutboxDispatcher(first).dispatch_once(_online, now=NOW)
    del first

    revived = _restart(tmp_path)
    dead = revived.dead_letters()
    assert len(dead) == 1
    assert dead[0].entry_id == "out-bad"
    assert dead[0].last_error_code == "CONTRACT_VERSION_UNKNOWN"


def test_requeued_dead_letter_survives_restart_and_delivers(tmp_path):
    first = DurableOutboxStore(tmp_path)
    first.enqueue(
        entry_id="out-1", project_id=PROJECT, idempotency_key="k1",
        payload=_envelope(), now=NOW, max_attempts=1,
    )
    OutboxDispatcher(first).dispatch_once(_offline, now=NOW)
    OutboxDispatcher(first).requeue_dead_letter("out-1", now=NOW)
    del first

    revived = _restart(tmp_path)
    entry = revived.get("out-1")
    assert entry.state is DeliveryState.PENDING
    assert entry.attempts == 0

    [delivered] = OutboxDispatcher(revived).dispatch_once(_online, now=NOW)
    assert delivered.state is DeliveryState.DELIVERED


# ---------------------------------------------------------------------------
# 9 — reconciliação após restart
# ---------------------------------------------------------------------------


def test_reconciliation_after_restart_reports_what_to_resend(tmp_path):
    """A pergunta que o consumidor faz quando volta e não sabe o que chegou."""
    first = DurableOutboxStore(tmp_path)
    first.enqueue(
        entry_id="out-1", project_id=PROJECT, idempotency_key="k1",
        payload=_envelope("ev-1", "k1"), now=NOW,
    )
    first.enqueue(
        entry_id="out-2", project_id=PROJECT, idempotency_key="k2",
        payload=_envelope("ev-2", "k2"), now=NOW,
    )
    # Só a primeira é entregue antes da queda.
    OutboxDispatcher(first).dispatch_once(
        lambda entry: _online(entry) if entry.entry_id == "out-1" else _offline(entry),
        now=NOW,
    )
    del first

    revived = _restart(tmp_path)
    report = reconciliation_service.reconcile(
        PROJECT, ReconciliationRequest(idempotency_keys=["k1", "k2"])
    )
    assert report.known == 1
    assert report.missing_keys == ["k2"]
    # E o outbox concorda: exatamente `out-2` continua pendente.
    assert [item.entry_id for item in revived.due(now=NOW + timedelta(minutes=1))] == [
        "out-2"
    ]


def test_corrupted_file_does_not_crash_the_consumer(tmp_path):
    """Corrupção não derruba o processo — mas também não vira fila vazia.

    Esta era a versão antiga do teste, que afirmava `all_entries() == []` e
    seguia gravando por cima. Ela codificava o defeito: fingir vazio fazia a
    escrita seguinte apagar entregas que ninguém viu. O comportamento correto
    é degradar, e é o que se afirma agora.
    """
    (tmp_path / "outbox.json").write_text("{ isto não é json válido", encoding="utf-8")
    store = DurableOutboxStore(tmp_path)
    assert store.degraded is True
    assert store.corruption is not None


# ---------------------------------------------------------------------------
# Dataset Registry — durabilidade de metadata de governança
# ---------------------------------------------------------------------------


def _admin() -> AuthenticatedCallerContext:
    return AuthenticatedCallerContext(
        credential_id=ADMIN,
        caller_role=CallerRole.TECHNICAL_TOOL,
        environment="test",
        identity_strength=IdentityStrength.REGISTERED,
        authenticated=True,
        project_id="alpha",
        allowed_origins=("alpha",),
    )


def _definition() -> DatasetDefinition:
    return DatasetDefinition(
        dataset_id="ds-durable",
        display_name="Dataset durável",
        scope=DatasetScope.PROJECT,
        project_ids=("alpha",),
        training_purpose=TrainingPurpose.EVALUATION_ONLY,
        allowed_source_types=(TrainingSourceType.EVIDENCE_RECORD,),
        created_by=ADMIN,
        created_at=NOW,
    )


@pytest.fixture
def durable_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("PEDROCORE_TRAINING_DATA_ADMIN_IDS", ADMIN)
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "memory")
    dataset_registry_service.set_repository(
        LocalJsonDatasetRegistryRepository(tmp_path)
    )
    yield tmp_path
    dataset_registry_service.set_repository(None)


def test_dataset_definition_survives_restart(durable_registry):
    """Uma decisão de governança que morre com o processo vira boato."""
    dataset_registry_service.define(_definition(), _admin())

    # Restart: repositório NOVO, mesmo diretório.
    dataset_registry_service.set_repository(
        LocalJsonDatasetRegistryRepository(durable_registry)
    )
    restored = dataset_registry_service.get("ds-durable")
    assert restored is not None
    assert restored.status is DatasetStatus.DEFINED
    assert restored.created_by == ADMIN
    assert restored.training_purpose is TrainingPurpose.EVALUATION_ONLY
    assert restored.split_policy.train == pytest.approx(0.8)


def test_duplicate_definition_is_still_rejected_after_restart(durable_registry):
    """Sem isso, reiniciar o processo viraria uma forma de burlar a unicidade."""
    from app.modules.dataset_registry.service import DatasetRegistryError

    dataset_registry_service.define(_definition(), _admin())
    dataset_registry_service.set_repository(
        LocalJsonDatasetRegistryRepository(durable_registry)
    )
    with pytest.raises(DatasetRegistryError) as error:
        dataset_registry_service.define(_definition(), _admin())
    assert error.value.code == "DATASET_ALREADY_DEFINED"


def test_registry_file_is_written_atomically(durable_registry):
    dataset_registry_service.define(_definition(), _admin())
    assert (durable_registry / "dataset_registry.json").exists()
    assert not list(durable_registry.glob("*.tmp"))


def test_persisting_governance_does_not_create_population(durable_registry):
    """Persistir governança não fabrica dado — são coisas de natureza diferente."""
    dataset_registry_service.define(_definition(), _admin())
    dataset_registry_service.set_repository(
        LocalJsonDatasetRegistryRepository(durable_registry)
    )

    report = training_candidate_service.readiness(project_id="alpha")
    assert report.readiness == "DATASET_NOT_READY"
    assert report.canonical_dataset_created is False
    assert report.training_started is False
    assert dataset_registry_service.versions("ds-durable") == []


def test_materialization_is_still_refused_after_restart(durable_registry):
    from app.modules.dataset_registry.schemas import MaterializationRefusal

    dataset_registry_service.define(_definition(), _admin())
    dataset_registry_service.set_repository(
        LocalJsonDatasetRegistryRepository(durable_registry)
    )
    result = dataset_registry_service.materialize("ds-durable", _admin())
    assert isinstance(result, MaterializationRefusal)
    assert result.readiness == "DATASET_NOT_READY"
    assert result.canonical_dataset_created is False


def test_corrupted_registry_file_does_not_crash_startup(tmp_path):
    (tmp_path / "dataset_registry.json").write_text("não é json", encoding="utf-8")
    repository = LocalJsonDatasetRegistryRepository(tmp_path)
    assert repository.list_definitions() == []

"""Corrupção e wiring de produção (Final Durability Verification).

Duas lacunas que a revisão humana encontrou, e que esta suíte fecha.

**1. Corrupção virava fila vazia.** A primeira versão tratava arquivo ilegível
com `return`, deixando o store vazio. Isso é pior do que não persistir: o
consumidor conclui que não há nada pendente, e a escrita seguinte apaga
entregas que ninguém chegou a ver. Corrupção recuperável vira perda definitiva.

**2. A implementação durável nunca era construída fora de teste.** Nenhum
caminho de produção instanciava `DurableOutboxStore`, e o Dataset Registry
criava um store em memória no próprio `__init__`. "Durável" descrevia uma
classe disponível, não um comportamento em vigor. Uma peça montada só em teste
não protege nada.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.dataset_registry.factory import (
    build_dataset_registry_repository,
    dataset_registry_is_durable,
)
from app.modules.dataset_registry.repository import LocalJsonDatasetRegistryRepository
from app.modules.dataset_registry.schemas import DatasetDefinition, DatasetScope
from app.modules.dataset_registry.service import dataset_registry_service
from app.modules.report_memory.repository import ReportMemoryRepositoryConfigurationError
from app.modules.resilience.durable_outbox import (
    DurableOutboxStore,
    PostgreSQLOutboxStore,
)
from app.modules.resilience.factory import build_outbox_store, outbox_is_durable
from app.modules.resilience.outbox import OutboxDispatcher, OutboxStore
from app.modules.resilience.storage import DurableStorageDegradedError
from app.modules.training_data.acquisition import training_candidate_service
from app.modules.training_data.schemas import TrainingPurpose, TrainingSourceType

NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "pedrocore"
ADMIN = "alpha-admin"
CORRUPT = "{ isto nao e json valido"


@pytest.fixture(autouse=True)
def restore_registry_injection():
    yield
    dataset_registry_service.set_repository(None)


def _payload() -> dict:
    return {"envelope_version": "pedrocore-integration/v1", "event_id": "evt-1"}


def _enqueue(store, entry_id="out-1", key="k1"):
    return store.enqueue(
        entry_id=entry_id,
        project_id=PROJECT,
        idempotency_key=key,
        payload=_payload(),
        now=NOW,
    )


def _corrupt_outbox(directory: Path, content: str = CORRUPT) -> Path:
    target = directory / "outbox.json"
    target.write_text(content, encoding="utf-8")
    return target


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
        dataset_id="ds-wired",
        display_name="Dataset via factory",
        scope=DatasetScope.PROJECT,
        project_ids=("alpha",),
        training_purpose=TrainingPurpose.EVALUATION_ONLY,
        allowed_source_types=(TrainingSourceType.EVIDENCE_RECORD,),
        created_by=ADMIN,
        created_at=NOW,
    )


# ---------------------------------------------------------------------------
# Outbox — corrupção
# ---------------------------------------------------------------------------


def test_corruption_is_detected_and_never_looks_like_an_empty_queue(tmp_path):
    """Fila vazia e fila ilegível são afirmações diferentes.

    "Não há nada pendente" faz o consumidor seguir em frente. "Não consigo
    ler" precisa parar a camada de entrega.
    """
    _corrupt_outbox(tmp_path)
    store = DurableOutboxStore(tmp_path)
    assert store.degraded is True
    assert store.corruption is not None


def test_corrupted_original_is_preserved_and_copied_to_quarantine(tmp_path):
    """Quarentena é CÓPIA, não movimentação.

    Mover liberaria o caminho original e a escrita seguinte criaria um arquivo
    novo por cima — exatamente o desaparecimento que se quer impedir.
    """
    original = _corrupt_outbox(tmp_path, "{ conteudo corrompido especifico")
    DurableOutboxStore(tmp_path)

    assert original.exists()
    assert original.read_text(encoding="utf-8") == "{ conteudo corrompido especifico"
    copies = list(tmp_path.glob("outbox.json.corrupt-*"))
    assert len(copies) == 1
    assert copies[0].read_text(encoding="utf-8") == original.read_text(encoding="utf-8")


def test_enqueue_on_a_degraded_store_is_refused_and_writes_nothing(tmp_path):
    """Gravar por cima faria sumir evidência pendente que ninguém viu."""
    original = _corrupt_outbox(tmp_path)
    store = DurableOutboxStore(tmp_path)

    with pytest.raises(DurableStorageDegradedError):
        _enqueue(store)
    assert original.read_text(encoding="utf-8") == CORRUPT


def test_dispatch_on_a_degraded_store_does_not_overwrite(tmp_path):
    original = _corrupt_outbox(tmp_path)
    store = DurableOutboxStore(tmp_path)
    assert OutboxDispatcher(store).dispatch_once(lambda _e: None, now=NOW) == []
    assert original.read_text(encoding="utf-8") == CORRUPT


def test_an_invalid_record_is_corruption_not_a_record_to_skip(tmp_path):
    """Descartar a linha ruim faria uma entrega pendente sumir em silêncio.

    É o mesmo defeito do arquivo vazio, só que por registro.
    """
    (tmp_path / "outbox.json").write_text(
        json.dumps([{"entry_id": "out-1", "faltando": "tudo o mais"}]),
        encoding="utf-8",
    )
    store = DurableOutboxStore(tmp_path)
    assert store.degraded is True
    assert "registro 0" in store.corruption.reason


def test_corruption_diagnostics_never_leak_payload_or_secret(tmp_path):
    """Reproduzir o conteúdo o colocaria no log de quem tentava protegê-lo."""
    secret = "SEGREDO-QUE-NAO-PODE-VAZAR-123456"
    (tmp_path / "outbox.json").write_text(
        '[{"entry_id": "out-1", "payload": "api_key=' + secret + '"',
        encoding="utf-8",
    )
    store = DurableOutboxStore(tmp_path)
    rendered = f"{store.corruption} | {store.corruption.reason}"
    assert secret not in rendered
    assert "api_key" not in rendered


def test_a_normal_restart_still_works_after_the_corruption_guard(tmp_path):
    """A proteção não pode custar o caminho feliz."""
    first = DurableOutboxStore(tmp_path)
    _enqueue(first)
    del first

    revived = DurableOutboxStore(tmp_path)
    assert revived.degraded is False
    assert revived.get("out-1") is not None


def test_clear_is_the_explicit_way_out_of_quarantine(tmp_path):
    """Depois de revisar a cópia, `clear()` é o gesto de reconhecer a perda.

    Bloqueá-la deixaria o consumidor sem caminho de recuperação.
    """
    _corrupt_outbox(tmp_path)
    store = DurableOutboxStore(tmp_path)
    assert store.degraded is True

    store.clear()
    assert store.degraded is False
    _enqueue(store)

    assert DurableOutboxStore(tmp_path).get("out-1") is not None
    # A cópia sobrevive à recuperação: é a evidência do que houve.
    assert list(tmp_path.glob("outbox.json.corrupt-*"))


def test_empty_file_is_not_corruption(tmp_path):
    """Arquivo vazio é store legitimamente sem itens.

    A escrita é atômica, então este processo nunca produz um arquivo pela
    metade — tratar vazio como corrupção geraria alarme falso a cada store novo.
    """
    (tmp_path / "outbox.json").write_text("", encoding="utf-8")
    store = DurableOutboxStore(tmp_path)
    assert store.degraded is False
    assert store.all_entries() == []


# ---------------------------------------------------------------------------
# Outbox — wiring de produção
# ---------------------------------------------------------------------------


def test_factory_refuses_when_persistence_is_off(monkeypatch):
    """Outbox que não persiste promete uma garantia de entrega que não tem."""
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "off")
    with pytest.raises(ReportMemoryRepositoryConfigurationError):
        build_outbox_store()
    assert outbox_is_durable() is False


def test_factory_uses_in_memory_only_by_explicit_choice(monkeypatch):
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "memory")
    assert type(build_outbox_store()) is OutboxStore
    assert outbox_is_durable() is False


def test_factory_builds_the_durable_store_for_local_json(tmp_path, monkeypatch):
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "local_json")
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_DIR", str(tmp_path))
    store = build_outbox_store()
    assert isinstance(store, DurableOutboxStore)
    assert outbox_is_durable() is True
    # Subdiretório próprio: limpar a memória operacional não pode levar a fila.
    assert (tmp_path / "outbox").is_dir()


def test_factory_requires_a_directory_for_local_json(monkeypatch):
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "local_json")
    monkeypatch.delenv("PEDROCORE_REPORT_MEMORY_DIR", raising=False)
    with pytest.raises(ReportMemoryRepositoryConfigurationError):
        build_outbox_store()


def test_factory_builds_postgresql_and_requires_a_url(monkeypatch):
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "postgresql")
    monkeypatch.delenv("PEDROCORE_REPORT_MEMORY_DATABASE_URL", raising=False)
    with pytest.raises(ReportMemoryRepositoryConfigurationError):
        build_outbox_store()

    monkeypatch.setenv(
        "PEDROCORE_REPORT_MEMORY_DATABASE_URL", "postgresql://u:p@localhost/db"
    )
    assert isinstance(build_outbox_store(), PostgreSQLOutboxStore)
    assert outbox_is_durable() is True


# ---------------------------------------------------------------------------
# Dataset Registry — corrupção e wiring
# ---------------------------------------------------------------------------


def test_degraded_registry_never_looks_like_an_empty_one(tmp_path):
    """Registry vazio afirma "ninguém decidiu nada" — forte e falso.

    Aceitá-lo permitiria redefinir um dataset já definido e gravar por cima da
    linhagem que tornava um modelo auditável.
    """
    target = tmp_path / "dataset_registry.json"
    target.write_text("{ governanca corrompida", encoding="utf-8")
    repository = LocalJsonDatasetRegistryRepository(tmp_path)

    assert repository.degraded is True
    assert repository.list_definitions() == []
    with pytest.raises(DurableStorageDegradedError):
        repository.save_definition(_definition())

    assert target.read_text(encoding="utf-8") == "{ governanca corrompida"
    assert list(tmp_path.glob("dataset_registry.json.corrupt-*"))


def test_degraded_registry_fabricates_nothing_and_keeps_dataset_not_ready(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("PEDROCORE_TRAINING_DATA_ADMIN_IDS", ADMIN)
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "memory")
    (tmp_path / "dataset_registry.json").write_text("corrompido", encoding="utf-8")
    dataset_registry_service.set_repository(
        LocalJsonDatasetRegistryRepository(tmp_path)
    )

    assert dataset_registry_service.list_definitions() == []
    assert dataset_registry_service.versions("ds-wired") == []
    report = training_candidate_service.readiness(project_id="alpha")
    assert report.readiness == "DATASET_NOT_READY"
    assert report.canonical_dataset_created is False
    assert report.training_started is False


def test_registry_factory_refuses_when_persistence_is_off(monkeypatch):
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "off")
    with pytest.raises(ReportMemoryRepositoryConfigurationError):
        build_dataset_registry_repository()
    assert dataset_registry_is_durable() is False


def test_registry_factory_builds_the_durable_repository(tmp_path, monkeypatch):
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "local_json")
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_DIR", str(tmp_path))
    repository = build_dataset_registry_repository()
    assert isinstance(repository, LocalJsonDatasetRegistryRepository)
    assert dataset_registry_is_durable() is True
    assert (tmp_path / "dataset-registry").is_dir()


def test_registry_factory_refuses_postgresql_instead_of_silently_using_a_file(
    monkeypatch,
):
    """Cair para arquivo faria a governança parecer estar no banco que se copia."""
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "postgresql")
    with pytest.raises(ReportMemoryRepositoryConfigurationError) as error:
        build_dataset_registry_repository()
    assert "PostgreSQL" in str(error.value)


def test_registry_service_has_no_implicit_in_memory_default(monkeypatch):
    """Produção não pode guardar decisões de governança sem ninguém escolher."""
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "off")
    dataset_registry_service.set_repository(None)
    with pytest.raises(ReportMemoryRepositoryConfigurationError):
        dataset_registry_service.get("qualquer-coisa")


def test_registry_service_reaches_the_durable_repository_without_injection(
    tmp_path, monkeypatch
):
    """O caminho REAL de produção: serviço → factory → repositório durável."""
    monkeypatch.setenv("PEDROCORE_TRAINING_DATA_ADMIN_IDS", ADMIN)
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", "local_json")
    monkeypatch.setenv("PEDROCORE_REPORT_MEMORY_DIR", str(tmp_path))
    dataset_registry_service.set_repository(None)

    dataset_registry_service.define(_definition(), _admin())
    assert (tmp_path / "dataset-registry" / "dataset_registry.json").exists()

    # E o restart real: serviço re-resolve e enxerga a decisão gravada.
    dataset_registry_service.set_repository(None)
    assert dataset_registry_service.get("ds-wired") is not None

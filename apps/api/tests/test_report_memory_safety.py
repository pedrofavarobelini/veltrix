"""Report Memory Safety (PEDROCORE-QA-SAFETY-HARDENING-01).

Prova que a memória técnica é opcional, default-off e opt-in por request:
não é treinamento, não injeta contexto no prompt sem flag explícita, não
inventa snapshot e não vaza memória entre projetos. Complementa (sem
duplicar) tests/test_report_memory.py.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.chat.schemas import ChatRequest
from app.modules.project_context.service import project_context_resolver
from app.modules.prompt_builder.schemas import PromptBuildInput
from app.modules.prompt_builder.service import prompt_builder
from app.modules.report_memory.service import (
    FLAG_MEMORY_DIR,
    FLAG_PERSISTENCE,
    report_memory_service,
)
from app.modules.task_router.service import task_router

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_memory(monkeypatch):
    monkeypatch.delenv(FLAG_PERSISTENCE, raising=False)
    monkeypatch.delenv(FLAG_MEMORY_DIR, raising=False)
    report_memory_service.reset()
    yield
    report_memory_service.reset()


@pytest.fixture
def prompt_spy(monkeypatch):
    """Captura o PromptBuildInput real usado pelo pipeline de orquestração."""
    captured: dict = {}
    original = prompt_builder.build

    def spy(data: PromptBuildInput):
        captured["memory_block"] = data.memory_block
        return original(data)

    monkeypatch.setattr(prompt_builder, "build", spy)
    return captured


def _report(**overrides) -> dict:
    base = {
        "project_id": "pedrocore",
        "report_type": "qa_run",
        "status": "passed",
        "summary": "Execução concluída com sucesso.",
        "next_steps": ["Rodar suíte full"],
        "created_at": "2026-07-09T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def test_chat_request_defaults_are_all_safe():
    payload = ChatRequest(message="teste")

    assert payload.allow_real_provider is False
    assert payload.allow_local_model is False
    assert payload.context_from_memory is False


def test_invalid_persistence_flag_value_behaves_as_off(monkeypatch):
    # Valor errado na flag (ex.: "true" em vez de "memory") não pode ligar nada.
    for invalid in ["true", "on", "enabled", "1", "yes"]:
        monkeypatch.setenv(FLAG_PERSISTENCE, invalid)

        response = client.post("/api/reports/ingest", json=_report())
        data = response.json()

        assert data["status"] == "disabled", f"valor: {invalid}"
        assert data["stored"] is False, f"valor: {invalid}"


def test_summary_returns_null_snapshot_without_data(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")

    response = client.get("/api/project-memory/projeto-sem-dados/summary")
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["snapshot"] is None
    codes = [w["code"] for w in data["warnings"]]
    assert "REPORT_MEMORY_EMPTY" in codes


def test_memory_not_injected_into_prompt_without_flag(monkeypatch, prompt_spy):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    client.post("/api/reports/ingest", json=_report())

    response = client.post(
        "/api/orchestrate",
        json={"message": "Status?", "provider": "mock", "task_type": "project_status"},
    )
    data = response.json()

    assert response.status_code == 200
    assert prompt_spy["memory_block"] is None
    assert data["memory_used"] is False
    assert "REPORT_MEMORY_USED" not in data["warning_codes"]


def test_memory_injected_only_with_explicit_flag(monkeypatch, prompt_spy):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    client.post("/api/reports/ingest", json=_report())

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Status?",
            "provider": "mock",
            "task_type": "project_status",
            "context_from_memory": True,
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["memory_used"] is True
    assert prompt_spy["memory_block"] is not None
    # O bloco injetado carrega o aviso explícito de não-treinamento.
    assert "memória técnica não é treinamento" in prompt_spy["memory_block"]


def test_context_block_never_consulted_without_flag(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    client.post("/api/reports/ingest", json=_report())

    calls: list[str] = []
    original = report_memory_service.context_block

    def spy(project_id: str):
        calls.append(project_id)
        return original(project_id)

    monkeypatch.setattr(report_memory_service, "context_block", spy)

    response = client.post(
        "/api/orchestrate",
        json={"message": "Status?", "provider": "mock", "task_type": "project_status"},
    )

    assert response.status_code == 200
    assert calls == []


def test_memory_does_not_leak_between_projects_via_orchestrate(
    monkeypatch, prompt_spy
):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    # Memória existe apenas para o projeto finguard.
    client.post("/api/reports/ingest", json=_report(project_id="finguard"))

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Status?",
            "provider": "mock",
            "task_type": "project_status",
            "origin_system": "pedrocore",
            "context_from_memory": True,
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["memory_used"] is False
    assert prompt_spy["memory_block"] is None
    assert "REPORT_MEMORY_EMPTY" in data["warning_codes"]


def test_ingest_invalid_payload_fails_controlled():
    response = client.post(
        "/api/reports/ingest",
        json={
            "project_id": "x",
            "report_type": "qa_run",
            "status": "passed",
            "summary": "ok",
            "next_steps": {"nao": "é lista"},
        },
    )

    assert response.status_code == 422
    assert "detail" in response.json()
    assert "Traceback" not in response.text


def test_prompt_builder_memory_section_only_appears_with_block():
    strategy = task_router.resolve("project_status")
    project = project_context_resolver.resolve("pedrocore")

    def build(memory_block):
        return prompt_builder.build(
            PromptBuildInput(
                message="Status?",
                mode="tecnico",
                system_prompt=None,
                strategy=strategy,
                project=project,
                origin_system="pedrocore",
                context=None,
                metadata=None,
                artifacts_text_block=None,
                intelligence_instructions=[],
                memory_block=memory_block,
            )
        )

    without = build(None)
    with_block = build("last_known_status: passed")

    assert "[Memória técnica]" not in without.enriched_system_prompt
    assert "[Memória técnica]" in with_block.enriched_system_prompt
    assert "last_known_status: passed" in with_block.enriched_system_prompt

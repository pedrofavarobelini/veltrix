"""Eval Harness estendido (PEDROCORE-QA-SAFETY-HARDENING-01).

Prova que o harness é determinístico, usa apenas providers seguros e cobre
os casos negativos adicionados nesta frente (provider inválido, task_type
desconhecido, local_qa determinístico). Nenhum caso usa rede ou chave.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.eval_harness.fixtures import DEFAULT_EVAL_CASES
from app.modules.eval_harness.service import eval_harness_service
from app.modules.report_memory.service import FLAG_PERSISTENCE

client = TestClient(app)

SAFE_PROVIDERS = {"mock", "local_qa", "local_model", "provider_inexistente"}

# Providers reais só aparecem em fixtures que PROVAM o bloqueio do safe mode
# (allow_real_provider=False garante que nunca são executados).
REAL_PROVIDERS = {"gemini", "openai", "claude", "deepseek", "grok"}

HARDENING_CASE_IDS = {
    "invalid-provider-falls-back-safely",
    "unknown-task-type-warned-not-crashed",
    "local-qa-deterministic-assistant",
}


@pytest.fixture(autouse=True)
def default_env(monkeypatch):
    # Fixtures padrão assumem ambiente default (memória/local model OFF).
    monkeypatch.delenv(FLAG_PERSISTENCE, raising=False)
    monkeypatch.delenv("PEDROCORE_ENABLE_LOCAL_MODEL", raising=False)
    yield


def test_hardening_cases_are_registered():
    case_ids = [case.case_id for case in DEFAULT_EVAL_CASES]

    assert len(case_ids) == len(set(case_ids)), "case_id duplicado nas fixtures"
    assert HARDENING_CASE_IDS <= set(case_ids)


def test_all_default_cases_use_only_safe_providers():
    for case in DEFAULT_EVAL_CASES:
        assert case.allow_real_provider is False, case.case_id
        assert case.provider in SAFE_PROVIDERS | REAL_PROVIDERS, (
            f"caso '{case.case_id}' usa provider desconhecido: '{case.provider}'"
        )
        if case.provider in REAL_PROVIDERS:
            # Caso com provider real só é aceitável para provar o bloqueio.
            assert "PROVIDER_REAL_BLOCKED" in case.expected_warnings, (
                f"caso '{case.case_id}' usa provider real sem provar o bloqueio"
            )


def test_hardening_cases_pass():
    selected = [c for c in DEFAULT_EVAL_CASES if c.case_id in HARDENING_CASE_IDS]
    assert len(selected) == len(HARDENING_CASE_IDS)

    result = eval_harness_service.run_sync(selected)

    failed = [(c.case_id, c.failures) for c in result.cases if not c.passed]
    assert failed == []


def test_harness_is_deterministic_across_runs():
    first = eval_harness_service.run_sync()
    second = eval_harness_service.run_sync()

    def signature(run):
        return [(c.case_id, c.passed, c.provider_used, c.task_type) for c in run.cases]

    assert signature(first) == signature(second)
    assert first.failed == 0
    assert second.failed == 0


def test_harness_never_calls_real_provider(real_provider_guard):
    if real_provider_guard is None:
        pytest.skip("guard desativado por PEDROCORE_RUN_REAL_PROVIDER_TESTS=true")

    result = eval_harness_service.run_sync()

    assert result.failed == 0
    assert real_provider_guard == []


def test_local_qa_answer_is_deterministic_at_api_level():
    payload = {
        "message": "Como está o ecossistema?",
        "provider": "local_qa",
        "task_type": "assistant_chat",
    }

    first = client.post("/api/orchestrate", json=payload).json()
    second = client.post("/api/orchestrate", json=payload).json()

    assert first["answer"] == second["answer"]
    assert first["provider_used"] == "local_qa"
    assert first["model"] == "local-qa-v1"

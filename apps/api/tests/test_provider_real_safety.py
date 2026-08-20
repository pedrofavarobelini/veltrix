"""Provider Real Safety (PEDROCORE-QA-SAFETY-HARDENING-01).

Prova que provider real (Gemini/OpenAI/Claude/DeepSeek/Grok) não roda por
acidente: default-off, bloqueio por safe mode, fallback controlado, bypass
por payload aninhado inócuo e guard estrutural de testes (conftest.py).
Nenhum teste aqui usa rede ou chave externa.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.eval_harness.service import eval_harness_service
from app.modules.providers.registry import provider_registry

client = TestClient(app)

REAL_PROVIDERS = ["gemini", "openai", "claude", "deepseek", "grok"]

CLEAN_QA_EVIDENCE = "All tests passed. 0 failed. Build successful."


def test_allow_real_provider_absent_behaves_as_false():
    response = client.post(
        "/api/orchestrate",
        json={"message": "Teste sem flag", "provider": "gemini"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["allow_real_provider"] is False
    assert data["safe_mode_blocked"] is True
    assert data["fallback_used"] is True
    assert data["provider_used"] == "mock"
    assert data["error_code"] == "PROVIDER_REAL_BLOCKED"


def test_all_real_providers_blocked_by_default_in_orchestrate():
    for provider in REAL_PROVIDERS:
        response = client.post(
            "/api/orchestrate",
            json={"message": "Teste", "provider": provider},
        )
        data = response.json()

        assert response.status_code == 200, f"provider: {provider}"
        assert data["safe_mode_blocked"] is True, f"provider: {provider}"
        assert data["provider_used"] == "mock", f"provider: {provider}"
        assert "PROVIDER_REAL_BLOCKED" in data["warning_codes"], (
            f"provider: {provider}"
        )


def test_blocked_real_provider_returns_controlled_safe_response():
    response = client.post(
        "/api/orchestrate",
        json={"message": "Teste", "provider": "claude"},
    )
    data = response.json()

    assert response.status_code == 200
    # Task de baixa criticidade: bloqueio vira fallback seguro, não erro 5xx.
    assert data["status"] == "ok"
    assert data["answer"]
    assert data["blocked_reason"] is None
    assert "Traceback" not in response.text


def test_blocked_real_provider_in_critical_task_blocks_release():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Pode liberar?",
            "provider": "gemini",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "content": CLEAN_QA_EVIDENCE}],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "blocked"
    assert data["safe_mode_blocked"] is True
    assert data["release_gate"]["can_advance"] is False


def test_invalid_provider_fails_standardized():
    response = client.post(
        "/api/orchestrate",
        json={"message": "Teste", "provider": "provider_inexistente"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["provider_requested"] == "provider_inexistente"
    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    # /api/orchestrate nunca expõe erro técnico bruto publicamente (só
    # `error_code`, um código estável); a resposta conversacional também
    # não pode citar o nome do provider inválido nem debug/traceback.
    assert "provider_inexistente" not in data["answer"]
    assert "Traceback" not in response.text
    assert "Traceback" not in data["answer"]


# Substrings tecnicas/debug que NUNCA podem aparecer na resposta conversacional
# de um fallback (contrato de UX exigido pelo consumidor FinGuard).
FORBIDDEN_ANSWER_SUBSTRINGS = [
    "MockProvider",
    "mock-v1",
    "Modelo solicitado",
    "A V2 possui arquitetura multi-provider",
    "Mensagem recebida",
    "PROVIDER_REAL_BLOCKED",
    "PROVIDER_REAL_UNAVAILABLE",
    "Fallback acionado",
    "Erro técnico",
    "Traceback",
]


def test_fallback_answer_never_leaks_technical_debug_text():
    """PEDROCORE x FinGuard: quando o provider solicitado falha, nao esta
    configurado ou e bloqueado por safe mode, a resposta conversacional
    (`answer`) deve ser sempre segura/conservadora, nunca um eco tecnico/
    debug do erro interno. Nenhum destes dois gatilhos toca em provider
    real (o segundo e bloqueado por allow_real_provider=false antes de
    qualquer chamada), entao nao precisa do guard/marker de provider real."""
    scenarios = [
        {"message": "Teste", "provider": "provider_inexistente"},
        {"message": "Teste", "provider": "gemini"},
    ]

    for payload in scenarios:
        response = client.post("/api/orchestrate", json=payload)
        data = response.json()

        assert response.status_code == 200, payload
        assert data["fallback_used"] is True, payload
        assert data["provider_used"] == "mock", payload
        for forbidden in FORBIDDEN_ANSWER_SUBSTRINGS:
            assert forbidden not in data["answer"], (payload, forbidden, data["answer"])


@pytest.mark.expected_guarded_call
def test_fallback_answer_never_leaks_technical_debug_text_for_auto_real_provider(
    monkeypatch, real_provider_guard
):
    """Mesma garantia acima, cobrindo o gatilho provider=auto com
    allow_real_provider=true e uma chave Gemini falsa configurada — o guard
    estrutural do conftest intercepta a chamada antes de qualquer rede real,
    e o fallback resultante ainda assim nao pode vazar texto tecnico."""
    if real_provider_guard is None:
        pytest.skip("guard desativado por PEDROCORE_RUN_REAL_PROVIDER_TESTS=true")

    monkeypatch.setattr(settings, "gemini_api_key", "test-fake-key-never-leak")

    response = client.post(
        "/api/orchestrate",
        json={"message": "Teste", "provider": "auto", "allow_real_provider": True},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["fallback_used"] is True
    assert data["provider_used"] == "mock"
    assert real_provider_guard == ["gemini"]
    for forbidden in FORBIDDEN_ANSWER_SUBSTRINGS:
        assert forbidden not in data["answer"], (forbidden, data["answer"])


def test_nested_payload_cannot_bypass_allow_real_provider():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Teste de bypass",
            "provider": "gemini",
            "context": {"allow_real_provider": True},
            "metadata": {"allow_real_provider": "true"},
            # Campo extra no topo é ignorado pelo schema (extra ignore).
            "Allow_Real_Provider": True,
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["allow_real_provider"] is False
    assert data["safe_mode_blocked"] is True
    assert data["provider_used"] == "mock"


def test_mock_provider_works_without_api_key():
    response = client.post(
        "/api/orchestrate",
        json={"message": "Teste", "provider": "mock"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is False
    assert data["safe_mode_blocked"] is False
    assert data["answer"]


def test_local_qa_works_without_api_key_and_stays_release_gate_provider():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Pode liberar?",
            "provider": "local_qa",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "content": CLEAN_QA_EVIDENCE}],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["provider_used"] == "local_qa"
    assert data["model"] == "local-qa-v1"
    assert data["safe_mode_blocked"] is False
    assert data["release_gate"]["can_advance"] is True


def test_real_providers_report_real_provider_true_in_registry():
    listed = {p["name"]: p for p in provider_registry.list_providers()}

    for provider in REAL_PROVIDERS:
        assert listed[provider]["real_provider"] is True, f"provider: {provider}"
    assert listed["mock"]["real_provider"] is False
    assert listed["local_model"]["real_provider"] is False


@pytest.mark.expected_guarded_call
def test_guard_fires_if_real_provider_is_invoked_directly(real_provider_guard):
    if real_provider_guard is None:
        pytest.skip("guard desativado por PEDROCORE_RUN_REAL_PROVIDER_TESTS=true")

    provider = provider_registry.get("gemini")

    with pytest.raises(RuntimeError, match="REAL_PROVIDER_CALL_BLOCKED_BY_TEST_GUARD"):
        asyncio.run(provider.generate_response(message="Teste", mode="tecnico"))

    assert real_provider_guard == ["gemini"]


@pytest.mark.expected_guarded_call
def test_even_authorized_flag_cannot_reach_network_in_tests(
    monkeypatch, real_provider_guard
):
    """allow_real_provider=true em teste bate no guard e cai em fallback mock."""
    if real_provider_guard is None:
        pytest.skip("guard desativado por PEDROCORE_RUN_REAL_PROVIDER_TESTS=true")

    # A autorização só alcança o adapter se existir configuração. Uma chave
    # sintética garante que este teste exercita o guard, nunca a rede.
    monkeypatch.setattr(settings, "gemini_api_key", "test-fake-key-guard-proof")

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Teste",
            "provider": "gemini",
            "allow_real_provider": True,
        },
    )
    data = response.json()

    assert response.status_code == 200
    # A prova de que o guard disparou de verdade é `real_provider_guard`
    # (populado pelo próprio conftest ao interceptar a chamada), não o
    # texto da resposta: `/api/orchestrate` não expõe erro técnico bruto
    # publicamente, e a resposta conversacional nunca deve citar o guard.
    assert real_provider_guard == ["gemini"]
    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert "REAL_PROVIDER_CALL_BLOCKED_BY_TEST_GUARD" not in (data["answer"] or "")


def test_eval_harness_never_invokes_real_provider(real_provider_guard, monkeypatch):
    if real_provider_guard is None:
        pytest.skip("guard desativado por PEDROCORE_RUN_REAL_PROVIDER_TESTS=true")

    # Fixtures padrão assumem ambiente default (memória/local model OFF).
    monkeypatch.delenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", raising=False)
    monkeypatch.delenv("PEDROCORE_ENABLE_LOCAL_MODEL", raising=False)

    result = eval_harness_service.run_sync()

    assert result.failed == 0
    assert real_provider_guard == []

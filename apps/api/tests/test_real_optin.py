"""Testes opt-in de recursos reais (IMPLEMENT-05A).

Todos são SKIPPED no pytest padrão. Cada um exige uma flag de ambiente
explícita e, quando executado, exige também a configuração real correspondente
(chaves, dependências instaladas, serviços locais). Nenhum deles roda em CI ou
suíte padrão por decisão de segurança.
"""

import os

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.real_features import service as real_features
from tests.real_flags import optin

client = TestClient(app)


@optin(real_features.FLAG_RUN_REAL_INTEGRATION_TESTS)
def test_real_integration_smoke():
    # Integração real ponta-a-ponta: exige ambiente configurado pelo humano.
    response = client.post(
        "/api/orchestrate",
        json={"message": "Smoke de integração real", "provider": "local_qa"},
    )
    assert response.status_code == 200


@optin(real_features.FLAG_RUN_REAL_FINGUARD_TESTS)
def test_real_finguard_contract_roundtrip():
    # Simula o payload que o cliente HTTP real do FinGuard enviará.
    # Só roda com flag explícita; nunca acessa o repositório do FinGuard.
    response = client.post(
        "/api/orchestrate",
        json={
            "origin_system": "finguard",
            "task_type": "qa_report_analysis",
            "message": "Round-trip real do contrato FinGuard.",
            "provider": "local_qa",
            "artifacts": [{"type": "text", "content": "125 passed, 0 failed."}],
        },
    )
    assert response.status_code == 200
    assert response.json()["qa"]["analysis_source"] == "local_text_heuristic"


@optin(real_features.FLAG_RUN_REAL_PROVIDER_TESTS)
def test_real_provider_authorized_call():
    # Chama provider real com autorização explícita. Gera custo/chamada externa.
    response = client.post(
        "/api/chat",
        json={
            "message": "Responda apenas: ok",
            "provider": "gemini",
            "allow_real_provider": True,
        },
    )
    assert response.status_code == 200


@optin(real_features.FLAG_RUN_REAL_GEMINI_TESTS)
def test_real_gemini_orchestrate_authorized_call():
    # Chama Gemini real via /api/orchestrate apenas com opt-in explicito.
    # Nunca roda no pytest padrao e nunca imprime chave.
    assert settings.gemini_api_key, "GEMINI_API_KEY precisa estar configurada no ambiente PedroCore"
    response = client.post(
        "/api/orchestrate",
        json={
            "origin_system": "finguard",
            "project_id": "finguard",
            "task_type": "finance_advice",
            "message": "Responda de forma conservadora em uma frase.",
            "provider": "gemini",
            "allow_real_provider": True,
            "allow_local_model": False,
            "context_from_memory": False,
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["provider_used"] == "gemini"
    assert settings.gemini_api_key not in str(data)


@optin(real_features.FLAG_RUN_REAL_OCR_TESTS)
def test_real_ocr_local_execution():
    # Executa OCR local real: exige PEDROCORE_OCR_ENABLED=true e pytesseract instalado.
    assert os.environ.get(real_features.FLAG_OCR_ENABLED, "").lower() == "true"


@optin(real_features.FLAG_RUN_REAL_MULTIMODAL_TESTS)
def test_real_multimodal_visual_qa():
    # QA visual real com provider multimodal: exige todas as flags + autorização.
    assert real_features.multimodal_enabled() is True
    assert real_features.visual_qa_enabled() is True


@optin(real_features.FLAG_RUN_REAL_PLAYWRIGHT_TESTS)
def test_real_playwright_readonly_exploration():
    # Exploração read-only real: exige Playwright instalado + allowlist configurada.
    assert real_features.playwright_enabled() is True
    assert real_features.playwright_allowed_base_urls() != []

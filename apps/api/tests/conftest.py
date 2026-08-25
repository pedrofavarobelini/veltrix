"""Guard global de segurança dos testes (PEDROCORE-QA-SAFETY-HARDENING-01).

Bloqueia estruturalmente qualquer invocação de provider real (Gemini, OpenAI,
Claude, DeepSeek, Grok) durante o pytest padrão:

  - cada `generate_response` real é substituído por um guard que registra a
    chamada e levanta RuntimeError, sem nunca alcançar SDK ou rede;
  - ao final de cada teste, o guard falha o teste se algum provider real foi
    invocado (mesmo que o pipeline tenha absorvido o erro via fallback);
  - o guard respeita os opt-ins existentes: com
    PEDROCORE_RUN_REAL_PROVIDER_TESTS=true ou PEDROCORE_RUN_REAL_GEMINI_TESTS=true
    ele se desativa por completo, preservando os testes reais de
    tests/test_real_optin.py.

Testes que disparam o guard de propósito devem usar o marker
`@pytest.mark.expected_guarded_call`.
"""

import pytest

from app.modules.providers.claude_provider import ClaudeProvider
from app.modules.providers.deepseek_provider import DeepSeekProvider
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.providers.grok_provider import GrokProvider
from app.modules.providers.openai_provider import OpenAIProvider
from app.modules.real_features import service as real_features
from tests.real_flags import flag_is_true

REAL_PROVIDER_CLASSES = [
    GeminiProvider,
    OpenAIProvider,
    ClaudeProvider,
    DeepSeekProvider,
    GrokProvider,
]

GUARD_MESSAGE = (
    "REAL_PROVIDER_CALL_BLOCKED_BY_TEST_GUARD: provider real '{name}' foi "
    "invocado durante o pytest padrão. Nenhuma chamada externa foi feita. "
    "Para testes reais autorizados, use PEDROCORE_RUN_REAL_PROVIDER_TESTS=true."
)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "expected_guarded_call: teste que dispara o guard de provider real "
        "de propósito (não falha no teardown).",
    )


@pytest.fixture(autouse=True)
def real_provider_guard(monkeypatch, request):
    """Kill-switch de provider real: registra e bloqueia toda invocação.

    Retorna a lista de nomes de providers reais invocados no teste (vazia no
    caminho seguro). Retorna None quando o opt-in real está ativo.
    """
    if flag_is_true(real_features.FLAG_RUN_REAL_PROVIDER_TESTS) or flag_is_true(
        real_features.FLAG_RUN_REAL_GEMINI_TESTS
    ) or flag_is_true(real_features.FLAG_RUN_REAL_ELYRA_TESTS):
        yield None
        return

    calls: list[str] = []

    def make_guard(provider_name: str):
        # `**kwargs` absorve os parâmetros de geração que o pipeline passa a
        # adapters com `supports_generation_budget` (output_budget,
        # transport_timeout_ms). O guard continua bloqueando ANTES do SDK.
        async def guard(self, message, mode, model=None, system_prompt=None, **kwargs):
            calls.append(provider_name)
            raise RuntimeError(GUARD_MESSAGE.format(name=provider_name))

        return guard

    for cls in REAL_PROVIDER_CLASSES:
        monkeypatch.setattr(cls, "generate_response", make_guard(cls.name))

    yield calls

    if request.node.get_closest_marker("expected_guarded_call"):
        return
    assert calls == [], (
        "Provider real invocado sem autorização durante o teste: "
        f"{calls}. A chamada foi bloqueada pelo guard (nenhuma rede real), "
        "mas o teste não pode depender de provider real."
    )

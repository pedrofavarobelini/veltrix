import importlib.util

import pytest

from app.modules.exploration.playwright_adapter import playwright_readonly_adapter

FLAG_ENABLED = "PEDROCORE_EXPLORATION_PLAYWRIGHT_ENABLED"
FLAG_URLS = "PEDROCORE_EXPLORATION_ALLOWED_BASE_URLS"

playwright_installed = importlib.util.find_spec("playwright") is not None


def test_playwright_disabled_blocks(monkeypatch):
    monkeypatch.delenv(FLAG_ENABLED, raising=False)

    result = playwright_readonly_adapter.explore("http://localhost:5173")

    assert result.executed is False
    assert "PLAYWRIGHT_NOT_ENABLED" in result.warning_codes


def test_url_outside_allowlist_blocks(monkeypatch):
    monkeypatch.setenv(FLAG_ENABLED, "true")
    monkeypatch.setenv(FLAG_URLS, "http://localhost:5173")

    result = playwright_readonly_adapter.explore("https://example.com")

    assert result.executed is False
    assert "PLAYWRIGHT_BASE_URL_NOT_ALLOWED" in result.warning_codes


def test_finguard_urls_always_blocked(monkeypatch):
    monkeypatch.setenv(FLAG_ENABLED, "true")
    monkeypatch.setenv(FLAG_URLS, "http://localhost:9999")

    result = playwright_readonly_adapter.explore("http://localhost:9999/finguard/app")

    assert result.executed is False
    assert "PLAYWRIGHT_BASE_URL_NOT_ALLOWED" in result.warning_codes


def test_empty_allowlist_blocks_everything(monkeypatch):
    monkeypatch.setenv(FLAG_ENABLED, "true")
    monkeypatch.delenv(FLAG_URLS, raising=False)

    result = playwright_readonly_adapter.explore("http://localhost:5173")

    assert result.executed is False
    assert "PLAYWRIGHT_BASE_URL_NOT_ALLOWED" in result.warning_codes


@pytest.mark.skipif(
    playwright_installed,
    reason="playwright instalado neste ambiente; cenário de indisponibilidade não se aplica",
)
def test_dependency_unavailable_is_handled(monkeypatch):
    monkeypatch.setenv(FLAG_ENABLED, "true")
    monkeypatch.setenv(FLAG_URLS, "http://localhost:5173")

    result = playwright_readonly_adapter.explore("http://localhost:5173")

    assert result.executed is False
    assert "PLAYWRIGHT_DEPENDENCY_UNAVAILABLE" in result.warning_codes


def test_interactive_actions_always_blocked(monkeypatch):
    # Mesmo com tudo habilitado, clique/digitação/submissão/login são bloqueados.
    monkeypatch.setenv(FLAG_ENABLED, "true")
    monkeypatch.setenv(FLAG_URLS, "http://localhost:5173")

    for action in (
        playwright_readonly_adapter.click,
        playwright_readonly_adapter.type_text,
        playwright_readonly_adapter.submit,
        playwright_readonly_adapter.login,
    ):
        result = action("qualquer-alvo")
        assert result.executed is False
        assert "PLAYWRIGHT_ACTION_BLOCKED" in result.warning_codes


def test_result_never_advances_release():
    result = playwright_readonly_adapter.explore("http://localhost:5173")

    assert result.can_advance is False
    assert result.requires_human_review is True


def test_standard_pytest_never_opens_browser(monkeypatch):
    # Garantia estrutural: no pytest padrão a flag está off e a dependência não
    # está instalada; qualquer chamada retorna bloqueio sem abrir navegador.
    monkeypatch.delenv(FLAG_ENABLED, raising=False)

    result = playwright_readonly_adapter.explore("http://localhost:5173")

    assert result.attempted is False
    assert result.executed is False

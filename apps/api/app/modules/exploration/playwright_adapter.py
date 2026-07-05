import importlib.util

from pydantic import BaseModel, Field

from app.modules.contracts import codes
from app.modules.real_features import service as real_features

# Adapter Playwright read-only opt-in (IMPLEMENT-05F).
#
# Regras inegociáveis:
#   - desabilitado por padrão (PEDROCORE_EXPLORATION_PLAYWRIGHT_ENABLED=false);
#   - só navega em base URLs da allowlist (PEDROCORE_EXPLORATION_ALLOWED_BASE_URLS);
#   - somente leitura: coleta título/status/links visíveis; NUNCA clica, digita,
#     submete formulário, faz login ou altera dados;
#   - nunca acessa URLs do FinGuard por padrão;
#   - nunca roda no pytest padrão (flag off + dependência não instalada);
#   - dependência NÃO é instalada por este projeto.

PLAYWRIGHT_NOT_ENABLED_WARNING = (
    "Playwright desabilitado (PEDROCORE_EXPLORATION_PLAYWRIGHT_ENABLED=false); "
    "nenhuma navegação executada."
)
PLAYWRIGHT_URL_NOT_ALLOWED_WARNING = (
    "Base URL fora da allowlist de exploração; navegação bloqueada."
)
PLAYWRIGHT_DEPENDENCY_WARNING = (
    "Playwright não instalado; navegação não executada. "
    "Instalação requer aprovação explícita."
)
PLAYWRIGHT_READ_ONLY_WARNING = (
    "Exploração Playwright em modo somente leitura: sem clique, sem digitação, "
    "sem submissão, sem login e sem alteração de dados."
)
PLAYWRIGHT_ACTION_BLOCKED_WARNING = (
    "Ação interativa (clique/digitação/submissão) é bloqueada pelo adapter read-only."
)
PLAYWRIGHT_HUMAN_REVIEW_WARNING = (
    "Resultado de exploração exige revisão humana; não é evidência de release."
)


class PlaywrightExplorationResult(BaseModel):
    attempted: bool = False
    executed: bool = False
    base_url: str | None = None
    page_title: str | None = None
    status_code: int | None = None
    visible_links: list[str] = Field(default_factory=list)
    read_only: bool = True
    can_advance: bool = False
    requires_human_review: bool = True
    warnings: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)


def _blocked(code: str, message: str, base_url: str | None = None) -> PlaywrightExplorationResult:
    return PlaywrightExplorationResult(
        attempted=False,
        executed=False,
        base_url=base_url,
        warnings=[message],
        warning_codes=[code],
    )


def dependency_available() -> bool:
    return importlib.util.find_spec("playwright") is not None


class PlaywrightReadOnlyAdapter:
    def explore(self, base_url: str) -> PlaywrightExplorationResult:
        if not real_features.playwright_enabled():
            return _blocked(
                codes.PLAYWRIGHT_NOT_ENABLED, PLAYWRIGHT_NOT_ENABLED_WARNING, base_url
            )

        normalized = (base_url or "").strip().rstrip("/")
        allowed = real_features.playwright_allowed_base_urls()
        if (
            not normalized
            or "finguard" in normalized.lower()
            or not any(
                normalized == entry or normalized.startswith(entry + "/")
                for entry in allowed
            )
        ):
            return _blocked(
                codes.PLAYWRIGHT_BASE_URL_NOT_ALLOWED,
                PLAYWRIGHT_URL_NOT_ALLOWED_WARNING,
                base_url,
            )

        if not dependency_available():
            return _blocked(
                codes.PLAYWRIGHT_DEPENDENCY_UNAVAILABLE,
                PLAYWRIGHT_DEPENDENCY_WARNING,
                base_url,
            )

        # Caminho real: só alcançável com flag ligada + allowlist + dependência
        # instalada pelo humano. Nunca roda no pytest padrão.
        from playwright.sync_api import sync_playwright  # noqa: PLC0415 (opt-in)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                response = page.goto(normalized, wait_until="domcontentloaded")
                title = page.title()
                links = [
                    href
                    for href in page.eval_on_selector_all(
                        "a[href]", "els => els.map(e => e.getAttribute('href'))"
                    )
                    if href
                ][:50]
                status_code = response.status if response is not None else None
            finally:
                browser.close()

        return PlaywrightExplorationResult(
            attempted=True,
            executed=True,
            base_url=normalized,
            page_title=title,
            status_code=status_code,
            visible_links=links,
            read_only=True,
            can_advance=False,
            requires_human_review=True,
            warnings=[
                PLAYWRIGHT_READ_ONLY_WARNING,
                PLAYWRIGHT_HUMAN_REVIEW_WARNING,
            ],
            warning_codes=[
                codes.PLAYWRIGHT_READ_ONLY_MODE,
                codes.PLAYWRIGHT_REQUIRES_HUMAN_REVIEW,
            ],
        )

    # Ações interativas: sempre bloqueadas, independentemente de flags.
    def click(self, *args, **kwargs) -> PlaywrightExplorationResult:
        return _blocked(codes.PLAYWRIGHT_ACTION_BLOCKED, PLAYWRIGHT_ACTION_BLOCKED_WARNING)

    def type_text(self, *args, **kwargs) -> PlaywrightExplorationResult:
        return _blocked(codes.PLAYWRIGHT_ACTION_BLOCKED, PLAYWRIGHT_ACTION_BLOCKED_WARNING)

    def submit(self, *args, **kwargs) -> PlaywrightExplorationResult:
        return _blocked(codes.PLAYWRIGHT_ACTION_BLOCKED, PLAYWRIGHT_ACTION_BLOCKED_WARNING)

    def login(self, *args, **kwargs) -> PlaywrightExplorationResult:
        return _blocked(codes.PLAYWRIGHT_ACTION_BLOCKED, PLAYWRIGHT_ACTION_BLOCKED_WARNING)


playwright_readonly_adapter = PlaywrightReadOnlyAdapter()

import os

# Guard central de recursos reais (PEDROCORE-IMPLEMENT-05A).
#
# Todo recurso real (OCR, multimodal, Playwright, integração FinGuard real,
# provider real em teste) é OPT-IN: desabilitado por padrão, ligado apenas por
# flag de ambiente explícita. Nenhuma flag é lida de .env real por este módulo —
# somente do ambiente do processo (os.environ), o que permite testes com
# monkeypatch sem tocar em arquivos.

FLAG_OCR_ENABLED = "PEDROCORE_OCR_ENABLED"
FLAG_OCR_ENGINE = "PEDROCORE_OCR_ENGINE"
FLAG_MULTIMODAL_ENABLED = "PEDROCORE_MULTIMODAL_PROVIDER_ENABLED"
FLAG_VISUAL_QA_ENABLED = "PEDROCORE_VISUAL_QA_ENABLED"
FLAG_PLAYWRIGHT_ENABLED = "PEDROCORE_EXPLORATION_PLAYWRIGHT_ENABLED"
FLAG_PLAYWRIGHT_ALLOWED_BASE_URLS = "PEDROCORE_EXPLORATION_ALLOWED_BASE_URLS"
FLAG_ENFORCE_PROJECT_POLICY = "PEDROCORE_ENFORCE_PROJECT_POLICY"
FLAG_REQUIRE_HUMAN_REVIEW_REAL = (
    "PEDROCORE_RELEASE_REQUIRE_HUMAN_REVIEW_FOR_REAL_FEATURES"
)

# Flags de testes opt-in (nunca ligadas por padrão).
FLAG_RUN_REAL_INTEGRATION_TESTS = "PEDROCORE_RUN_REAL_INTEGRATION_TESTS"
FLAG_RUN_REAL_FINGUARD_TESTS = "PEDROCORE_RUN_REAL_FINGUARD_TESTS"
FLAG_RUN_REAL_PROVIDER_TESTS = "PEDROCORE_RUN_REAL_PROVIDER_TESTS"
FLAG_RUN_REAL_GEMINI_TESTS = "PEDROCORE_RUN_REAL_GEMINI_TESTS"
FLAG_RUN_REAL_ELYRA_TESTS = "PEDROCORE_RUN_REAL_ELYRA_TESTS"
FLAG_RUN_REAL_PLAYWRIGHT_TESTS = "PEDROCORE_RUN_REAL_PLAYWRIGHT_TESTS"
FLAG_RUN_REAL_OCR_TESTS = "PEDROCORE_RUN_REAL_OCR_TESTS"
FLAG_RUN_REAL_MULTIMODAL_TESTS = "PEDROCORE_RUN_REAL_MULTIMODAL_TESTS"


def flag_enabled(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw == "true"


def ocr_enabled() -> bool:
    return flag_enabled(FLAG_OCR_ENABLED)


def ocr_engine() -> str:
    return (os.environ.get(FLAG_OCR_ENGINE) or "local").strip().lower()


def multimodal_enabled() -> bool:
    return flag_enabled(FLAG_MULTIMODAL_ENABLED)


def visual_qa_enabled() -> bool:
    return flag_enabled(FLAG_VISUAL_QA_ENABLED)


def playwright_enabled() -> bool:
    return flag_enabled(FLAG_PLAYWRIGHT_ENABLED)


def playwright_allowed_base_urls() -> list[str]:
    raw = (os.environ.get(FLAG_PLAYWRIGHT_ALLOWED_BASE_URLS) or "").strip()
    return [part.strip().rstrip("/") for part in raw.split(",") if part.strip()]


def enforce_project_policy() -> bool:
    # Enforcement de policy é a única flag com default TRUE: segurança por padrão.
    return flag_enabled(FLAG_ENFORCE_PROJECT_POLICY, default=True)


def require_human_review_for_real_features() -> bool:
    # Também default TRUE: recurso real nunca decide sozinho.
    return flag_enabled(FLAG_REQUIRE_HUMAN_REVIEW_REAL, default=True)

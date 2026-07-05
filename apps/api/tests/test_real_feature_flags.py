from app.modules.real_features import service as real_features

ALL_OPTIN_TEST_FLAGS = [
    real_features.FLAG_RUN_REAL_INTEGRATION_TESTS,
    real_features.FLAG_RUN_REAL_FINGUARD_TESTS,
    real_features.FLAG_RUN_REAL_PROVIDER_TESTS,
    real_features.FLAG_RUN_REAL_PLAYWRIGHT_TESTS,
    real_features.FLAG_RUN_REAL_OCR_TESTS,
    real_features.FLAG_RUN_REAL_MULTIMODAL_TESTS,
]

ALL_FEATURE_FLAGS = [
    real_features.FLAG_OCR_ENABLED,
    real_features.FLAG_MULTIMODAL_ENABLED,
    real_features.FLAG_VISUAL_QA_ENABLED,
    real_features.FLAG_PLAYWRIGHT_ENABLED,
]


def _clear(monkeypatch):
    for flag in ALL_OPTIN_TEST_FLAGS + ALL_FEATURE_FLAGS:
        monkeypatch.delenv(flag, raising=False)


def test_real_feature_flags_default_false(monkeypatch):
    _clear(monkeypatch)

    assert real_features.ocr_enabled() is False
    assert real_features.multimodal_enabled() is False
    assert real_features.visual_qa_enabled() is False
    assert real_features.playwright_enabled() is False


def test_optin_test_flags_default_false(monkeypatch):
    _clear(monkeypatch)

    for flag in ALL_OPTIN_TEST_FLAGS:
        assert real_features.flag_enabled(flag) is False, f"flag ligada: {flag}"


def test_security_defaults_are_true(monkeypatch):
    monkeypatch.delenv(real_features.FLAG_ENFORCE_PROJECT_POLICY, raising=False)
    monkeypatch.delenv(real_features.FLAG_REQUIRE_HUMAN_REVIEW_REAL, raising=False)

    assert real_features.enforce_project_policy() is True
    assert real_features.require_human_review_for_real_features() is True


def test_flag_only_accepts_explicit_true(monkeypatch):
    for value in ("1", "yes", "TRUE ", "True", "on", "enabled"):
        monkeypatch.setenv(real_features.FLAG_OCR_ENABLED, value)
        expected = value.strip().lower() == "true"
        assert real_features.ocr_enabled() is expected, f"valor: {value!r}"


def test_playwright_allowlist_parsing(monkeypatch):
    monkeypatch.setenv(
        real_features.FLAG_PLAYWRIGHT_ALLOWED_BASE_URLS,
        "http://localhost:5173, http://localhost:3333/",
    )

    urls = real_features.playwright_allowed_base_urls()

    assert urls == ["http://localhost:5173", "http://localhost:3333"]


def test_playwright_allowlist_empty_by_default(monkeypatch):
    monkeypatch.delenv(real_features.FLAG_PLAYWRIGHT_ALLOWED_BASE_URLS, raising=False)

    assert real_features.playwright_allowed_base_urls() == []

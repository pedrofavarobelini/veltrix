"""Catálogo de providers (MULTI-PROVIDER-SAFE-EVOLUTION, Etapa 1).

Prova que o catálogo caracteriza os providers existentes com estados
SEPARADOS (registro, implementação, configuração, homologação, autorização,
saúde), que combinações incoerentes não podem ser representadas e que nenhum
valor de credencial entra na estrutura. Nenhum teste usa rede ou chave real.
"""

import json

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.modules.orchestration.service import (
    AUTO_REAL_PROVIDER_CANDIDATES,
    LOCAL_PROVIDER_MODEL,
    LOCAL_PROVIDER_NAME,
)
from app.modules.provider_catalog.schemas import (
    HealthEvidence,
    HomologationStatus,
    ProviderAvailability,
    ProviderCapability,
    ProviderCategory,
    ProviderDefinition,
    ProviderHealth,
)
from app.modules.provider_catalog.service import provider_catalog_service
from app.modules.providers.registry import provider_registry

FAKE_KEY = "test-catalog-key-never-leak"

EXPECTED_PROVIDER_IDS = {
    "gemini",
    "claude",
    "openai",
    "deepseek",
    "grok",
    "mock",
    "local_qa",
    "local_model",
}


def test_catalog_characterizes_only_providers_recognized_by_the_repository():
    ids = set(provider_catalog_service.provider_ids())

    assert ids == EXPECTED_PROVIDER_IDS
    registry_ids = {item["name"] for item in provider_registry.list_providers()}
    # `auto` é modo de seleção, não provider: não pertence ao catálogo.
    assert "auto" not in ids
    assert ids <= registry_ids | {"local_qa"}


def test_local_pseudo_providers_are_not_real_external_providers():
    for provider_id in ("mock", "local_qa", "local_model"):
        definition = provider_catalog_service.get(provider_id)
        assert definition is not None
        assert definition.is_real_provider is False, provider_id

    for provider_id in ("gemini", "claude", "openai", "deepseek", "grok"):
        definition = provider_catalog_service.get(provider_id)
        assert definition.category is ProviderCategory.REAL_EXTERNAL, provider_id


def test_local_qa_matches_the_pipeline_constants():
    definition = provider_catalog_service.get("local_qa")

    assert definition.provider_id == LOCAL_PROVIDER_NAME
    assert definition.known_models == (LOCAL_PROVIDER_MODEL,)
    assert ProviderCapability.RELEASE_GATE_DECISION in definition.capabilities


def test_catalog_auto_authorization_matches_frozen_pipeline_list():
    """O catálogo descreve o automático atual; não o expande."""
    assert AUTO_REAL_PROVIDER_CANDIDATES == ("gemini",)
    assert provider_catalog_service.authorized_auto_ids() == ("gemini",)


def test_configured_provider_is_not_automatically_homologated(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", FAKE_KEY)

    claude = provider_catalog_service.get("claude")

    assert claude.configured is True
    assert claude.homologation is HomologationStatus.NOT_HOMOLOGATED
    assert claude.is_approved_for_production is False
    assert claude.is_eligible_for_auto is False


def test_configured_provider_is_not_automatically_healthy(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_KEY)

    gemini = provider_catalog_service.get("gemini")

    assert gemini.configured is True
    assert gemini.health is ProviderHealth.UNKNOWN
    assert gemini.health_evidence is HealthEvidence.NOT_EVALUATED
    assert gemini.availability is ProviderAvailability.UNKNOWN


def test_registered_but_not_implemented_provider_is_not_eligible():
    definition = ProviderDefinition(
        provider_id="futuro_provider",
        adapter=None,
        category=ProviderCategory.REAL_EXTERNAL,
        registered=True,
        implemented=False,
    )

    assert definition.is_executable is False
    assert definition.is_eligible_for_auto is False
    assert definition.is_approved_for_production is False


def test_incoherent_states_are_rejected_by_invariants():
    # Não implementado não pode estar configurado.
    with pytest.raises(ValidationError):
        ProviderDefinition(
            provider_id="x",
            adapter=None,
            category=ProviderCategory.REAL_EXTERNAL,
            registered=True,
            implemented=False,
            configured=True,
        )

    # Não implementado não pode estar homologado.
    with pytest.raises(ValidationError):
        ProviderDefinition(
            provider_id="x",
            adapter=None,
            category=ProviderCategory.REAL_EXTERNAL,
            registered=True,
            implemented=False,
            homologation=HomologationStatus.HOMOLOGATED_REAL,
        )

    # Não homologado não pode ser autorizado no automático.
    with pytest.raises(ValidationError):
        ProviderDefinition(
            provider_id="x",
            adapter="X",
            category=ProviderCategory.REAL_EXTERNAL,
            registered=True,
            implemented=True,
            configured=True,
            authorized_for_auto=True,
        )

    # Não registrado não pode ser autorizado no automático.
    with pytest.raises(ValidationError):
        ProviderDefinition(
            provider_id="x",
            adapter="X",
            category=ProviderCategory.REAL_EXTERNAL,
            registered=False,
            implemented=True,
            homologation=HomologationStatus.HOMOLOGATED_REAL,
            authorized_for_auto=True,
        )


def test_healthy_cannot_be_inferred_from_configuration():
    # Sem evidência explícita, 'healthy' é proibido.
    with pytest.raises(ValidationError):
        ProviderDefinition(
            provider_id="x",
            adapter="X",
            category=ProviderCategory.SIMULATED,
            registered=True,
            implemented=True,
            configured=True,
            homologation=HomologationStatus.HOMOLOGATED_INTERNAL,
            health=ProviderHealth.HEALTHY,
        )

    # Provider real não pode ser 'healthy' sem avaliação real (não existe nesta etapa).
    with pytest.raises(ValidationError):
        ProviderDefinition(
            provider_id="gemini_fake",
            adapter="X",
            category=ProviderCategory.REAL_EXTERNAL,
            registered=True,
            implemented=True,
            configured=True,
            homologation=HomologationStatus.HOMOLOGATED_REAL,
            health=ProviderHealth.HEALTHY,
            health_evidence=HealthEvidence.IN_PROCESS_DETERMINISTIC,
        )


def test_real_providers_start_with_unknown_health_even_when_configured(monkeypatch):
    for attribute in (
        "gemini_api_key",
        "anthropic_api_key",
        "openai_api_key",
        "deepseek_api_key",
        "xai_api_key",
    ):
        monkeypatch.setattr(settings, attribute, FAKE_KEY)

    for definition in provider_catalog_service.definitions():
        if definition.is_real_provider:
            assert definition.configured is True, definition.provider_id
            assert definition.health is ProviderHealth.UNKNOWN, definition.provider_id


def test_catalog_never_contains_credential_values(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_KEY)
    monkeypatch.setattr(settings, "anthropic_api_key", FAKE_KEY)
    monkeypatch.setattr(settings, "openai_api_key", FAKE_KEY)

    dumped = json.dumps(provider_catalog_service.snapshot(), ensure_ascii=False)

    assert FAKE_KEY not in dumped
    for definition in provider_catalog_service.definitions():
        # Só nomes de env var, nunca valores.
        for key in definition.required_config_keys:
            assert key == key.upper()
            assert FAKE_KEY not in key


def test_config_keys_must_be_env_var_names_not_values():
    with pytest.raises(ValidationError):
        ProviderDefinition(
            provider_id="x",
            adapter="X",
            category=ProviderCategory.REAL_EXTERNAL,
            required_config_keys=("AIzaSy-fake-value",),
        )


def test_missing_configuration_keeps_provider_not_executable(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")

    gemini = provider_catalog_service.get("gemini")

    assert gemini.registered is True
    assert gemini.implemented is True
    assert gemini.configured is False
    assert gemini.is_executable is False
    assert gemini.is_eligible_for_auto is False


def test_auto_eligibility_requires_configuration_homologation_and_authorization(
    monkeypatch,
):
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_KEY)
    monkeypatch.setattr(settings, "anthropic_api_key", FAKE_KEY)
    monkeypatch.setattr(settings, "openai_api_key", FAKE_KEY)

    assert provider_catalog_service.auto_eligible_ids() == ("gemini",)

    monkeypatch.setattr(settings, "gemini_api_key", "")
    assert provider_catalog_service.auto_eligible_ids() == ()


def test_release_gate_capability_belongs_only_to_local_qa():
    with_capability = [
        definition.provider_id
        for definition in provider_catalog_service.definitions()
        if ProviderCapability.RELEASE_GATE_DECISION in definition.capabilities
    ]

    assert with_capability == ["local_qa"]


def test_task_compatibility_excludes_release_gate_for_mock_and_local_model():
    assert provider_catalog_service.get("mock").supports_task("release_gate_review") is False
    assert (
        provider_catalog_service.get("local_model").supports_task("release_gate_review")
        is False
    )
    assert provider_catalog_service.get("local_qa").supports_task("release_gate_review") is True


def test_unknown_provider_is_not_in_catalog():
    assert provider_catalog_service.get("provider_inexistente") is None
    assert provider_catalog_service.get(None) is None

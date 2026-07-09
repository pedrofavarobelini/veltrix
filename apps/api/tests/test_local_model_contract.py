import pytest
from pydantic import ValidationError

from app.modules.orchestration.service import LOCAL_PROVIDER_NAME
from app.modules.providers.local_model_contract import (
    LOCAL_MODEL_PROVIDER_ID,
    SUPPORTED_BACKENDS,
    LocalModelProviderContract,
    default_local_model_contract,
)
from app.modules.providers.registry import provider_registry


def test_default_contract_is_disabled_and_offline():
    contract = default_local_model_contract()

    assert contract.provider_id == "local_model"
    assert contract.category == "local_generative"
    assert contract.real_provider is False
    assert contract.requires_external_api_key is False
    assert contract.enabled_by_default is False
    assert contract.generation_supported is False
    assert contract.health_check_supported is False
    assert contract.endpoint_url is None


def test_contract_rejects_generation_in_this_foundation():
    with pytest.raises(ValidationError):
        LocalModelProviderContract(generation_supported=True)


def test_contract_rejects_external_api_key_requirement():
    with pytest.raises(ValidationError):
        LocalModelProviderContract(requires_external_api_key=True)


def test_contract_rejects_unknown_backend():
    with pytest.raises(ValidationError):
        LocalModelProviderContract(backend="openai")


def test_supported_backends_are_local_only():
    assert SUPPORTED_BACKENDS == {"ollama", "llama_cpp", "lm_studio", "custom"}


def test_local_model_is_distinct_from_local_qa():
    # local_qa: determinístico de QA, ativo no pipeline.
    # local_model: generativo futuro, apenas contrato nesta frente.
    assert LOCAL_MODEL_PROVIDER_ID != LOCAL_PROVIDER_NAME
    assert LOCAL_PROVIDER_NAME == "local_qa"


def test_local_model_is_registered_but_disabled_by_default():
    # ECOSYSTEM-INTELLIGENCE-SUITE-01: o provider passou a existir no registry,
    # mas é opt-in default-off — nunca configured sem flag explícita e nunca
    # real_provider externo.
    provider = provider_registry.get("local_model")

    assert provider is not None
    assert provider.real_provider is False
    assert provider.is_configured is False

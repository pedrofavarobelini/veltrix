from pydantic import BaseModel, field_validator

# Contrato futuro do Local Model Provider (PEDROCORE-MODEL-FOUNDATION-01).
#
# Diferença obrigatória entre os dois providers locais:
#   - local_qa    -> provider DETERMINÍSTICO de QA, já ativo no pipeline de
#                    orquestração (LOCAL_PROVIDERS); é o único confiável para
#                    release gate.
#   - local_model -> provider GENERATIVO local FUTURO (Ollama, llama.cpp,
#                    LM Studio ou backend custom). Nesta frente é apenas
#                    contrato: nenhuma chamada de rede, nenhum backend
#                    instalado, nenhum modelo baixado, nenhuma geração.
#
# O local_model NÃO está registrado no provider_registry nesta frente;
# pedir provider="local_model" cai no fallback Mock existente.

LOCAL_MODEL_PROVIDER_ID = "local_model"
LOCAL_MODEL_CATEGORY = "local_generative"

SUPPORTED_BACKENDS = {"ollama", "llama_cpp", "lm_studio", "custom"}


class LocalModelProviderContract(BaseModel):
    """Contrato estrutural do futuro provider generativo local.

    generation_supported permanece False nesta fundação: o contrato existe
    para fixar o formato, não para habilitar geração local.
    """

    provider_id: str = LOCAL_MODEL_PROVIDER_ID
    category: str = LOCAL_MODEL_CATEGORY
    real_provider: bool = False
    requires_external_api_key: bool = False
    enabled_by_default: bool = False
    supports_streaming: bool = False
    supports_tools: bool = False
    max_context_tokens: int | None = None
    backend: str = "custom"
    endpoint_url: str | None = None
    health_check_supported: bool = False
    generation_supported: bool = False

    @field_validator("backend")
    @classmethod
    def backend_known(cls, value: str) -> str:
        if value not in SUPPORTED_BACKENDS:
            raise ValueError(
                f"backend inválido: '{value}'. Permitidos: {sorted(SUPPORTED_BACKENDS)}."
            )
        return value

    @field_validator("generation_supported")
    @classmethod
    def generation_not_supported_in_foundation(cls, value: bool) -> bool:
        if value:
            raise ValueError(
                "generation_supported deve permanecer False nesta fundação; "
                "a implementação real fica para PEDROCORE-LOCAL-MODEL-01."
            )
        return value

    @field_validator("requires_external_api_key")
    @classmethod
    def never_requires_external_key(cls, value: bool) -> bool:
        if value:
            raise ValueError(
                "local_model é local por definição; nunca exige chave externa."
            )
        return value


def default_local_model_contract() -> LocalModelProviderContract:
    """Contrato padrão: desabilitado, sem endpoint, sem geração."""
    return LocalModelProviderContract()

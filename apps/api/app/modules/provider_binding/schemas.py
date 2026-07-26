"""Provider/model binding (MULTI-PROVIDER-SAFE-EVOLUTION, Etapa 3).

Provider e modelo deixam de ser dois campos independentes e passam a ser
selecionados e validados como UMA unidade coerente. O adapter só recebe uma
combinação já validada pelo PedroCore — nunca decide sozinho se aceita ou
corrige silenciosamente o modelo enviado no payload.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.modules.provider_catalog.schemas import ProviderCapability


class ModelSource(str, Enum):
    """De onde veio o modelo efetivamente selecionado."""

    # Default interno declarado pelo provider no catálogo.
    PROVIDER_DEFAULT = "provider_default"
    # Política interna do projeto (reservado; hoje recai no default).
    PROJECT_POLICY = "project_policy"
    # Seleção explícita de ferramenta técnica autorizada.
    EXPLICIT_TECHNICAL = "explicit_technical"
    # Modelo fixo de Mock / provider determinístico local.
    LOCAL_FIXED = "local_fixed"
    # Nenhum modelo selecionado (provider desconhecido ou binding inválido).
    # Este estado nunca pode alcançar adapter real.
    NOT_SELECTED = "not_selected"


class BindingValidation(str, Enum):
    VALID = "valid"
    INVALID = "invalid"


class ProviderModelBinding(BaseModel):
    """Unidade provider+modelo caracterizada a partir do catálogo."""

    model_config = ConfigDict(frozen=True, protected_namespaces=())

    provider_id: str
    model_id: str
    adapter_id: str | None
    capabilities: tuple[ProviderCapability, ...] = ()
    compatible_tasks: tuple[str, ...] = ()
    registered: bool = False
    implemented: bool = False
    configured: bool = False
    homologated: bool = False
    # Autorização de MODELO (pertence ao provider, é reconhecido e homologado
    # quando exigido). Autorização por projeto/identidade continua sendo
    # responsabilidade exclusiva de provider_authorization.
    authorized: bool = False
    default_for_provider: bool = False
    source: ModelSource = ModelSource.NOT_SELECTED


class SelectedProviderModel(BaseModel):
    """Decisão interna de binding entregue ao pipeline."""

    model_config = ConfigDict(frozen=True, protected_namespaces=())

    selection_mode: str
    requested_provider: str
    requested_model: str | None = None
    provider_id: str | None = None
    model_id: str | None = None
    model_source: ModelSource = ModelSource.NOT_SELECTED
    validation_result: BindingValidation = BindingValidation.VALID
    error_code: str | None = None
    reason: str | None = None
    warning_code: str | None = None
    warning_reason: str | None = None
    binding: ProviderModelBinding | None = None

    @property
    def valid(self) -> bool:
        return self.validation_result is BindingValidation.VALID

    @property
    def invalid(self) -> bool:
        return self.validation_result is BindingValidation.INVALID

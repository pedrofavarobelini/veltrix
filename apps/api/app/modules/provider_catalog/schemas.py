"""Catálogo tipado de providers (MULTI-PROVIDER-SAFE-EVOLUTION, Etapa 1).

Estrutura PASSIVA de caracterização. Descreve, sem segredos, cada provider
conhecido pelo PedroCore: adapter associado, categoria, modelos conhecidos,
configuração exigida (apenas NOMES de variáveis de ambiente), capacidades,
tasks compatíveis, prioridade estática e os estados SEPARADOS de registro,
implementação, configuração, homologação, autorização e saúde.

Regras desta etapa:
  - o catálogo NÃO decide roteamento: `provider=auto` continua Gemini-only
    (`AUTO_REAL_PROVIDER_CANDIDATES` em orchestration/service.py);
  - nenhum valor de credencial entra aqui — só nomes de env var;
  - `registered`, `implemented`, `configured`, `homologation`, `authorized`
    e `health` são conceitos distintos e nunca inferidos um do outro;
  - saúde de provider real exige avaliação real, que NÃO existe nesta etapa:
    sem evidência, o estado permanece `unknown`.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator

# Marcador de "qualquer task permitida pela policy do projeto".
ANY_TASK = "*"

_ENV_VAR_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")


class ProviderCategory(str, Enum):
    """Natureza do provider. Mock/local NÃO são providers externos reais."""

    REAL_EXTERNAL = "real_external"
    LOCAL_DETERMINISTIC = "local_deterministic"
    LOCAL_GENERATIVE = "local_generative"
    SIMULATED = "simulated"


class ProviderCapability(str, Enum):
    """Capacidades efetivamente suportadas pelo código atual."""

    TEXT_GENERATION = "text_generation"
    DETERMINISTIC_QA_ANALYSIS = "deterministic_qa_analysis"
    RELEASE_GATE_DECISION = "release_gate_decision"
    SAFE_FALLBACK = "safe_fallback"


class HomologationStatus(str, Enum):
    """Homologação é decisão de engenharia, não consequência de ter chave."""

    NOT_HOMOLOGATED = "not_homologated"
    HOMOLOGATED_INTERNAL = "homologated_internal"
    HOMOLOGATED_REAL = "homologated_real"


class ProviderAvailability(str, Enum):
    """Disponibilidade conhecida, sem qualquer sondagem de rede."""

    UNKNOWN = "unknown"
    KNOWN_AVAILABLE = "known_available"
    KNOWN_UNAVAILABLE = "known_unavailable"


class ProviderHealth(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class HealthEvidence(str, Enum):
    """Origem da evidência de saúde. `NOT_EVALUATED` é o default honesto."""

    NOT_EVALUATED = "not_evaluated"
    IN_PROCESS_DETERMINISTIC = "in_process_deterministic"


class ModelDefinition(BaseModel):
    """Entrada explícita de modelo, vinculada a exatamente um provider.

    O catálogo é a fonte única de verdade de modelos: o binding (Etapa 3) e a
    política shadow (Etapa 4) leem daqui em vez de manter listas paralelas.
    Configuração runtime nunca cria ou homologa uma instância.
    """

    model_config = ConfigDict(frozen=True, protected_namespaces=())

    model_id: str
    provider_id: str
    registered: bool
    implemented: bool
    homologated: bool
    authorized: bool
    default_for_provider: bool
    compatible_tasks: tuple[str, ...] = (ANY_TASK,)
    excluded_tasks: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    # Teto de saída do modelo (OUTPUT-BUDGET-CANCELLATION-01). É uma das três
    # camadas do orçamento efetivo, junto do teto global e da política por
    # task; nunca é enviado pelo consumidor. `None` significa "sem teto
    # próprio declarado", não "ilimitado": o global e a task continuam valendo.
    max_output_tokens: int | None = None
    notes: str = ""

    @model_validator(mode="after")
    def _check(self) -> ModelDefinition:
        if not self.model_id.strip():
            raise ValueError("model_id vazio não identifica modelo.")
        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError(
                "max_output_tokens deve ser inteiro positivo quando declarado: "
                f"{self.model_id}"
            )
        if not self.provider_id.strip():
            raise ValueError(
                f"modelo sem provider não pode existir no catálogo: {self.model_id!r}"
            )
        if not self.registered and (
            self.implemented
            or self.homologated
            or self.authorized
            or self.default_for_provider
        ):
            raise ValueError(
                "modelo não registrado não pode estar implementado, homologado, "
                f"autorizado ou ser default: {self.model_id}"
            )
        if not self.implemented and (
            self.homologated or self.authorized or self.default_for_provider
        ):
            raise ValueError(
                "modelo não implementado não pode estar homologado, autorizado "
                f"ou ser default: {self.model_id}"
            )
        normalized_aliases = [alias.strip().lower() for alias in self.aliases]
        if any(not alias for alias in normalized_aliases):
            raise ValueError(f"alias vazio no modelo: {self.model_id}")
        if len(normalized_aliases) != len(set(normalized_aliases)):
            raise ValueError(f"aliases duplicados no modelo: {self.model_id}")
        if self.model_id.strip().lower() in normalized_aliases:
            raise ValueError(f"alias repete o model_id canônico: {self.model_id}")
        return self

    def supports_task(self, task_type: str) -> bool:
        normalized = (task_type or "").strip().lower()
        if normalized in self.excluded_tasks:
            return False
        if ANY_TASK in self.compatible_tasks:
            return True
        return normalized in self.compatible_tasks


class ProviderDefinition(BaseModel):
    """Definição imutável e sem segredos de um provider do catálogo."""

    model_config = ConfigDict(frozen=True)

    provider_id: str
    adapter: str | None
    category: ProviderCategory
    known_models: tuple[str, ...] = ()
    # Apenas NOMES de variáveis de ambiente; nunca valores.
    required_config_keys: tuple[str, ...] = ()
    capabilities: tuple[ProviderCapability, ...] = ()
    compatible_tasks: tuple[str, ...] = (ANY_TASK,)
    excluded_tasks: tuple[str, ...] = ()

    registered: bool = False
    implemented: bool = False
    configured: bool = False
    homologation: HomologationStatus = HomologationStatus.NOT_HOMOLOGATED
    # Autorização estática de participação na seleção automática. Não é
    # autorização por projeto (Etapa 2) nem permissão de execução.
    authorized_for_auto: bool = False
    static_priority: int | None = None
    availability: ProviderAvailability = ProviderAvailability.UNKNOWN
    health: ProviderHealth = ProviderHealth.UNKNOWN
    health_evidence: HealthEvidence = HealthEvidence.NOT_EVALUATED
    notes: str = ""

    # ------------------------------------------------------------------
    # Invariantes: estados incoerentes não podem ser representados.
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def _check_invariants(self) -> ProviderDefinition:
        for key in self.required_config_keys:
            if not _ENV_VAR_NAME.match(key):
                raise ValueError(
                    "required_config_keys aceita apenas NOMES de variáveis de "
                    f"ambiente em maiúsculas, nunca valores: {key!r}"
                )

        if not self.registered and self.authorized_for_auto:
            raise ValueError(
                "provider não registrado não pode ser autorizado no automático: "
                f"{self.provider_id}"
            )

        if not self.implemented:
            if self.configured:
                raise ValueError(
                    "provider sem adapter implementado não pode estar configurado: "
                    f"{self.provider_id}"
                )
            if self.homologation is not HomologationStatus.NOT_HOMOLOGATED:
                raise ValueError(
                    "provider não implementado não pode estar homologado: "
                    f"{self.provider_id}"
                )
            if self.authorized_for_auto:
                raise ValueError(
                    "provider não implementado não pode ser elegível no automático: "
                    f"{self.provider_id}"
                )

        if self.authorized_for_auto and self.homologation is HomologationStatus.NOT_HOMOLOGATED:
            raise ValueError(
                "provider não homologado não pode ser autorizado no automático: "
                f"{self.provider_id}"
            )

        if self.health is ProviderHealth.HEALTHY:
            if self.health_evidence is HealthEvidence.NOT_EVALUATED:
                raise ValueError(
                    "'healthy' não pode ser inferido de configuração: exige "
                    f"evidência explícita ({self.provider_id})"
                )
            if self.category is ProviderCategory.REAL_EXTERNAL:
                raise ValueError(
                    "saúde de provider real exige avaliação real, não implementada "
                    f"nesta etapa: {self.provider_id}"
                )
            if not (self.implemented and self.configured):
                raise ValueError(
                    "provider não implementado/configurado não pode ser 'healthy': "
                    f"{self.provider_id}"
                )

        if (
            self.availability is ProviderAvailability.KNOWN_AVAILABLE
            and not self.implemented
        ):
            raise ValueError(
                f"provider não implementado não pode estar disponível: {self.provider_id}"
            )

        return self

    # ------------------------------------------------------------------
    # Estados derivados (nunca booleanos soltos).
    # ------------------------------------------------------------------
    @property
    def is_executable(self) -> bool:
        """Pode ser executado tecnicamente agora (registro + adapter + config)."""
        return self.registered and self.implemented and self.configured

    @property
    def is_approved_for_production(self) -> bool:
        """Homologação explícita; nunca derivada de chave presente."""
        return self.implemented and self.homologation is not HomologationStatus.NOT_HOMOLOGATED

    @property
    def is_real_provider(self) -> bool:
        return self.category is ProviderCategory.REAL_EXTERNAL

    @property
    def is_eligible_for_auto(self) -> bool:
        """Elegibilidade estática no automático — consultiva nesta etapa."""
        return (
            self.is_real_provider
            and self.is_executable
            and self.is_approved_for_production
            and self.authorized_for_auto
        )

    def supports_task(self, task_type: str) -> bool:
        normalized = (task_type or "").strip().lower()
        if normalized in self.excluded_tasks:
            return False
        if ANY_TASK in self.compatible_tasks:
            return True
        return normalized in self.compatible_tasks

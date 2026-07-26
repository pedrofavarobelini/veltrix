"""Serviço de catálogo de providers (MULTI-PROVIDER-SAFE-EVOLUTION, Etapa 1).

Constrói, sob demanda, a caracterização tipada dos providers realmente
reconhecidos pelo repositório. É uma camada de LEITURA: não escolhe provider,
não altera prioridade real, não inicia fallback e não é consultada pelo
pipeline de orquestração nesta etapa.

`configured` é derivado do adapter em tempo de leitura (`is_configured`), por
isso o catálogo é reconstruído a cada chamada: ambiente muda, catálogo
acompanha — sem nunca ler ou expor o valor da credencial.
"""

from __future__ import annotations

from typing import Any

from app.modules.provider_catalog.schemas import (
    ANY_TASK,
    HealthEvidence,
    HomologationStatus,
    ModelDefinition,
    ProviderAvailability,
    ProviderCapability,
    ProviderCategory,
    ProviderDefinition,
    ProviderHealth,
)
from app.modules.providers.local_model_provider import local_model_name
from app.modules.providers.registry import provider_registry

# Pseudo-providers resolvidos dentro do pipeline, sem entrada no registry.
# `local_qa` é o caminho determinístico de QA (LOCAL_PROVIDER_NAME/MODEL em
# orchestration/service.py); nunca é um provider externo real.
LOCAL_QA_PROVIDER_ID = "local_qa"
LOCAL_QA_MODEL = "local-qa-v1"

_REAL_EXTERNAL_NOTE = (
    "Provider externo real: só executa com allow_real_provider=true e "
    "configuração presente; nunca decide release gate sozinho."
)

# Caracterização estática. Tudo que depende de ambiente (configured) é
# resolvido dinamicamente em _build(); aqui só há decisão de engenharia.
_STATIC_SPECS: dict[str, dict[str, Any]] = {
    "gemini": {
        "adapter": "GeminiProvider",
        "category": ProviderCategory.REAL_EXTERNAL,
        "required_config_keys": ("GEMINI_API_KEY",),
        "capabilities": (ProviderCapability.TEXT_GENERATION,),
        "excluded_tasks": (),
        # Único provider real homologado e autorizado no automático desde
        # FINGUARD-PEDROCORE-ASSISTANT-REAL-PROVIDER-QA-01.
        "homologation": HomologationStatus.HOMOLOGATED_REAL,
        "authorized_for_auto": True,
        "static_priority": 10,
        "notes": _REAL_EXTERNAL_NOTE,
    },
    "claude": {
        "adapter": "ClaudeProvider",
        "category": ProviderCategory.REAL_EXTERNAL,
        "required_config_keys": ("ANTHROPIC_API_KEY",),
        "capabilities": (ProviderCapability.TEXT_GENERATION,),
        "homologation": HomologationStatus.NOT_HOMOLOGATED,
        "authorized_for_auto": False,
        "static_priority": 20,
        "notes": _REAL_EXTERNAL_NOTE + " Não homologado; fora do automático.",
    },
    "openai": {
        "adapter": "OpenAIProvider",
        "category": ProviderCategory.REAL_EXTERNAL,
        "required_config_keys": ("OPENAI_API_KEY",),
        "capabilities": (ProviderCapability.TEXT_GENERATION,),
        "homologation": HomologationStatus.NOT_HOMOLOGATED,
        "authorized_for_auto": False,
        "static_priority": 30,
        "notes": _REAL_EXTERNAL_NOTE + " Não homologado; fora do automático.",
    },
    "deepseek": {
        "adapter": "DeepSeekProvider",
        "category": ProviderCategory.REAL_EXTERNAL,
        "required_config_keys": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"),
        "capabilities": (ProviderCapability.TEXT_GENERATION,),
        "homologation": HomologationStatus.NOT_HOMOLOGATED,
        "authorized_for_auto": False,
        "static_priority": 40,
        "notes": _REAL_EXTERNAL_NOTE + " Não homologado; fora do automático.",
    },
    "grok": {
        "adapter": "GrokProvider",
        "category": ProviderCategory.REAL_EXTERNAL,
        "required_config_keys": ("XAI_API_KEY", "XAI_BASE_URL"),
        "capabilities": (ProviderCapability.TEXT_GENERATION,),
        "homologation": HomologationStatus.NOT_HOMOLOGATED,
        "authorized_for_auto": False,
        "static_priority": 50,
        "notes": _REAL_EXTERNAL_NOTE + " Não homologado; fora do automático.",
    },
    "mock": {
        "adapter": "MockProvider",
        "category": ProviderCategory.SIMULATED,
        "required_config_keys": (),
        "capabilities": (
            ProviderCapability.TEXT_GENERATION,
            ProviderCapability.SAFE_FALLBACK,
        ),
        "excluded_tasks": ("release_gate_review",),
        "homologation": HomologationStatus.HOMOLOGATED_INTERNAL,
        "authorized_for_auto": False,
        "static_priority": None,
        "availability": ProviderAvailability.KNOWN_AVAILABLE,
        "health": ProviderHealth.HEALTHY,
        "health_evidence": HealthEvidence.IN_PROCESS_DETERMINISTIC,
        "notes": (
            "Resposta simulada em processo; é o fallback seguro do pipeline e "
            "nunca aprova release gate."
        ),
    },
    LOCAL_QA_PROVIDER_ID: {
        "adapter": None,
        "category": ProviderCategory.LOCAL_DETERMINISTIC,
        "required_config_keys": (),
        "capabilities": (
            ProviderCapability.DETERMINISTIC_QA_ANALYSIS,
            ProviderCapability.RELEASE_GATE_DECISION,
        ),
        "homologation": HomologationStatus.HOMOLOGATED_INTERNAL,
        "authorized_for_auto": False,
        "static_priority": None,
        "availability": ProviderAvailability.KNOWN_AVAILABLE,
        "health": ProviderHealth.HEALTHY,
        "health_evidence": HealthEvidence.IN_PROCESS_DETERMINISTIC,
        "notes": (
            "Análise textual determinística em processo, sem rede e sem chave; "
            "único provider confiável para release gate."
        ),
    },
    "local_model": {
        "adapter": "LocalModelProvider",
        "category": ProviderCategory.LOCAL_GENERATIVE,
        "required_config_keys": (
            "PEDROCORE_ENABLE_LOCAL_MODEL",
            "PEDROCORE_LOCAL_MODEL_BACKEND",
        ),
        "capabilities": (ProviderCapability.TEXT_GENERATION,),
        "excluded_tasks": ("release_gate_review",),
        "homologation": HomologationStatus.NOT_HOMOLOGATED,
        "authorized_for_auto": False,
        "static_priority": None,
        "notes": (
            "Generativo local opt-in, default OFF e sem transport padrão; "
            "não é provider externo real e nunca aprova release gate."
        ),
    },
}

# Catálogo explícito e imutável de modelos. Estes são exatamente os
# identificadores já reconhecidos pelo código antes desta correção; valores de
# settings/env/adapter.default_model apenas selecionam um identificador e nunca
# criam uma entrada.
_MODEL_CATALOG: tuple[ModelDefinition, ...] = (
    ModelDefinition(
        provider_id="gemini",
        model_id="gemini-3.5-flash",
        registered=True,
        implemented=True,
        homologated=True,
        authorized=True,
        default_for_provider=True,
        notes="Modelo Gemini explicitamente homologado para o uso real atual.",
    ),
    ModelDefinition(
        provider_id="claude",
        model_id="claude-sonnet-4-5",
        registered=True,
        implemented=True,
        homologated=False,
        authorized=False,
        default_for_provider=True,
        notes="Modelo conhecido, ainda não homologado nem autorizado.",
    ),
    ModelDefinition(
        provider_id="openai",
        model_id="gpt-5.2-mini",
        registered=True,
        implemented=True,
        homologated=False,
        authorized=False,
        default_for_provider=True,
        notes="Modelo conhecido, ainda não homologado nem autorizado.",
    ),
    ModelDefinition(
        provider_id="deepseek",
        model_id="deepseek-chat",
        registered=True,
        implemented=True,
        homologated=False,
        authorized=False,
        default_for_provider=True,
        notes="Modelo conhecido, ainda não homologado nem autorizado.",
    ),
    ModelDefinition(
        provider_id="grok",
        model_id="grok-4.3",
        registered=True,
        implemented=True,
        homologated=False,
        authorized=False,
        default_for_provider=True,
        notes="Modelo conhecido, ainda não homologado nem autorizado.",
    ),
    ModelDefinition(
        provider_id="mock",
        model_id="mock-v1",
        registered=True,
        implemented=True,
        homologated=True,
        authorized=True,
        default_for_provider=True,
        excluded_tasks=("release_gate_review",),
        notes="Modelo simulado fixo usado somente no fallback seguro.",
    ),
    ModelDefinition(
        provider_id=LOCAL_QA_PROVIDER_ID,
        model_id=LOCAL_QA_MODEL,
        registered=True,
        implemented=True,
        homologated=True,
        authorized=True,
        default_for_provider=True,
        notes="Modelo determinístico local fixo para análise de QA.",
    ),
    ModelDefinition(
        provider_id="local_model",
        model_id="local-model",
        registered=True,
        implemented=True,
        homologated=False,
        authorized=True,
        default_for_provider=True,
        excluded_tasks=("release_gate_review",),
        notes="Modelo generativo local opt-in; nunca é provider externo real.",
    ),
)


def _validate_model_catalog(
    entries: tuple[ModelDefinition, ...],
) -> tuple[ModelDefinition, ...]:
    """Falha cedo se model_id/alias for ambíguo ou houver defaults duplicados."""
    identifiers: dict[str, str] = {}
    defaults: set[str] = set()

    for entry in entries:
        if entry.provider_id not in _STATIC_SPECS:
            raise ValueError(
                f"modelo {entry.model_id!r} aponta para provider desconhecido: "
                f"{entry.provider_id!r}"
            )
        for identifier in (entry.model_id, *entry.aliases):
            normalized = identifier.strip().lower()
            owner = identifiers.get(normalized)
            if owner is not None:
                raise ValueError(
                    "model_id/alias deve pertencer a exatamente um provider: "
                    f"{identifier!r} aparece em {owner!r} e {entry.provider_id!r}"
                )
            identifiers[normalized] = entry.provider_id
        if entry.default_for_provider:
            if entry.provider_id in defaults:
                raise ValueError(
                    f"provider com mais de um default explícito: {entry.provider_id}"
                )
            defaults.add(entry.provider_id)

    return entries


_MODEL_CATALOG = _validate_model_catalog(_MODEL_CATALOG)


class ProviderCatalogService:
    """Leitura tipada do catálogo. Nenhuma decisão de roteamento aqui."""

    def definitions(self) -> tuple[ProviderDefinition, ...]:
        return tuple(
            self._build(provider_id, spec) for provider_id, spec in _STATIC_SPECS.items()
        )

    def get(self, provider_id: str | None) -> ProviderDefinition | None:
        normalized = (provider_id or "").strip().lower()
        spec = _STATIC_SPECS.get(normalized)
        if spec is None:
            return None
        return self._build(normalized, spec)

    def provider_ids(self) -> tuple[str, ...]:
        return tuple(_STATIC_SPECS)

    def real_provider_ids(self) -> tuple[str, ...]:
        return tuple(
            definition.provider_id
            for definition in self.definitions()
            if definition.is_real_provider
        )

    def auto_eligible_ids(self) -> tuple[str, ...]:
        """Elegíveis estáticos no automático, ordenados por prioridade.

        Consultivo nesta etapa: o pipeline continua usando
        `AUTO_REAL_PROVIDER_CANDIDATES`, que permanece Gemini-only.
        """
        eligible = [
            definition
            for definition in self.definitions()
            if definition.is_eligible_for_auto
        ]
        eligible.sort(key=lambda item: (item.static_priority or 10_000, item.provider_id))
        return tuple(definition.provider_id for definition in eligible)

    def authorized_auto_ids(self) -> tuple[str, ...]:
        """Autorizados estaticamente no automático, independente de configuração."""
        authorized = [
            definition
            for definition in self.definitions()
            if definition.is_real_provider and definition.authorized_for_auto
        ]
        authorized.sort(key=lambda item: (item.static_priority or 10_000, item.provider_id))
        return tuple(definition.provider_id for definition in authorized)

    def snapshot(self) -> list[dict[str, Any]]:
        """Projeção de diagnóstico interno, sem segredos e sem endpoints privados."""
        return [
            {
                "provider_id": definition.provider_id,
                "adapter": definition.adapter,
                "category": definition.category.value,
                "known_models": list(definition.known_models),
                "required_config_keys": list(definition.required_config_keys),
                "capabilities": [item.value for item in definition.capabilities],
                "compatible_tasks": list(definition.compatible_tasks),
                "excluded_tasks": list(definition.excluded_tasks),
                "registered": definition.registered,
                "implemented": definition.implemented,
                "configured": definition.configured,
                "homologation": definition.homologation.value,
                "authorized_for_auto": definition.authorized_for_auto,
                "static_priority": definition.static_priority,
                "availability": definition.availability.value,
                "health": definition.health.value,
                "health_evidence": definition.health_evidence.value,
                "is_executable": definition.is_executable,
                "is_approved_for_production": definition.is_approved_for_production,
                "is_eligible_for_auto": definition.is_eligible_for_auto,
                "notes": definition.notes,
            }
            for definition in self.definitions()
        ]

    # ------------------------------------------------------------------
    # Modelos conhecidos — fonte única de verdade do binding (Etapa 3).
    # ------------------------------------------------------------------
    def models(self) -> tuple[ModelDefinition, ...]:
        return _MODEL_CATALOG

    def models_for(self, provider_id: str | None) -> tuple[ModelDefinition, ...]:
        normalized = (provider_id or "").strip().lower()
        if normalized not in _STATIC_SPECS:
            return ()
        return tuple(
            model for model in _MODEL_CATALOG if model.provider_id == normalized
        )

    def find_model(self, model_id: str | None) -> ModelDefinition | None:
        """Resolve um identificador canônico ou alias sem ambiguidade."""
        normalized = (model_id or "").strip().lower()
        if not normalized:
            return None
        return next(
            (
                model
                for model in _MODEL_CATALOG
                if model.model_id.lower() == normalized
                or normalized in {alias.lower() for alias in model.aliases}
            ),
            None,
        )

    def default_model_for(self, provider_id: str | None) -> ModelDefinition | None:
        return next(
            (model for model in self.models_for(provider_id) if model.default_for_provider),
            None,
        )

    def configured_model_id_for(self, provider_id: str | None) -> str | None:
        """Lê a seleção runtime sem criar ou homologar entrada de catálogo."""
        normalized = (provider_id or "").strip().lower()
        if normalized == LOCAL_QA_PROVIDER_ID:
            return LOCAL_QA_MODEL

        spec = _STATIC_SPECS.get(normalized)
        if spec is None or not spec.get("adapter"):
            return None
        adapter = provider_registry.get(normalized)
        if adapter is None or adapter.name != normalized:
            return None

        if normalized == "local_model":
            candidate = local_model_name()
        else:
            candidate = adapter.default_model
        candidate = (candidate or "").strip()
        return candidate or None

    # ------------------------------------------------------------------
    def _build(self, provider_id: str, spec: dict[str, Any]) -> ProviderDefinition:
        adapter = provider_registry.get(provider_id) if spec.get("adapter") else None
        # provider_registry.get() devolve o Mock para nomes ausentes; só vale
        # como evidência quando o adapter registrado é o próprio provider.
        matched = adapter is not None and adapter.name == provider_id

        if provider_id == LOCAL_QA_PROVIDER_ID:
            registered = True
            implemented = True
            configured = True
        else:
            registered = matched
            implemented = matched
            configured = bool(matched and adapter.is_configured)
        known_models = tuple(
            model.model_id
            for model in _MODEL_CATALOG
            if model.provider_id == provider_id and model.registered
        )

        health = spec.get("health", ProviderHealth.UNKNOWN)
        health_evidence = spec.get("health_evidence", HealthEvidence.NOT_EVALUATED)
        availability = spec.get("availability", ProviderAvailability.UNKNOWN)
        if not implemented or not configured:
            # Sem adapter utilizável não há evidência de saúde nem de disponibilidade.
            health = ProviderHealth.UNKNOWN
            health_evidence = HealthEvidence.NOT_EVALUATED
            availability = ProviderAvailability.UNKNOWN

        homologation = spec.get("homologation", HomologationStatus.NOT_HOMOLOGATED)
        authorized_for_auto = bool(spec.get("authorized_for_auto", False))
        if not implemented:
            homologation = HomologationStatus.NOT_HOMOLOGATED
            authorized_for_auto = False

        return ProviderDefinition(
            provider_id=provider_id,
            adapter=spec.get("adapter"),
            category=spec["category"],
            known_models=known_models,
            required_config_keys=tuple(spec.get("required_config_keys", ())),
            capabilities=tuple(spec.get("capabilities", ())),
            compatible_tasks=tuple(spec.get("compatible_tasks", (ANY_TASK,))),
            excluded_tasks=tuple(spec.get("excluded_tasks", ())),
            registered=registered,
            implemented=implemented,
            configured=configured,
            homologation=homologation,
            authorized_for_auto=authorized_for_auto,
            static_priority=spec.get("static_priority"),
            availability=availability,
            health=health,
            health_evidence=health_evidence,
            notes=spec.get("notes", ""),
        )


provider_catalog_service = ProviderCatalogService()

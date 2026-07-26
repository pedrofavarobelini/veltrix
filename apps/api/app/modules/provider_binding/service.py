"""Resolução de provider/model binding (Etapa 3).

Regras centrais:

  - o modelo NUNCA seleciona provider: em `provider=auto` o candidato real
    continua vindo de `AUTO_REAL_PROVIDER_CANDIDATES` (Gemini-only);
  - consumidor comum não define modelo;
  - modelo explícito precisa pertencer ao provider pedido, ser conhecido pelo
    catálogo, estar homologado quando o provider é externo e ser compatível
    com a task;
  - combinação inválida é REJEITADA, nunca corrigida em silêncio para o
    default — quem pediu explicitamente recebe o motivo exato;
  - Mock, `local_qa` e `local_model` têm binding próprio e fixo: identificador
    local jamais é tratado como modelo de provider externo.
"""

from __future__ import annotations

from app.modules.caller_identity.schemas import CallerRole
from app.modules.contracts import codes
from app.modules.provider_binding.schemas import (
    BindingValidation,
    ModelSource,
    ProviderModelBinding,
    SelectedProviderModel,
)
from app.modules.provider_catalog.schemas import ProviderCategory
from app.modules.provider_catalog.service import provider_catalog_service

SELECTION_MODE_AUTO = "auto"

MODEL_UNKNOWN_REASON = (
    "Modelo não reconhecido pelo catálogo do PedroCore; combinação rejeitada."
)
MODEL_PROVIDER_MISMATCH_REASON = (
    "Modelo não pertence ao provider solicitado; provider e modelo são uma "
    "unidade e não podem ser combinados livremente."
)
MODEL_NOT_AUTHORIZED_REASON = (
    "Modelo não homologado para uso real; combinação rejeitada até homologação "
    "explícita."
)
MODEL_TASK_INCOMPATIBLE_REASON = (
    "Modelo não é compatível com a task solicitada; combinação rejeitada."
)
MODEL_NOT_ALLOWED_FOR_CALLER_REASON = (
    "Consumidor comum não define modelo: a seleção pertence ao PedroCore."
)
MODEL_NOT_ALLOWED_IN_AUTO_REASON = (
    "Modelo não é aceito em provider=auto: o modelo nunca seleciona provider "
    "nem influencia o roteamento automático."
)
MODEL_DEFAULT_UNAVAILABLE_REASON = (
    "Provider sem modelo default válido no catálogo; nenhum modelo foi "
    "selecionado pelo PedroCore nesta requisição."
)


class ProviderBindingService:
    """Valida provider+modelo antes de qualquer adapter ser tocado."""

    def resolve(
        self,
        *,
        requested_provider: str,
        requested_model: str | None,
        selection_mode: str,
        caller_role: CallerRole,
        task_type: str,
        auto_candidate: str | None = None,
    ) -> SelectedProviderModel:
        requested = (requested_provider or "").strip().lower()
        model = (requested_model or "").strip() or None

        def invalid(error_code: str, reason: str) -> SelectedProviderModel:
            return SelectedProviderModel(
                selection_mode=selection_mode,
                requested_provider=requested,
                requested_model=model,
                validation_result=BindingValidation.INVALID,
                error_code=error_code,
                reason=reason,
            )

        # --------------------------------------------------------------
        # provider=auto: o modelo do payload nunca entra na decisão.
        # --------------------------------------------------------------
        if selection_mode == SELECTION_MODE_AUTO:
            if model is not None:
                error_code = (
                    codes.MODEL_NOT_ALLOWED_FOR_CALLER
                    if caller_role is CallerRole.COMMON_CONSUMER
                    else codes.MODEL_NOT_ALLOWED_IN_AUTO
                )
                reason = (
                    MODEL_NOT_ALLOWED_FOR_CALLER_REASON
                    if caller_role is CallerRole.COMMON_CONSUMER
                    else MODEL_NOT_ALLOWED_IN_AUTO_REASON
                )
                return invalid(error_code, reason)
            return self._bind_default(
                provider_id=auto_candidate,
                selection_mode=selection_mode,
                requested_provider=requested,
            )

        # --------------------------------------------------------------
        # Seleção explícita.
        # --------------------------------------------------------------
        if model is not None and caller_role is CallerRole.COMMON_CONSUMER:
            return invalid(
                codes.MODEL_NOT_ALLOWED_FOR_CALLER, MODEL_NOT_ALLOWED_FOR_CALLER_REASON
            )

        definition = provider_catalog_service.get(requested)
        if definition is None:
            # Provider fora do catálogo: o pipeline preexistente já trata como
            # provider não suportado (fallback Mock seguro, sem adapter real).
            return SelectedProviderModel(
                selection_mode=selection_mode,
                requested_provider=requested,
                requested_model=model,
                model_source=ModelSource.NOT_SELECTED,
            )

        if model is None:
            return self._bind_default(
                provider_id=requested,
                selection_mode=selection_mode,
                requested_provider=requested,
            )

        known = provider_catalog_service.find_model(model)
        if not known:
            return invalid(codes.MODEL_UNKNOWN, MODEL_UNKNOWN_REASON)

        owned = [item for item in known if item.provider_id == definition.provider_id]
        if not owned:
            return invalid(codes.MODEL_PROVIDER_MISMATCH, MODEL_PROVIDER_MISMATCH_REASON)

        model_definition = owned[0]
        if (
            definition.category is ProviderCategory.REAL_EXTERNAL
            and not model_definition.homologated
        ):
            return invalid(codes.MODEL_NOT_AUTHORIZED, MODEL_NOT_AUTHORIZED_REASON)

        if not model_definition.supports_task(task_type):
            return invalid(codes.MODEL_TASK_INCOMPATIBLE, MODEL_TASK_INCOMPATIBLE_REASON)

        source = (
            ModelSource.LOCAL_FIXED
            if definition.category is not ProviderCategory.REAL_EXTERNAL
            else ModelSource.EXPLICIT_TECHNICAL
        )
        return SelectedProviderModel(
            selection_mode=selection_mode,
            requested_provider=requested,
            requested_model=model,
            provider_id=definition.provider_id,
            model_id=model_definition.model_id,
            model_source=source,
            binding=self._binding(definition, model_definition, source),
        )

    # ------------------------------------------------------------------
    def _bind_default(
        self,
        *,
        provider_id: str | None,
        selection_mode: str,
        requested_provider: str,
    ) -> SelectedProviderModel:
        """Modelo derivado internamente: default declarado no catálogo."""
        definition = provider_catalog_service.get(provider_id)
        if definition is None:
            return SelectedProviderModel(
                selection_mode=selection_mode,
                requested_provider=requested_provider,
                model_source=ModelSource.NOT_SELECTED,
            )

        model_definition = provider_catalog_service.default_model_for(provider_id)
        if model_definition is None:
            # Degradação honesta: sem default válido o adapter mantém o
            # comportamento preexistente, e o motivo fica registrado.
            return SelectedProviderModel(
                selection_mode=selection_mode,
                requested_provider=requested_provider,
                provider_id=definition.provider_id,
                model_source=ModelSource.NOT_SELECTED,
                warning_code=codes.MODEL_DEFAULT_UNAVAILABLE,
                warning_reason=MODEL_DEFAULT_UNAVAILABLE_REASON,
            )

        source = (
            ModelSource.LOCAL_FIXED
            if definition.category is not ProviderCategory.REAL_EXTERNAL
            else ModelSource.PROVIDER_DEFAULT
        )
        return SelectedProviderModel(
            selection_mode=selection_mode,
            requested_provider=requested_provider,
            provider_id=definition.provider_id,
            model_id=model_definition.model_id,
            model_source=source,
            binding=self._binding(definition, model_definition, source),
        )

    @staticmethod
    def _binding(definition, model_definition, source: ModelSource) -> ProviderModelBinding:
        is_real = definition.category is ProviderCategory.REAL_EXTERNAL
        return ProviderModelBinding(
            provider_id=definition.provider_id,
            model_id=model_definition.model_id,
            adapter_id=definition.adapter,
            capabilities=definition.capabilities,
            compatible_tasks=definition.compatible_tasks,
            configured=definition.configured,
            homologated=model_definition.homologated,
            authorized=model_definition.homologated or not is_real,
            default_for_provider=model_definition.default_for_provider,
            source=source,
        )


provider_binding_service = ProviderBindingService()

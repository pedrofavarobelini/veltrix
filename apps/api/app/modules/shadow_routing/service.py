"""Serviço de política shadow (Etapa 4).

Política determinística, sem qualquer sinal dinâmico:

    filtros eliminatórios → prioridade estática por projeto/task → desempate

Não há score, custo, latência, health, estatística, aprendizado, A/B, ensemble,
votação, execução paralela ou comparação de respostas. Nenhum provider é
chamado: a decisão é calculada apenas a partir do catálogo, da identidade, da
autorização e do binding já existentes.

Claude e OpenAI aparecem como candidatos conhecidos e potencialmente
priorizados, mas são eliminados pelo motivo correto — nunca executados e nunca
autorizados artificialmente para produzir uma decisão diferente.
"""

from __future__ import annotations

import os

from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.provider_authorization.service import provider_authorization_service
from app.modules.provider_binding.service import provider_binding_service
from app.modules.provider_catalog.schemas import ProviderCategory
from app.modules.provider_catalog.service import provider_catalog_service
from app.modules.shadow_routing.schemas import (
    POLICY_VERSION,
    EliminationReason,
    ShadowCandidate,
    ShadowRoutingDecision,
)

FLAG_SHADOW_ROUTING = "PEDROCORE_SHADOW_ROUTING_ENABLED"

# Prioridade estática, declarada em código e ordenada: nada é derivado de
# métrica dinâmica. Tuplas garantem ordem estável, sem depender de dict/set.
_PRIORITY_BY_PROJECT_TASK: dict[tuple[str, str], tuple[str, ...]] = {
    ("finguard", "assistant_chat"): ("gemini", "claude", "openai"),
    ("finguard", "finance_advice"): ("gemini", "claude", "openai"),
}

_PRIORITY_BY_PROJECT: dict[str, tuple[str, ...]] = {
    "finguard": ("gemini", "claude", "openai"),
    "finguard-local": ("gemini", "claude", "openai"),
    "pedrocore": ("gemini", "claude", "openai"),
}

_DEFAULT_PRIORITY: tuple[str, ...] = ("gemini", "claude", "openai")

SELECTED_REASON = "Primeiro candidato da prioridade estática que passou por todos os filtros."
NO_CANDIDATE_REASON = "Nenhum candidato sobreviveu aos filtros eliminatórios."
DISABLED_REASON = "Shadow mode desativado."


class ShadowRoutingService:
    """Calcula a decisão planejada. Nunca executa e nunca altera a real."""

    def enabled(self) -> bool:
        return (os.environ.get(FLAG_SHADOW_ROUTING) or "").strip().lower() == "true"

    def policy_version(self) -> str:
        return POLICY_VERSION

    def priority_for(self, project_id: str, task_type: str) -> tuple[str, ...]:
        project = (project_id or "").strip().lower()
        task = (task_type or "").strip().lower()
        by_task = _PRIORITY_BY_PROJECT_TASK.get((project, task))
        if by_task is not None:
            return by_task
        return _PRIORITY_BY_PROJECT.get(project, _DEFAULT_PRIORITY)

    def evaluate(
        self,
        *,
        caller: AuthenticatedCallerContext,
        identity_project_id: str,
        context_project_id: str,
        task_type: str,
        allow_real_provider: bool,
        policy_allowed: bool = True,
    ) -> ShadowRoutingDecision:
        """Decisão planejada; sem efeito algum sobre a execução real."""
        if not self.enabled():
            return ShadowRoutingDecision(
                enabled=False,
                project_id=context_project_id,
                task_type=task_type,
                selection_reason=DISABLED_REASON,
            )

        candidates: list[ShadowCandidate] = []
        selected: ShadowCandidate | None = None

        for priority, provider_id in enumerate(
            self.priority_for(context_project_id, task_type)
        ):
            reason, model_id = self._evaluate_candidate(
                provider_id=provider_id,
                caller=caller,
                identity_project_id=identity_project_id,
                task_type=task_type,
                allow_real_provider=allow_real_provider,
                policy_allowed=policy_allowed,
            )
            candidate = ShadowCandidate(
                provider_id=provider_id,
                model_id=model_id,
                priority=priority,
                eliminated=reason is not None,
                elimination_reason=reason,
            )
            candidates.append(candidate)
            # Desempate determinístico: vence o primeiro sobrevivente na ordem
            # estática declarada; empate de prioridade não existe por construção.
            if reason is None and selected is None:
                selected = candidate

        eliminated = tuple(item for item in candidates if item.eliminated)
        return ShadowRoutingDecision(
            enabled=True,
            project_id=context_project_id,
            task_type=task_type,
            candidates_considered=tuple(candidates),
            candidates_eliminated=eliminated,
            selected_provider=selected.provider_id if selected else None,
            selected_model=selected.model_id if selected else None,
            selection_reason=SELECTED_REASON if selected else NO_CANDIDATE_REASON,
            policy_version=POLICY_VERSION,
        )

    def compare_with_actual(
        self,
        decision: ShadowRoutingDecision,
        *,
        actual_provider: str | None,
        actual_model: str | None,
    ) -> ShadowRoutingDecision:
        """Compara identificadores; nunca executa o candidato planejado."""
        if not decision.enabled:
            return decision
        differs = (decision.selected_provider != actual_provider) or (
            decision.selected_model != actual_model
        )
        return decision.model_copy(update={"would_differ_from_actual": differs})

    # ------------------------------------------------------------------
    def _evaluate_candidate(
        self,
        *,
        provider_id: str,
        caller: AuthenticatedCallerContext,
        identity_project_id: str,
        task_type: str,
        allow_real_provider: bool,
        policy_allowed: bool,
    ) -> tuple[EliminationReason | None, str | None]:
        definition = provider_catalog_service.get(provider_id)
        if definition is None or not definition.registered:
            return EliminationReason.NOT_REGISTERED, None
        if not definition.implemented:
            return EliminationReason.NOT_IMPLEMENTED, None
        if not definition.configured:
            return EliminationReason.NOT_CONFIGURED, None
        if not definition.is_approved_for_production:
            return EliminationReason.NOT_HOMOLOGATED, None

        is_real = definition.category is ProviderCategory.REAL_EXTERNAL
        if is_real and caller.identity_strength is IdentityStrength.AMBIGUOUS:
            return EliminationReason.AMBIGUOUS_IDENTITY, None

        decision = provider_authorization_service.evaluate(
            identity_strength=caller.identity_strength,
            project_id=identity_project_id,
            caller_role=caller.caller_role,
            environment=caller.environment,
            provider_id=provider_id,
        )
        if decision.denied:
            return EliminationReason.NOT_AUTHORIZED, None

        if not definition.supports_task(task_type):
            return EliminationReason.TASK_INCOMPATIBLE, None

        if not policy_allowed:
            return EliminationReason.PROJECT_POLICY_BLOCKED, None

        model = provider_catalog_service.default_model_for(provider_id)
        if model is None or not model.supports_task(task_type):
            return EliminationReason.MODEL_INCOMPATIBLE, None

        binding = provider_binding_service.resolve(
            requested_provider=provider_id,
            requested_model=None,
            selection_mode="explicit",
            caller_role=CallerRole.TECHNICAL_TOOL,
            task_type=task_type,
        )
        if binding.invalid or binding.model_id is None:
            return EliminationReason.MODEL_INCOMPATIBLE, None

        if is_real and not allow_real_provider:
            return EliminationReason.SAFE_MODE_BLOCKED, binding.model_id

        return None, binding.model_id


shadow_routing_service = ShadowRoutingService()

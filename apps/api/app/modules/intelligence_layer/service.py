from app.modules.intelligence_layer.schemas import (
    IntelligenceContextPolicy,
    IntelligencePlan,
)
from app.modules.project_context.schemas import ProjectContext
from app.modules.task_router.schemas import TaskStrategy

# Intelligence Layer (fundação — PEDROCORE-MODEL-FOUNDATION-01).
#
# Camada determinística que prepara a decisão cognitiva/operacional ANTES do
# provider. Regras absolutas desta fundação:
#   - nunca chama provider (local ou real);
#   - nunca habilita allow_real_provider=true;
#   - nunca altera prompt de produção automaticamente;
#   - nunca persiste memória;
#   - é testável isoladamente.
#
# Nesta frente o plano é anexado ao OrchestrationOutcome apenas como metadado
# interno; a conexão com o Prompt Builder fica para a próxima frente.

SAFETY_FLAG_REAL_PROVIDER_BLOCKED = "provider_real_blocked_by_default"
SAFETY_FLAG_CRITICAL_TASK = "critical_task_requires_conservative_handling"
SAFETY_FLAG_HUMAN_REVIEW = "human_review_required"
SAFETY_FLAG_READ_ONLY_PROJECT = "project_is_read_only"
SAFETY_FLAG_NO_TRAINING = "report_memory_is_not_training"

# Mapeamento determinístico task_type -> response_profile.
_TASK_PROFILES: dict[str, str] = {
    "general_chat": "general_assistant",
    "technical_explanation": "technical_direct",
    "code_help": "technical_direct",
    "qa_report_analysis": "qa_strict",
    "qa_failure_diagnosis": "qa_strict",
    "release_gate_review": "release_gate_strict",
    "artifact_summary": "executive_summary",
    "exploratory_test_plan": "implementation_plan",
    "manual_exploration_report": "qa_strict",
    "assisted_exploration_review": "qa_strict",
    "report_ingestion": "executive_summary",
    "project_memory_summary": "executive_summary",
    "model_foundation_review": "technical_direct",
    "intelligence_planning": "implementation_plan",
    # ECOSYSTEM-INTELLIGENCE-SUITE-01: tasks de assistente/ecossistema.
    "assistant_chat": "general_assistant",
    "ecosystem_assistant": "general_assistant",
    "finance_advice": "financial_cautious",
    "project_status": "executive_summary",
    "report_memory_query": "executive_summary",
    "local_model_chat": "general_assistant",
    "evaluation_run": "technical_direct",
    "wellbeing_report_interpretation": "wellbeing_non_clinical",
    "unknown": "general_assistant",
}

# Tasks cuja fundação futura poderá usar contexto de relatórios técnicos.
_REPORT_CONTEXT_TASKS = {
    "report_ingestion",
    "project_memory_summary",
    "report_memory_query",
    "project_status",
    "qa_report_analysis",
    "qa_failure_diagnosis",
    "release_gate_review",
    "wellbeing_report_interpretation",
}

BASE_INSTRUCTIONS = [
    "Não executar comandos, não escrever arquivos e não deletar nada.",
    "Não tratar resposta Mock/fallback como validação real em tarefa crítica.",
    "Provider real permanece bloqueado por padrão (allow_real_provider=false).",
]


class IntelligenceLayerService:
    def build_plan(
        self,
        strategy: TaskStrategy,
        project: ProjectContext,
    ) -> IntelligencePlan:
        """Constrói o plano determinístico para a task, sem efeitos colaterais."""
        task_type = strategy.task_type
        profile = _TASK_PROFILES.get(task_type, "general_assistant")
        is_critical = strategy.criticality in {"high", "critical"}
        requires_human_review = strategy.criticality == "critical" or (
            is_critical and not strategy.allow_mock
        )

        context_policy = IntelligenceContextPolicy(
            allow_memory_context=False,
            allow_project_context=True,
            allow_report_context=task_type in _REPORT_CONTEXT_TASKS,
            allow_real_provider=False,
            requires_human_review=requires_human_review,
            sensitive_data_policy="sanitize",
        )

        safety_flags = [SAFETY_FLAG_REAL_PROVIDER_BLOCKED]
        if is_critical:
            safety_flags.append(SAFETY_FLAG_CRITICAL_TASK)
        if requires_human_review:
            safety_flags.append(SAFETY_FLAG_HUMAN_REVIEW)
        if project.read_only:
            safety_flags.append(SAFETY_FLAG_READ_ONLY_PROJECT)
        if context_policy.allow_report_context:
            safety_flags.append(SAFETY_FLAG_NO_TRAINING)

        instructions = list(BASE_INSTRUCTIONS)
        if profile == "release_gate_strict":
            instructions.append(
                "Release gate só pode ser aprovado com evidência determinística "
                "(local_qa); provider real nunca aprova sozinho."
            )
        if profile == "qa_strict":
            instructions.append(
                "Responder em formato estruturado, conservador e explicável, "
                "sem inferir sucesso sem evidência."
            )
        if profile == "financial_cautious":
            instructions.append(
                "Resposta financeira deve ser conservadora e informativa: "
                "incluir disclaimer, nunca dar aconselhamento absoluto, "
                "nunca executar ação financeira e nunca alterar dados."
            )
        if profile == "wellbeing_non_clinical":
            instructions.extend(
                [
                    "Interpretar somente métricas já calculadas pela Elyra; não recalcular.",
                    "Não diagnosticar, prescrever ou afirmar condição clínica.",
                    "Não tratar emoção facial como fato nem associação como causalidade.",
                ]
            )

        memory_hints: list[str] = []
        if context_policy.allow_report_context:
            memory_hints.append(
                "Memória técnica futura: sinais de relatórios poderão virar "
                "contexto nesta task; nenhuma persistência ocorre nesta fase."
            )

        evaluation_hints: list[str] = []
        if is_critical:
            evaluation_hints.append(
                "Avaliar coerência e segurança da resposta antes de uso; "
                "sinais críticos exigem revisão humana."
            )
        if requires_human_review:
            evaluation_hints.append(
                "Decisão final desta task exige revisão humana explícita."
            )

        return IntelligencePlan(
            task_type=task_type,
            response_profile=profile,
            context_policy=context_policy,
            safety_flags=safety_flags,
            instructions=instructions,
            memory_hints=memory_hints,
            evaluation_hints=evaluation_hints,
        )


intelligence_layer_service = IntelligenceLayerService()

from app.modules.task_router.schemas import TaskStrategy

DEFAULT_TASK_TYPE = "general_chat"
UNKNOWN_TASK_TYPE = "unknown"

CRITICAL_TASK_TYPES = {
    "qa_report_analysis",
    "qa_failure_diagnosis",
    "release_gate_review",
}

FALLBACK_CRITICAL_WARNING = (
    "Fallback Mock usado em tarefa crítica; "
    "resultado não deve ser tratado como validação real."
)

MOCK_CRITICAL_WARNING = (
    "MockProvider usado em tarefa crítica; "
    "resultado não deve ser tratado como validação real."
)

_STRATEGIES: dict[str, dict[str, object]] = {
    "general_chat": {
        "response_style": "free_text",
        "requires_structured_response": False,
        "criticality": "low",
        "allow_mock": True,
    },
    "technical_explanation": {
        "response_style": "technical_text",
        "requires_structured_response": False,
        "criticality": "low",
        "allow_mock": True,
    },
    "code_help": {
        "response_style": "code_oriented",
        "requires_structured_response": False,
        "criticality": "medium",
        "allow_mock": True,
    },
    "qa_report_analysis": {
        "response_style": "qa_structured_planned",
        "requires_structured_response": True,
        "criticality": "high",
        "allow_mock": False,
    },
    "qa_failure_diagnosis": {
        "response_style": "qa_structured_planned",
        "requires_structured_response": True,
        "criticality": "high",
        "allow_mock": False,
    },
    "release_gate_review": {
        "response_style": "release_gate_structured_planned",
        "requires_structured_response": True,
        "criticality": "critical",
        "allow_mock": False,
    },
    "artifact_summary": {
        "response_style": "artifact_summary",
        "requires_structured_response": False,
        "criticality": "medium",
        "allow_mock": True,
    },
    "exploratory_test_plan": {
        "response_style": "exploration_plan_structured",
        "requires_structured_response": True,
        "criticality": "medium",
        "allow_mock": True,
    },
    "manual_exploration_report": {
        "response_style": "exploration_plan_structured",
        "requires_structured_response": True,
        "criticality": "medium",
        "allow_mock": True,
    },
    "assisted_exploration_review": {
        "response_style": "exploration_plan_structured",
        "requires_structured_response": True,
        "criticality": "high",
        "allow_mock": True,
    },
    # PEDROCORE-MODEL-FOUNDATION-01: tasks de fundação de inteligência.
    # Planejamento/documentação, sem execução; mock permitido.
    "report_ingestion": {
        "response_style": "report_structured",
        "requires_structured_response": True,
        "criticality": "medium",
        "allow_mock": True,
    },
    "project_memory_summary": {
        "response_style": "report_structured",
        "requires_structured_response": True,
        "criticality": "medium",
        "allow_mock": True,
    },
    "model_foundation_review": {
        "response_style": "technical_text",
        "requires_structured_response": False,
        "criticality": "medium",
        "allow_mock": True,
    },
    "intelligence_planning": {
        "response_style": "plan_structured",
        "requires_structured_response": True,
        "criticality": "medium",
        "allow_mock": True,
    },
    # ECOSYSTEM-INTELLIGENCE-SUITE-01: tasks de assistente/ecossistema.
    # Todas read-only, sem execução; provider real segue bloqueado por padrão.
    "assistant_chat": {
        "response_style": "assistant_text",
        "requires_structured_response": False,
        "criticality": "low",
        "allow_mock": True,
    },
    "ecosystem_assistant": {
        "response_style": "assistant_text",
        "requires_structured_response": False,
        "criticality": "low",
        "allow_mock": True,
    },
    # finance_advice é conservador: read-only, com disclaimer obrigatório,
    # nunca executa ação financeira nem altera dados.
    "finance_advice": {
        "response_style": "financial_cautious",
        "requires_structured_response": False,
        "criticality": "medium",
        "allow_mock": True,
    },
    "project_status": {
        "response_style": "report_structured",
        "requires_structured_response": True,
        "criticality": "medium",
        "allow_mock": True,
    },
    "report_memory_query": {
        "response_style": "report_structured",
        "requires_structured_response": True,
        "criticality": "medium",
        "allow_mock": True,
    },
    "local_model_chat": {
        "response_style": "free_text",
        "requires_structured_response": False,
        "criticality": "low",
        "allow_mock": True,
    },
    "evaluation_run": {
        "response_style": "plan_structured",
        "requires_structured_response": True,
        "criticality": "medium",
        "allow_mock": True,
    },
    UNKNOWN_TASK_TYPE: {
        "response_style": "free_text",
        "requires_structured_response": False,
        "criticality": "low",
        "allow_mock": True,
    },
}


class TaskRouter:
    def resolve(self, task_type: str | None) -> TaskStrategy:
        normalized = (task_type or DEFAULT_TASK_TYPE).strip().lower()

        if not normalized:
            normalized = DEFAULT_TASK_TYPE

        warnings: list[str] = []
        config = _STRATEGIES.get(normalized)

        if config is None:
            warnings.append(
                f"task_type desconhecido: '{normalized}'. Tratado como '{UNKNOWN_TASK_TYPE}'."
            )
            normalized = UNKNOWN_TASK_TYPE
            config = _STRATEGIES[UNKNOWN_TASK_TYPE]

        return TaskStrategy(task_type=normalized, warnings=warnings, **config)


task_router = TaskRouter()

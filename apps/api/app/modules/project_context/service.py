from app.modules.project_context.schemas import ProjectContext, TaskPolicyResult

DEFAULT_PROJECT_ID = "pedrocore"
UNKNOWN_PROJECT_ID = "unknown"

UNKNOWN_SYSTEM_WARNING = (
    "Sistema de origem desconhecido; tratado como 'unknown' com limites restritivos."
)

TASK_NOT_ALLOWED_WARNING = (
    "task_type não listado em allowed_tasks do projeto; "
    "resultado deve ser tratado com cautela."
)

EMPTY_ALLOWED_TASKS_WARNING = (
    "Projeto sem lista de tarefas permitidas; "
    "task_type aceito sem validação rígida nesta etapa."
)

UNKNOWN_PROJECT_POLICY_WARNING = (
    "Sistema de origem desconhecido; task_type não validado contra política de projeto."
)

_FINGUARD_ALLOWED_TASKS = [
    "qa_report_analysis",
    "qa_failure_diagnosis",
    "release_gate_review",
    "exploratory_test_plan",
    "manual_exploration_report",
    "assisted_exploration_review",
    "artifact_summary",
    "technical_explanation",
    # ECOSYSTEM-INTELLIGENCE-SUITE-01: FinGuard como CONSUMIDOR read-only do
    # assistente de ecossistema — sem execução, sem escrita, sem leitura de
    # repositório; a integração real pertence a FINGUARD-PEDROCORE-ASSISTANT-01.
    "assistant_chat",
    "finance_advice",
    "project_status",
    "report_memory_query",
]

_FINGUARD_NOTES = (
    "Projeto externo; QA Automation pertence ao FinGuard; "
    "o PedroCore recebe apenas artefatos por payload (contrato fake nesta fase), "
    "sem leitura direta de repositório, sem execução de comandos e sem escrita."
)

_PROJECTS: dict[str, dict[str, object]] = {
    "pedrocore": {
        "display_name": "PedroCore IA",
        "allowed_tasks": [
            "general_chat",
            "technical_explanation",
            "code_help",
            "artifact_summary",
            "qa_report_analysis",
            "qa_failure_diagnosis",
            "release_gate_review",
            "exploratory_test_plan",
            "manual_exploration_report",
            "assisted_exploration_review",
            # PEDROCORE-MODEL-FOUNDATION-01: tasks de fundação de inteligência
            # (somente pedrocore; FinGuard não recebe essas tasks nesta frente).
            "report_ingestion",
            "project_memory_summary",
            "model_foundation_review",
            "intelligence_planning",
            # ECOSYSTEM-INTELLIGENCE-SUITE-01: tasks de assistente/ecossistema.
            "assistant_chat",
            "ecosystem_assistant",
            "finance_advice",
            "project_status",
            "report_memory_query",
            "local_model_chat",
            "evaluation_run",
        ],
        "notes": "Sistema local/default do próprio PedroCore.",
    },
    "finguard": {
        "display_name": "FinGuard",
        "allowed_tasks": list(_FINGUARD_ALLOWED_TASKS),
        "notes": _FINGUARD_NOTES,
    },
    "finguard-local": {
        "display_name": "FinGuard (ambiente local)",
        "allowed_tasks": list(_FINGUARD_ALLOWED_TASKS),
        "notes": _FINGUARD_NOTES,
    },
}

# Origens tratadas como FinGuard: sempre read-only, sem reader, sem execução.
FINGUARD_ORIGIN_SYSTEMS = {"finguard", "finguard-local"}


class ProjectContextResolver:
    def resolve(self, origin_system: str | None) -> ProjectContext:
        normalized = (origin_system or DEFAULT_PROJECT_ID).strip().lower()

        if not normalized:
            normalized = DEFAULT_PROJECT_ID

        config = _PROJECTS.get(normalized)

        if config is None:
            return ProjectContext(
                project_id=UNKNOWN_PROJECT_ID,
                display_name="Unknown external system",
                allowed_tasks=[],
                warnings=[UNKNOWN_SYSTEM_WARNING],
                notes=None,
            )

        return ProjectContext(project_id=normalized, warnings=[], **config)

    def evaluate_task_policy(
        self,
        project: ProjectContext,
        task_type: str,
    ) -> TaskPolicyResult:
        if not project.allowed_tasks:
            if project.project_id == UNKNOWN_PROJECT_ID:
                return TaskPolicyResult(
                    allowed=True,
                    warnings=[UNKNOWN_PROJECT_POLICY_WARNING],
                )
            return TaskPolicyResult(
                allowed=True,
                warnings=[EMPTY_ALLOWED_TASKS_WARNING],
            )

        if task_type in project.allowed_tasks:
            return TaskPolicyResult(allowed=True, warnings=[])

        return TaskPolicyResult(allowed=False, warnings=[TASK_NOT_ALLOWED_WARNING])


project_context_resolver = ProjectContextResolver()

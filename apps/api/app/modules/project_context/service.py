from app.modules.project_context.schemas import ProjectContext

DEFAULT_PROJECT_ID = "pedrocore"
UNKNOWN_PROJECT_ID = "unknown"

UNKNOWN_SYSTEM_WARNING = (
    "Sistema de origem desconhecido; tratado como 'unknown' com limites restritivos."
)

_PROJECTS: dict[str, dict[str, object]] = {
    "pedrocore": {
        "display_name": "PedroCore IA",
        "allowed_tasks": [
            "general_chat",
            "technical_explanation",
            "code_help",
            "artifact_summary",
        ],
        "notes": "Sistema local/default do próprio PedroCore.",
    },
    "finguard": {
        "display_name": "FinGuard",
        "allowed_tasks": [
            "qa_report_analysis",
            "qa_failure_diagnosis",
            "release_gate_review",
            "artifact_summary",
            "technical_explanation",
        ],
        "notes": (
            "Projeto externo; QA Automation pertence ao FinGuard; "
            "o PedroCore só pode receber/analisar artefatos enviados por payload no futuro."
        ),
    },
}


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


project_context_resolver = ProjectContextResolver()

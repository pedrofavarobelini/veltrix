from app.modules.project_context.service import (
    EMPTY_ALLOWED_TASKS_WARNING,
    TASK_NOT_ALLOWED_WARNING,
    UNKNOWN_PROJECT_POLICY_WARNING,
    project_context_resolver,
)


def test_resolves_pedrocore():
    project = project_context_resolver.resolve("pedrocore")

    assert project.project_id == "pedrocore"
    assert project.display_name == "PedroCore IA"
    assert project.read_only is True
    assert project.can_execute_commands is False
    assert project.can_write_files is False
    assert "general_chat" in project.allowed_tasks
    assert project.warnings == []


def test_resolves_finguard():
    project = project_context_resolver.resolve("finguard")

    assert project.project_id == "finguard"
    assert project.display_name == "FinGuard"
    assert project.read_only is True
    assert project.can_execute_commands is False
    assert project.can_write_files is False
    assert "qa_report_analysis" in project.allowed_tasks
    assert "release_gate_review" in project.allowed_tasks
    assert project.warnings == []
    assert "externo" in (project.notes or "")


def test_unknown_system_returns_unknown_with_warning():
    project = project_context_resolver.resolve("sistema_que_nao_existe")

    assert project.project_id == "unknown"
    assert project.read_only is True
    assert project.can_execute_commands is False
    assert project.can_write_files is False
    assert project.allowed_tasks == []
    assert any("desconhecido" in warning for warning in project.warnings)


def test_normalizes_case_whitespace_and_defaults():
    assert project_context_resolver.resolve("  FinGuard  ").project_id == "finguard"

    for value in (None, "", "   "):
        project = project_context_resolver.resolve(value)
        assert project.project_id == "pedrocore"
        assert project.warnings == []


def test_resolver_only_returns_data():
    project = project_context_resolver.resolve("finguard")

    assert project.model_dump() == {
        "project_id": "finguard",
        "display_name": "FinGuard",
        "read_only": True,
        "can_execute_commands": False,
        "can_write_files": False,
        "allowed_tasks": [
            "qa_report_analysis",
            "qa_failure_diagnosis",
            "release_gate_review",
            "exploratory_test_plan",
            "manual_exploration_report",
            "assisted_exploration_review",
            "artifact_summary",
            "technical_explanation",
            # ECOSYSTEM-INTELLIGENCE-SUITE-01: FinGuard como consumidor
            # read-only do assistente de ecossistema.
            "assistant_chat",
            "finance_advice",
            "project_status",
            "report_memory_query",
        ],
        "warnings": [],
        "notes": (
            "Projeto externo; QA Automation pertence ao FinGuard; "
            "o PedroCore recebe apenas artefatos por payload (contrato fake nesta fase), "
            "sem leitura direta de repositório, sem execução de comandos e sem escrita."
        ),
    }


def test_resolves_finguard_local_with_same_restrictions():
    project = project_context_resolver.resolve("finguard-local")

    assert project.project_id == "finguard-local"
    assert project.read_only is True
    assert project.can_execute_commands is False
    assert project.can_write_files is False
    assert "qa_report_analysis" in project.allowed_tasks
    assert "exploratory_test_plan" in project.allowed_tasks


def test_policy_allows_listed_task():
    project = project_context_resolver.resolve("finguard")
    policy = project_context_resolver.evaluate_task_policy(project, "qa_report_analysis")

    assert policy.allowed is True
    assert policy.warnings == []


def test_policy_warns_for_unlisted_task():
    project = project_context_resolver.resolve("finguard")
    policy = project_context_resolver.evaluate_task_policy(project, "general_chat")

    assert policy.allowed is False
    assert TASK_NOT_ALLOWED_WARNING in policy.warnings


def test_policy_warns_for_unknown_project():
    project = project_context_resolver.resolve("sistema_inexistente")
    policy = project_context_resolver.evaluate_task_policy(project, "general_chat")

    assert policy.allowed is True
    assert UNKNOWN_PROJECT_POLICY_WARNING in policy.warnings


def test_policy_warns_for_empty_allowed_tasks_on_known_project():
    project = project_context_resolver.resolve("pedrocore")
    project.allowed_tasks = []
    policy = project_context_resolver.evaluate_task_policy(project, "general_chat")

    assert policy.allowed is True
    assert EMPTY_ALLOWED_TASKS_WARNING in policy.warnings

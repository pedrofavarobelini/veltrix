from app.modules.project_context.service import project_context_resolver


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
            "artifact_summary",
            "technical_explanation",
        ],
        "warnings": [],
        "notes": (
            "Projeto externo; QA Automation pertence ao FinGuard; "
            "o PedroCore só pode receber/analisar artefatos enviados por payload no futuro."
        ),
    }

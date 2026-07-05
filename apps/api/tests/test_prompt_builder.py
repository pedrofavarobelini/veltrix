from app.modules.project_context.service import project_context_resolver
from app.modules.prompt_builder.schemas import PromptBuildInput
from app.modules.prompt_builder.service import prompt_builder
from app.modules.task_router.service import task_router


def build_input(
    task_type: str = "general_chat",
    origin_system: str = "pedrocore",
    message: str = "Mensagem de teste",
    system_prompt: str | None = None,
    context: dict | None = None,
    metadata: dict | None = None,
) -> PromptBuildInput:
    return PromptBuildInput(
        message=message,
        mode="tecnico",
        system_prompt=system_prompt,
        strategy=task_router.resolve(task_type),
        project=project_context_resolver.resolve(origin_system),
        origin_system=origin_system,
        context=context,
        metadata=metadata,
    )


def test_builds_prompt_for_general_chat():
    result = prompt_builder.build(build_input())

    assert "[Instruções do sistema]" in result.enriched_system_prompt
    assert "[Tarefa]" in result.enriched_system_prompt
    assert "[Regras de segurança]" in result.enriched_system_prompt
    assert "[Mensagem do usuário]" in result.full_prompt
    assert "Mensagem de teste" in result.full_prompt
    assert "Mensagem de teste" not in result.enriched_system_prompt


def test_includes_task_type_and_origin_system():
    result = prompt_builder.build(build_input(task_type="code_help", origin_system="pedrocore"))

    assert "task_type: code_help" in result.enriched_system_prompt
    assert "origin_system: pedrocore" in result.enriched_system_prompt
    assert "project_id: pedrocore" in result.enriched_system_prompt
    assert "display_name: PedroCore IA" in result.enriched_system_prompt


def test_includes_context_and_metadata_when_sent():
    result = prompt_builder.build(
        build_input(
            context={"module": "personal-finance"},
            metadata={"source": "manual-test"},
        )
    )

    assert '"module": "personal-finance"' in result.enriched_system_prompt
    assert '"source": "manual-test"' in result.enriched_system_prompt


def test_reports_absence_of_context_and_metadata():
    result = prompt_builder.build(build_input())

    assert "Nenhum contexto adicional foi enviado." in result.enriched_system_prompt
    assert "Nenhuma metadata adicional foi enviada." in result.enriched_system_prompt


def test_includes_criticality_for_qa_report_analysis():
    result = prompt_builder.build(
        build_input(task_type="qa_report_analysis", origin_system="finguard")
    )

    assert "task_type: qa_report_analysis" in result.enriched_system_prompt
    assert "criticality: high" in result.enriched_system_prompt
    assert "requires_structured_response: True" in result.enriched_system_prompt


def test_includes_project_limits():
    result = prompt_builder.build(build_input(origin_system="finguard"))

    assert "read_only: True" in result.enriched_system_prompt
    assert "can_execute_commands: False" in result.enriched_system_prompt
    assert "can_write_files: False" in result.enriched_system_prompt


def test_includes_finguard_security_rule():
    result = prompt_builder.build(build_input(origin_system="finguard"))

    assert (
        "O FinGuard é um projeto externo e somente leitura; não altere nada nele."
        in result.enriched_system_prompt
    )


def test_omits_finguard_rule_for_other_origins():
    result = prompt_builder.build(build_input(origin_system="pedrocore"))

    assert "FinGuard é um projeto externo" not in result.enriched_system_prompt


def test_preserves_original_system_prompt():
    result = prompt_builder.build(build_input(system_prompt="Prompt customizado do usuário."))

    assert "Prompt customizado do usuário." in result.enriched_system_prompt

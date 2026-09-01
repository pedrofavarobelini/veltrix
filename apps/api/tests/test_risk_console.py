"""Risk Console — CLI, TUI e apresentacao.

O que estes casos protegem
--------------------------

1. Que o console nao decide nada. O gate vem do core; a tela apenas mostra.
2. Que nenhum caminho executa a operacao analisada.
3. Que BLOCK fecha as duas acoes que transformariam analise em autorizacao —
   emitir contrato e copiar prompt aprovado — e que fecha no SERVICO, nao so
   no botao.
4. Que o vinculo entre prompt e analise nao sobrevive a uma edicao.
5. Que a interface esta em portugues.
6. Que erro operacional nao vaza segredo, caminho interno nem stack.

Os testes de TUI usam o harness do proprio Textual e verificam CONTEUDO, nao
captura de tela: largura de janela e fonte nao deveriam poder reprovar um
teste de idioma.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from app.modules.retrieval.schemas import RetrievalResponse
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_console import cli
from app.modules.risk_console.analysis import (
    ConsoleOperationError,
    analyze,
    approved_prompt,
    binding_signature,
    issue_contract,
)
from app.modules.risk_console.branding import COMMAND_NAME, PRODUCT_NAME, console_command
from app.modules.risk_console.domain import (
    ConsoleInputError,
    ConsoleRequestInput,
    available_projects,
    build_request,
    split_list,
)
from app.modules.risk_console.export import REDACTED, as_dict, redact
from app.modules.risk_console.presentation import GATE_LABELS
from app.modules.risk_console.render import render_analysis
from app.modules.risk_engine.execution_contract_schemas import RiskGate
from app.modules.risk_engine.execution_contract_service import FLAG_CONTRACT_SIGNING_KEY

PROJECT = "pedrocore"
SIGNING_KEY = "synthetic-console-signing-key-with-more-than-32-chars"


@pytest.fixture(autouse=True)
def quiet_retrieval(monkeypatch):
    """Sem histórico externo: cada caso mede o que ele mesmo declara."""
    monkeypatch.setattr(
        retrieval_service,
        "retrieve",
        lambda query, **_: RetrievalResponse(
            query_id=query.query_id, project_id=query.project_id
        ),
    )
    monkeypatch.setenv(FLAG_CONTRACT_SIGNING_KEY, SIGNING_KEY)


# --- entradas que produzem cada gate, com fatos reais ---------------------


def _clean(**overrides) -> ConsoleRequestInput:
    """Pedido bem declarado: alcança PASS sem que nada seja forçado."""
    values = dict(
        project_id=PROJECT,
        environment_label="Desenvolvimento",
        executor_label="Claude Code",
        prompt="Ler o relatorio de billing e auditar os totais",
        permissions=["read:billing"],
        allowed_scope=["module:billing"],
        targets=["module:billing"],
        required_tests=["billing"],
        constraints=["somente leitura"],
        acceptance_criteria=["nenhum dado alterado"],
        rollback_plan_present=True,
    )
    values.update(overrides)
    return ConsoleRequestInput(**values)


def _warnings() -> ConsoleRequestInput:
    """Pedido válido, porém pouco declarado: sinal MEDIUM, nada bloqueante."""
    return _clean(
        prompt="Alterar o modulo de billing conforme o criterio definido",
        permissions=["write:billing"],
        constraints=[],
        acceptance_criteria=[],
    )


def _review() -> ConsoleRequestInput:
    return _clean(
        prompt="Executar a migration para alterar o schema da tabela de billing",
        permissions=["migrate:billing"],
        database="pedrocore",
    )


def _blocked() -> ConsoleRequestInput:
    return _clean(
        prompt="Alterar o modulo de auth",
        permissions=["write:auth"],
        forbidden_scope=["module:auth"],
        targets=["module:auth"],
    )


# --- gates reais ----------------------------------------------------------


def test_the_four_gates_are_reachable_from_the_console():
    """Se um gate fosse inalcançável, ele nunca seria exercitado de verdade."""
    assert analyze(_clean()).gate is RiskGate.PASS
    assert analyze(_warnings()).gate is RiskGate.PASS_WITH_WARNINGS
    assert analyze(_review()).gate is RiskGate.REVIEW_REQUIRED
    assert analyze(_blocked()).gate is RiskGate.BLOCK


def test_no_console_path_executes_the_target_operation():
    for entry in (_clean(), _warnings(), _review(), _blocked()):
        result = analyze(entry)
        assert result.analysis.target_operation_executed is False
        assert result.analysis.provider_called is False
        assert all(item.mode == "analytical_dry_run" for item in result.analysis.simulations)


def test_the_console_does_not_invent_permissions_to_produce_a_pass():
    """Sem permissão declarada, o resultado honesto é BLOCK — e ele aparece."""
    result = analyze(_clean(permissions=[]))
    assert result.gate is RiskGate.BLOCK
    assert "PERMISSION_CONFLICT" in result.gate_reasons


# --- BLOCK fecha as portas ------------------------------------------------


def test_block_refuses_contract_in_the_service_not_only_in_the_button():
    """A recusa tem que valer para quem chama a função direto."""
    result = analyze(_blocked())
    with pytest.raises(ConsoleOperationError) as error:
        issue_contract(result)
    assert "bloqueada" in str(error.value).lower()


def test_block_refuses_the_approved_prompt():
    result = analyze(_blocked())
    with pytest.raises(ConsoleOperationError):
        approved_prompt(result)


def test_an_approved_analysis_issues_a_signed_contract():
    result = analyze(_clean())
    contract = issue_contract(result)
    assert contract.gate is RiskGate.PASS
    assert contract.integrity_signature.startswith("hmac-sha256:")


def test_a_missing_signing_key_is_reported_without_leaking_configuration(monkeypatch):
    monkeypatch.delenv(FLAG_CONTRACT_SIGNING_KEY, raising=False)
    result = analyze(_clean())
    with pytest.raises(ConsoleOperationError) as error:
        issue_contract(result)
    message = str(error.value)
    assert "PEDROCORE_RISK_CONTRACT_SIGNING_KEY" in message
    assert SIGNING_KEY not in message


# --- vinculo prompt <-> analise -------------------------------------------


def test_editing_the_prompt_invalidates_the_previous_approval():
    """analisa A -> edita para B -> copiar B como aprovado tem que falhar."""
    result = analyze(_clean())
    edited = build_request(_clean(prompt="Ler outro relatorio completamente diferente"))
    with pytest.raises(ConsoleOperationError) as error:
        approved_prompt(result, edited)
    assert "Reanalisar" in str(error.value)


def test_changing_scope_alone_also_breaks_the_binding():
    """O que foi aprovado não é só o texto: escopo e permissão fazem parte."""
    result = analyze(_clean())
    widened = build_request(_clean(allowed_scope=["module:billing", "module:auth"]))
    with pytest.raises(ConsoleOperationError):
        approved_prompt(result, widened)


def test_an_unchanged_form_keeps_the_binding_valid():
    result = analyze(_clean())
    same = build_request(_clean())
    assert result.matches(same)
    assert approved_prompt(result, same) == result.request.request_text


def test_the_binding_ignores_the_request_identifier():
    """Dois pedidos idênticos não podem parecer diferentes por causa do id."""
    first = build_request(_clean(request_id="console-a"))
    second = build_request(_clean(request_id="console-b"))
    assert binding_signature(first) == binding_signature(second)


# --- entrada --------------------------------------------------------------


def test_an_empty_prompt_is_refused_in_portuguese():
    with pytest.raises(ConsoleInputError) as error:
        build_request(_clean(prompt="   "))
    assert "Prompt vazio" in str(error.value)


def test_a_project_without_the_capability_is_refused():
    with pytest.raises(ConsoleInputError) as error:
        build_request(_clean(project_id="structa"))
    assert "risk_analysis" in str(error.value)


def test_an_invalid_environment_is_refused():
    with pytest.raises(ConsoleInputError) as error:
        build_request(_clean(environment_label="Homologação"))
    assert "Ambiente inválido" in str(error.value)


def test_a_prompt_over_the_engine_limit_is_refused_instead_of_truncated():
    """Cortar em silêncio mudaria o que foi analisado sem o usuário saber."""
    with pytest.raises(ConsoleInputError) as error:
        build_request(_clean(prompt="a" * 5000))
    assert "excede o limite" in str(error.value)


def test_multiline_prompt_is_preserved():
    text = "Primeira linha\nSegunda linha\nTerceira linha"
    assert build_request(_clean(prompt=text)).request_text == text


def test_only_projects_declaring_the_capability_are_offered():
    assert PROJECT in available_projects()
    assert "structa" not in available_projects()


def test_split_list_accepts_commas_and_newlines():
    assert split_list("a, b\nc ,, ") == ["a", "b", "c"]


# --- apresentacao em PT-BR ------------------------------------------------


def test_every_gate_has_a_portuguese_label():
    assert GATE_LABELS[RiskGate.PASS] == "APROVADO"
    assert GATE_LABELS[RiskGate.PASS_WITH_WARNINGS] == "APROVADO COM AVISOS"
    assert GATE_LABELS[RiskGate.REVIEW_REQUIRED] == "REVISÃO OBRIGATÓRIA"
    assert GATE_LABELS[RiskGate.BLOCK] == "BLOQUEADO"


def test_the_internal_gate_enum_was_not_translated():
    """Traduzir o contrato para caber na tela seria mudar a lei pelo cartaz."""
    assert {item.value for item in RiskGate} == {
        "PASS",
        "PASS_WITH_WARNINGS",
        "REVIEW_REQUIRED",
        "BLOCK",
    }


def test_the_report_is_written_in_portuguese():
    text = render_analysis(analyze(_review()))
    for section in (
        "INTENÇÃO",
        "QUALIDADE DO PROMPT",
        "RAIO DE IMPACTO",
        "DIMENSÕES DE RISCO",
        "SIMULAÇÃO DE CENÁRIOS",
        "ACHADOS",
        "RECOMENDAÇÕES",
        "GATE FINAL",
    ):
        assert section in text


def test_a_blocked_report_says_so_plainly():
    text = render_analysis(analyze(_blocked()))
    assert "BLOQUEADO" in text
    assert "EXECUÇÃO BLOQUEADA" in text


def test_the_report_shows_the_blast_radius_metric():
    text = render_analysis(analyze(_review()))
    assert "Amplitude de fronteiras" in text
    assert "Extensão de itens" in text


def test_historical_section_is_absent_when_there_is_no_history():
    """Seção vazia preenchida com zeros seria indistinguível de dado real."""
    assert "EVIDÊNCIA HISTÓRICA" not in render_analysis(analyze(_clean()))


def test_recommendations_are_derived_from_real_facts():
    result = analyze(_blocked())
    bases = {item.basis for item in result.recommendations}
    assert "scope.forbidden_targets" in bases
    assert all(item.text for item in result.recommendations)


def test_a_clean_analysis_does_not_manufacture_recommendations():
    result = analyze(_clean())
    assert len(result.recommendations) <= 1


# --- exportacao sanitizada ------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "use api_key=ABCDEFGHIJKLMNOPQRSTUVWX",
        "conecte em postgres://user:supersecret@host:5432/db",
        "o token sk-abcdefghijklmnopqrstuvwx",
        "Authorization: Bearer abcdefghijklmnopqrstuvwx",
    ],
)
def test_export_redacts_secrets_typed_into_the_prompt(text):
    assert REDACTED in redact(text)


def test_export_keeps_the_useful_text_around_the_redaction():
    cleaned = redact("altere o billing com api_key=ABCDEFGHIJKLMNOPQRSTUV depois rode os testes")
    assert "altere o billing" in cleaned
    assert "ABCDEFGHIJKLMNOPQRSTUV" not in cleaned


def test_export_is_serialisable_and_declares_no_execution():
    data = as_dict(analyze(_review()))
    assert data["operacao_alvo_executada"] is False
    assert data["provider_chamado"] is False
    json.dumps(data, ensure_ascii=False)


# --- CLI ------------------------------------------------------------------


class _Capture:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, text: str) -> int:
        self.lines.append(text)
        return len(text)

    def flush(self) -> None:
        return None

    @property
    def text(self) -> str:
        return "".join(self.lines)


def _run_cli(*argv) -> tuple[int, str]:
    stream = _Capture()
    code = cli.main(list(argv), stream=stream)
    return code, stream.text


def _prompt_file(tmp_path, text: str):
    path = tmp_path / "prompt.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_cli_inspect_lists_real_options():
    code, output = _run_cli("risk", "inspect", "--json")
    data = json.loads(output)
    assert code == cli.EXIT_OK
    assert data["projetos"] == list(available_projects())
    assert data["comando"] == console_command()


def test_cli_analyze_reads_a_file(tmp_path):
    code, output = _run_cli(
        "risk",
        "analyze",
        _prompt_file(tmp_path, "Ler o relatorio de billing e auditar os totais"),
        "--permissions",
        "read:billing",
        "--allowed-scope",
        "module:billing",
        "--targets",
        "module:billing",
        "--required-tests",
        "billing",
        "--constraints",
        "somente leitura",
        "--acceptance-criteria",
        "nenhum dado alterado",
        "--rollback-plan",
        "--json",
    )
    data = json.loads(output)
    assert code == cli.EXIT_OK
    assert data["gate"]["interno"] == "PASS"
    assert data["gate"]["apresentado"] == "APROVADO"


def test_cli_reports_a_blocked_gate_with_its_own_exit_code(tmp_path):
    code, output = _run_cli(
        "risk",
        "analyze",
        _prompt_file(tmp_path, "Alterar o modulo de auth"),
        "--permissions",
        "write:auth",
        "--forbidden-scope",
        "module:auth",
        "--targets",
        "module:auth",
    )
    assert code == cli.EXIT_BLOCKED
    assert "BLOQUEADO" in output


def test_cli_refuses_an_unknown_project(tmp_path):
    code, output = _run_cli(
        "risk", "analyze", _prompt_file(tmp_path, "qualquer coisa"), "--project", "inexistente"
    )
    assert code == cli.EXIT_INPUT_ERROR
    assert "risk_analysis" in output


def test_cli_refuses_an_invalid_environment(tmp_path):
    with pytest.raises(SystemExit):
        _run_cli(
            "risk",
            "analyze",
            _prompt_file(tmp_path, "qualquer coisa"),
            "--environment",
            "Homologação",
        )


def test_cli_refuses_a_missing_prompt_file():
    code, output = _run_cli("risk", "analyze", "arquivo-que-nao-existe.txt")
    assert code == cli.EXIT_INPUT_ERROR
    assert "não encontrado" in output


def test_cli_refuses_an_empty_prompt(tmp_path):
    code, output = _run_cli("risk", "analyze", _prompt_file(tmp_path, "   \n  "))
    assert code == cli.EXIT_INPUT_ERROR
    assert "Prompt vazio" in output


def test_cli_does_not_issue_a_contract_for_a_blocked_gate(tmp_path):
    code, output = _run_cli(
        "risk",
        "contract",
        _prompt_file(tmp_path, "Alterar o modulo de auth"),
        "--permissions",
        "write:auth",
        "--forbidden-scope",
        "module:auth",
        "--targets",
        "module:auth",
    )
    assert code == cli.EXIT_BLOCKED
    assert "BLOQUEADA" in output


def test_cli_issues_a_contract_for_an_approved_prompt(tmp_path):
    code, output = _run_cli(
        "risk",
        "contract",
        _prompt_file(tmp_path, "Ler o relatorio de billing e auditar os totais"),
        "--permissions",
        "read:billing",
        "--allowed-scope",
        "module:billing",
        "--targets",
        "module:billing",
        "--required-tests",
        "billing",
        "--constraints",
        "somente leitura",
        "--acceptance-criteria",
        "nenhum dado alterado",
        "--rollback-plan",
    )
    assert code == cli.EXIT_OK
    assert "Contrato emitido" in output


def test_cli_validates_a_universal_contract(tmp_path):
    contract = {
        "contract_version": "pedrocore-risk-request/v1",
        "request_id": "cli-001",
        "environment": "development",
        "agent_id": "codex-local",
        "request_text": "Edit the billing module within the approved scope.",
        "permissions": ["write:billing"],
        "requested_operation": {"kind": "WRITE", "targets": ["module:billing"]},
        "context": {"allowed_scope": ["module:billing"]},
    }
    path = tmp_path / "contrato.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    code, output = _run_cli(
        "risk",
        "validate-contract",
        str(path),
        "--project",
        PROJECT,
        "--producer",
        "pedrocore-ci",
        "--json",
    )
    assert code == cli.EXIT_OK
    assert json.loads(output)["aceito"] is True


def test_cli_refuses_a_contract_that_declares_its_own_gate(tmp_path):
    contract = {
        "contract_version": "pedrocore-risk-request/v1",
        "request_id": "cli-002",
        "environment": "development",
        "agent_id": "codex-local",
        "request_text": "Edit the billing module.",
        "requested_operation": {"kind": "WRITE", "targets": ["module:billing"]},
        "gate": "PASS",
    }
    path = tmp_path / "forjado.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    code, output = _run_cli(
        "risk", "validate-contract", str(path), "--project", PROJECT, "--producer", "pedrocore-ci"
    )
    assert code == cli.EXIT_INPUT_ERROR
    assert "RISK_CONTRACT_AUTHORITY_VIOLATION" in output


def test_cli_history_reports_the_real_window():
    code, output = _run_cli(
        "risk", "history", "--project", PROJECT, "--producer", "pedrocore-ci", "--json"
    )
    assert code == cli.EXIT_OK
    assert json.loads(output)["project_id"] == PROJECT


def test_cli_benchmark_refuses_an_invalid_case_file(tmp_path):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"project_id": PROJECT}), encoding="utf-8")
    code, output = _run_cli("risk", "benchmark", str(path))
    assert code == cli.EXIT_INPUT_ERROR
    assert "inválida" in output


def test_cli_writes_the_output_file_when_asked(tmp_path):
    destination = tmp_path / "saida.json"
    code, _ = _run_cli(
        "risk",
        "analyze",
        _prompt_file(tmp_path, "Ler o relatorio de billing"),
        "--permissions",
        "read:billing",
        "--allowed-scope",
        "module:billing",
        "--json",
        "--output",
        str(destination),
    )
    assert code in {cli.EXIT_OK, cli.EXIT_BLOCKED}
    json.loads(destination.read_text(encoding="utf-8"))


def test_the_command_name_is_not_spelled_out_across_the_cli():
    """O rename futuro deve ser a edição de um módulo, não uma caçada."""
    assert console_command().startswith(COMMAND_NAME)
    assert PRODUCT_NAME in cli.build_parser().description


# --- TUI ------------------------------------------------------------------


def _app():
    from app.modules.risk_console.app import RiskConsoleApp

    return RiskConsoleApp()


def _fill(app, entry: ConsoleRequestInput) -> None:
    """Preenche o formulário como o usuário preencheria."""
    from textual.widgets import Checkbox, Input, Select, TextArea

    app.query_one("#projeto", Select).value = entry.project_id
    app.query_one("#ambiente", Select).value = entry.environment_label
    app.query_one("#executor", Select).value = entry.executor_label
    app.query_one("#prompt", TextArea).text = entry.prompt
    app.query_one("#permissoes", Input).value = ", ".join(entry.permissions)
    app.query_one("#escopo-permitido", Input).value = ", ".join(entry.allowed_scope)
    app.query_one("#escopo-proibido", Input).value = ", ".join(entry.forbidden_scope)
    app.query_one("#alvos", Input).value = ", ".join(entry.targets)
    app.query_one("#testes", Input).value = ", ".join(entry.required_tests)
    app.query_one("#restricoes", Input).value = ", ".join(entry.constraints)
    app.query_one("#criterios", Input).value = ", ".join(entry.acceptance_criteria)
    app.query_one("#banco", Input).value = entry.database or ""
    app.query_one("#rollback", Checkbox).value = entry.rollback_plan_present


def _drive(entry: ConsoleRequestInput | None, check):
    """Abre a TUI, preenche, analisa e entrega o app ao verificador."""

    async def scenario():
        app = _app()
        async with app.run_test() as pilot:
            if entry is not None:
                _fill(app, entry)
                await pilot.pause()
                app.action_analisar()
                await pilot.pause()
            return await check(app, pilot)

    return asyncio.run(scenario())


def test_the_console_opens_with_its_fields():
    async def check(app, _pilot):
        from textual.widgets import Select, TextArea

        assert app.query_one("#projeto", Select)
        assert app.query_one("#ambiente", Select)
        assert app.query_one("#executor", Select)
        assert app.query_one("#prompt", TextArea)
        return True

    assert _drive(None, check)


def test_the_console_titles_are_in_portuguese():
    async def check(app, _pilot):
        from textual.widgets import Label

        titles = [str(item.content) for item in app.query(Label)]
        assert PRODUCT_NAME in titles
        assert "Console de Risco Pré-Execução" in titles
        assert "Projeto" in titles
        assert "Ambiente" in titles
        assert "Executor" in titles
        assert "Prompt" in titles
        return True

    assert _drive(None, check)


def test_result_actions_start_disabled():
    async def check(app, _pilot):
        from textual.widgets import Button

        for selector in ("#acao-contrato", "#acao-copiar", "#acao-exportar"):
            assert app.query_one(selector, Button).disabled
        return True

    assert _drive(None, check)


def test_a_multiline_prompt_survives_the_form():
    entry = _clean(prompt="Primeira linha\nSegunda linha")

    async def check(app, _pilot):
        assert app.result is not None
        assert "\n" in app.result.request.request_text
        return True

    assert _drive(entry, check)


def test_an_approved_analysis_enables_the_approval_actions():
    async def check(app, _pilot):
        from textual.widgets import Button

        assert app.result.gate is RiskGate.PASS
        rendered = str(app.query_one("#resultado").content)
        assert "APROVADO" in rendered
        assert "APROVADO COM AVISOS" not in rendered
        assert not app.query_one("#acao-contrato", Button).disabled
        assert not app.query_one("#acao-copiar", Button).disabled
        return True

    assert _drive(_clean(), check)


def test_warnings_are_rendered_as_such():
    async def check(app, _pilot):
        assert app.result.gate is RiskGate.PASS_WITH_WARNINGS
        assert "APROVADO COM AVISOS" in str(app.query_one("#resultado").content)
        return True

    assert _drive(_warnings(), check)


def test_review_required_is_rendered_in_portuguese():
    async def check(app, _pilot):
        assert app.result.gate is RiskGate.REVIEW_REQUIRED
        assert "REVISÃO OBRIGATÓRIA" in str(app.query_one("#resultado").content)
        return True

    assert _drive(_review(), check)


def test_a_blocked_gate_disables_contract_and_approved_prompt():
    """As duas ações que transformariam análise em autorização."""

    async def check(app, _pilot):
        from textual.widgets import Button

        assert app.result.gate is RiskGate.BLOCK
        rendered = str(app.query_one("#resultado").content)
        assert "BLOQUEADO" in rendered
        assert "EXECUÇÃO BLOQUEADA" in rendered
        assert app.query_one("#acao-contrato", Button).disabled
        assert app.query_one("#acao-copiar", Button).disabled
        return True

    assert _drive(_blocked(), check)


def test_editing_after_an_analysis_disables_the_approval_actions():
    async def check(app, pilot):
        from textual.widgets import Button, TextArea

        assert not app.query_one("#acao-copiar", Button).disabled
        app.query_one("#prompt", TextArea).text = "Outro pedido totalmente diferente"
        await pilot.pause()
        assert app.query_one("#acao-copiar", Button).disabled
        assert app.query_one("#acao-contrato", Button).disabled
        assert "REANALISAR" in str(app.query_one("#mensagem").content)
        return True

    assert _drive(_clean(), check)


def test_reanalysing_after_an_edit_restores_a_valid_binding():
    async def check(app, pilot):
        from textual.widgets import Button, TextArea

        app.query_one("#prompt", TextArea).text = (
            "Ler o extrato de billing e auditar os totais"
        )
        await pilot.pause()
        assert app.query_one("#acao-copiar", Button).disabled
        app.query_one("#acao-reanalisar", Button).press()
        await pilot.pause()
        assert not app.query_one("#acao-copiar", Button).disabled
        return True

    assert _drive(_clean(), check)


def test_copying_the_approved_prompt_reports_success():
    async def check(app, pilot):
        from textual.widgets import Button

        app.query_one("#acao-copiar", Button).press()
        await pilot.pause()
        assert "copiado" in str(app.query_one("#mensagem").content)
        return True

    assert _drive(_clean(), check)


def test_an_empty_prompt_shows_a_portuguese_error():
    async def check(app, pilot):
        from textual.widgets import Button

        app.query_one("#analisar", Button).press()
        await pilot.pause()
        assert "Prompt vazio" in str(app.query_one("#mensagem").content)
        return True

    assert _drive(None, check)


def test_an_operational_failure_is_shown_sanitised(monkeypatch):
    """Nem string de conexão, nem caminho interno, nem stack trace."""
    secret = "postgresql://user:supersecret@host:5432/db"

    def explode(_request):
        raise RuntimeError(secret)

    from app.modules.risk_engine.pre_execution_service import pre_execution_risk_service

    monkeypatch.setattr(pre_execution_risk_service, "analyze", explode)

    async def check(app, _pilot):
        message = str(app.query_one("#mensagem").content)
        assert secret not in message
        assert "supersecret" not in message
        assert "RuntimeError" in message
        return True

    assert _drive(_clean(), check)


def test_the_export_action_writes_a_sanitised_file(tmp_path):
    from app.modules.risk_console.app import RiskConsoleApp

    async def scenario():
        app = RiskConsoleApp(export_dir=tmp_path)
        async with app.run_test() as pilot:
            _fill(app, _clean(prompt="Ler o billing com api_key=ABCDEFGHIJKLMNOPQRSTUV"))
            await pilot.pause()
            app.action_analisar()
            await pilot.pause()
            from textual.widgets import Button

            app.query_one("#acao-exportar", Button).press()
            await pilot.pause()
            return list(tmp_path.glob("risco-*.json"))

    files = asyncio.run(scenario())
    assert files
    content = files[0].read_text(encoding="utf-8")
    assert "ABCDEFGHIJKLMNOPQRSTUV" not in content
    assert REDACTED in content

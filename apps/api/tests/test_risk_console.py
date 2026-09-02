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


def _drive(entry: ConsoleRequestInput | None, check, size=(140, 45)):
    """Abre a TUI, preenche, analisa e entrega o app ao verificador."""

    async def scenario():
        from textual.widgets import Button

        app = _app()
        async with app.run_test(size=size) as pilot:
            if entry is not None:
                _fill(app, entry)
                await pilot.pause()
                app.query_one("#analisar", Button).press()
                await pilot.pause()
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

        # Titulo e subtitulo passaram a ser um bloco so: separados em cantos
        # opostos, liam como dois elementos sem relacao.
        cabecalho = str(app.query_one("#cabecalho").content)
        assert PRODUCT_NAME in cabecalho
        assert "Console de Risco Pré-Execução" in cabecalho

        titles = [str(item.content) for item in app.query(Label)]
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
        rendered = str(app.query_one("#painel-gate").content)
        assert "APROVADO" in rendered
        assert "APROVADO COM AVISOS" not in rendered
        assert not app.query_one("#acao-contrato", Button).disabled
        assert not app.query_one("#acao-copiar", Button).disabled
        return True

    assert _drive(_clean(), check)


def test_warnings_are_rendered_as_such():
    async def check(app, _pilot):
        assert app.result.gate is RiskGate.PASS_WITH_WARNINGS
        assert "APROVADO COM AVISOS" in str(app.query_one("#painel-gate").content)
        return True

    assert _drive(_warnings(), check)


def test_review_required_is_rendered_in_portuguese():
    async def check(app, _pilot):
        assert app.result.gate is RiskGate.REVIEW_REQUIRED
        assert "REVISÃO OBRIGATÓRIA" in str(app.query_one("#painel-gate").content)
        return True

    assert _drive(_review(), check)


def test_a_blocked_gate_disables_contract_and_approved_prompt():
    """As duas ações que transformariam análise em autorização."""

    async def check(app, _pilot):
        from textual.widgets import Button

        assert app.result.gate is RiskGate.BLOCK
        rendered = str(app.query_one("#painel-gate").content)
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
        async with app.run_test(size=(140, 45)) as pilot:
            from textual.widgets import Button

            _fill(app, _clean(prompt="Ler o billing com api_key=ABCDEFGHIJKLMNOPQRSTUV"))
            await pilot.pause()
            app.query_one("#analisar", Button).press()
            await pilot.pause()
            await pilot.pause()
            app.query_one("#acao-exportar", Button).press()
            await pilot.pause()
            return list(tmp_path.glob("risco-*.json"))

    files = asyncio.run(scenario())
    assert files
    content = files[0].read_text(encoding="utf-8")
    assert "ABCDEFGHIJKLMNOPQRSTUV" not in content
    assert REDACTED in content


# --- layout, hierarquia e responsividade ----------------------------------
#
# Estes casos medem DECISOES DE DESIGN, e nao estetica: o que esta recolhido
# ao abrir, o que aparece sem rolagem, o que vira uma coluna em terminal
# estreito e o que continua legivel sem cor. Beleza continua sendo julgamento
# humano; estas sao as propriedades que dariam para quebrar sem ninguem notar.


def _collapsible(app, selector):
    from textual.widgets import Collapsible

    return app.query_one(selector, Collapsible)


def test_the_first_screen_shows_only_the_common_path():
    """Projeto, Ambiente, Executor, Prompt e ANALISAR. Nada mais."""

    async def check(app, _pilot):
        from textual.widgets import Button, Select, TextArea

        assert app.query_one("#projeto", Select).display
        assert app.query_one("#ambiente", Select).display
        assert app.query_one("#executor", Select).display
        assert app.query_one("#prompt", TextArea).display
        assert not app.query_one("#analisar", Button).disabled
        return True

    assert _drive(None, check)


def test_advanced_settings_start_collapsed():
    """Onze campos abertos empurrariam o botão de análise para fora da tela."""

    async def check(app, _pilot):
        assert _collapsible(app, "#avancadas").collapsed is True
        return True

    assert _drive(None, check)


def test_advanced_settings_can_be_expanded():
    async def check(app, pilot):
        collapsible = _collapsible(app, "#avancadas")
        collapsible.collapsed = False
        await pilot.pause()
        assert collapsible.collapsed is False
        from textual.widgets import Input

        assert app.query_one("#permissoes", Input)
        return True

    assert _drive(None, check)


def test_advanced_settings_have_portuguese_help_text():
    """Campo técnico sem explicação intimida; com explicação, ensina."""

    async def check(app, _pilot):
        from textual.widgets import Label

        textos = [str(item.content) for item in app.query(Label)]
        # Os campos estao agrupados por pergunta, e a ajuda e curta: uma linha
        # que cabe ao lado do campo, e nao um paragrafo permanente na tela.
        for grupo in ("AUTORIZAÇÃO", "EXECUÇÃO", "VALIDAÇÃO", "DEPENDÊNCIAS"):
            assert grupo in textos
        assert "Operação — opcional" in textos
        assert "Se vazio, o Veltrix identifica pelo prompt." in textos
        assert "Capacidades que o executor poderá usar." in textos
        assert "Onde o agente poderá alterar." in textos
        assert "Áreas que nunca poderão mudar." in textos
        return True

    assert _drive(None, check)


def test_result_areas_are_hidden_before_any_analysis():
    """Painel vazio com moldura é ruído; ausência é resposta."""

    async def check(app, _pilot):
        for selector in ("#painel-gate", "#painel-dimensoes", "#linha-detalhe"):
            assert app.query_one(selector).display is False
        return True

    assert _drive(None, check)


def test_the_empty_state_explains_what_to_do():
    async def check(app, _pilot):
        texto = str(app.query_one("#painel-resumo").content)
        assert "ANALISAR RISCO" in texto
        assert "Nada é executado" in texto
        return True

    assert _drive(None, check)


def test_the_gate_has_a_panel_of_its_own():
    """Gate é informação de primeira classe, não rodapé de relatório."""

    async def check(app, _pilot):
        gate = app.query_one("#painel-gate")
        assert gate.display is True
        assert gate.border_title == "GATE FINAL"
        assert "REVISÃO OBRIGATÓRIA" in str(gate.content)
        return True

    assert _drive(_review(), check)


def test_the_gate_panel_is_colour_coded_by_state():
    """A cor é reforço; a classe é o que o teste consegue verificar."""
    for entry, expected in (
        (_clean(), "-aprovado"),
        (_warnings(), "-avisos"),
        (_review(), "-revisao"),
        (_blocked(), "-bloqueado"),
    ):

        async def check(app, _pilot, expected=expected):
            assert app.query_one("#painel-gate").has_class(expected)
            return True

        assert _drive(entry, check)


def test_severity_is_readable_without_colour():
    """Terminal monocromático, ou olho que não distingue: o texto basta."""

    async def check(app, _pilot):
        faixa = str(app.query_one("#painel-dimensoes").content)
        assert any(rotulo in faixa for rotulo in ("BAIXO", "MÉDIO", "ALTO", "CRÍTICO"))
        assert "Escopo" in faixa and "Segurança" in faixa
        return True

    assert _drive(_review(), check)


def test_scenarios_are_summarised_and_expandable():
    """Resumo primeiro; o detalhe inteiro continua a um toque."""

    async def check(app, pilot):
        from textual.widgets import Collapsible

        # O cabecalho conta os cenarios; os NOMES vivem no titulo de cada
        # `Collapsible`, que e a propria lista. Uma lista repetida acima deles
        # gastaria altura para dizer duas vezes a mesma coisa.
        resumo = str(app.query_one("#cenarios-resumo").content)
        assert "cenário(s)" in resumo
        assert "nada é executado" in resumo

        cenarios = list(app.query(".cenario"))
        titulos = " ".join(str(item.title) for item in cenarios)
        assert "Sucesso" in titulos
        # Severidade inteira no titulo: truncada, ela deixaria de substituir a
        # cor para quem nao a distingue.
        assert "INFORMATIVO" in titulos
        assert cenarios, "nenhum cenário montado"
        assert all(item.collapsed for item in cenarios), "cenário nasce recolhido"

        primeiro = app.query_one("#cenario-0", Collapsible)
        primeiro.collapsed = False
        await pilot.pause()
        assert primeiro.collapsed is False
        return True

    assert _drive(_review(), check)


def test_an_expanded_scenario_keeps_every_field():
    """Organizar não é remover: o detalhe continua completo."""

    async def check(app, _pilot):
        # `.query_one(Static)` pegaria o titulo do Collapsible, que tambem e
        # um Static. A classe aponta para o conteudo.
        detalhe = str(app.query_one("#cenario-0 .cenario-detalhe").content)
        for rotulo in (
            "Efeito",
            "Contenção",
            "Rollback",
            "Verificação",
            "Risco residual",
            "Confiança",
        ):
            assert rotulo in detalhe
        return True

    assert _drive(_review(), check)


def test_findings_and_recommendations_live_in_separate_panels():
    """O que está errado e o que fazer são leituras diferentes."""

    async def check(app, _pilot):
        assert app.query_one("#painel-achados").border_title == "ACHADOS"
        assert app.query_one("#painel-recomendacoes").border_title == "RECOMENDAÇÕES"
        return True

    assert _drive(_blocked(), check)


def test_reason_codes_are_not_in_the_main_reading_surface():
    """O usuário lê a frase em português, não o código interno."""

    async def check(app, _pilot):
        achados = str(app.query_one("#achados-texto").content)
        assert "PROMPT_QUALITY_LOW" not in achados
        assert "FORBIDDEN_SCOPE" not in achados
        assert any(item in achados for item in ("MÉDIO", "ALTO", "CRÍTICO"))
        return True

    assert _drive(_blocked(), check)


def test_reason_codes_remain_available_in_technical_details():
    """Secundários, e não escondidos: quem audita continua alcançando tudo."""

    async def check(app, _pilot):
        tecnicos = str(app.query_one("#tecnicos-texto").content)
        assert "FORBIDDEN_SCOPE" in tecnicos
        assert "BLOCK" in tecnicos
        assert _collapsible(app, "#tecnicos").collapsed is True
        return True

    assert _drive(_blocked(), check)


def test_the_action_bar_is_docked_and_complete():
    async def check(app, _pilot):
        from textual.widgets import Button

        rotulos = {str(item.label) for item in app.query("#acoes Button")}
        assert rotulos == {
            "EDITAR PROMPT",
            "REANALISAR",
            "EMITIR CONTRATO",
            "COPIAR PROMPT",
            "EXPORTAR",
            "SAIR",
        }
        # Quem ancora e o rodape; status e acoes vivem dentro dele para
        # que nao disputem a mesma ultima linha da tela.
        assert app.query_one("#rodape").styles.dock == "bottom"
        assert isinstance(app.query_one("#acao-sair", Button), Button)
        return True

    assert _drive(None, check)


def test_a_wide_terminal_uses_two_columns():
    async def check(app, _pilot):
        assert not app.screen.has_class("-estreito")
        return True

    assert _drive(None, check, size=(140, 45))


def test_a_narrow_terminal_collapses_to_one_column():
    """Duas colunas viram uma, e nada importante desaparece."""

    async def check(app, _pilot):
        assert app.screen.has_class("-estreito")
        for selector in ("#painel-gate", "#painel-dimensoes", "#painel-cenarios"):
            assert app.query_one(selector).display is True
        assert "REVISÃO OBRIGATÓRIA" in str(app.query_one("#painel-gate").content)
        return True

    assert _drive(_review(), check, size=(78, 40))


def test_a_medium_terminal_still_renders_every_panel():
    async def check(app, _pilot):
        for selector in (
            "#painel-resumo",
            "#painel-alcance",
            "#painel-dimensoes",
            "#painel-gate",
            "#painel-cenarios",
            "#painel-historico",
            "#painel-achados",
            "#painel-recomendacoes",
        ):
            assert app.query_one(selector).display is True
        return True

    assert _drive(_review(), check, size=(110, 40))


def test_keyboard_navigation_reaches_the_form():
    """Mouse é opcional; teclado é obrigatório."""

    async def check(app, pilot):
        await pilot.press("tab")
        await pilot.pause()
        assert app.focused is not None
        return True

    assert _drive(None, check)


def test_the_keyboard_shortcut_runs_the_analysis():
    async def check(app, pilot):
        from textual.widgets import TextArea

        app.query_one("#prompt", TextArea).text = (
            "Ler o relatorio de billing e auditar os totais"
        )
        await pilot.pause()
        await pilot.press("ctrl+r")
        await pilot.pause()
        await pilot.pause()
        assert app.result is not None
        return True

    assert _drive(None, check)


def test_the_shortcut_toggles_advanced_settings():
    async def check(app, pilot):
        assert _collapsible(app, "#avancadas").collapsed is True
        await pilot.press("ctrl+d")
        await pilot.pause()
        assert _collapsible(app, "#avancadas").collapsed is False
        return True

    assert _drive(None, check)


def test_the_panel_titles_are_in_portuguese():
    async def check(app, _pilot):
        titulos = {
            str(app.query_one(selector).border_title)
            for selector in (
                "#painel-entrada",
                "#painel-resumo",
                "#painel-alcance",
                "#painel-dimensoes",
                "#painel-gate",
                "#painel-cenarios",
                "#painel-historico",
                "#painel-achados",
                "#painel-recomendacoes",
            )
        }
        assert titulos == {
            "ENTRADA",
            "ANÁLISE DE RISCO",
            "RAIO DE IMPACTO",
            "DIMENSÕES DE RISCO",
            "GATE FINAL",
            "CENÁRIOS",
            "HISTÓRICO",
            "ACHADOS",
            "RECOMENDAÇÕES",
        }
        for proibido in ("Findings", "Recommendations", "Final Gate", "Scope"):
            assert proibido not in titulos
        return True

    assert _drive(_review(), check)


def test_the_header_stays_on_one_line():
    """Cabeçalho não deve gastar altura que o conteúdo precisa."""

    async def check(app, _pilot):
        assert app.query_one("#cabecalho").styles.height.value == 1
        return True

    assert _drive(None, check)


# --- proporcao, espacamento e acabamento ----------------------------------
#
# A rodada anterior organizou a tela; esta mede se ela USA a tela. Sobra
# horizontal, faixa de status colada no botao e titulo truncado sao coisas que
# ninguem percebe num teste funcional e todo mundo percebe ao abrir.


def test_the_header_is_a_single_coherent_block():
    """Título num canto e subtítulo no oposto liam como dois elementos."""

    async def check(app, _pilot):
        cabecalho = app.query_one("#cabecalho")
        texto = str(cabecalho.content)
        assert PRODUCT_NAME in texto and "Console de Risco" in texto
        assert cabecalho.styles.height.value == 1
        return True

    assert _drive(None, check)


def test_the_analysis_column_takes_most_of_the_width():
    """A saída mais importante do produto não pode ser o painel menor."""

    async def check(app, _pilot):
        entrada = app.query_one("#coluna-entrada").size.width
        analise = app.query_one("#coluna-analise").size.width
        assert analise > entrada
        proporcao = analise / (entrada + analise)
        assert 0.55 <= proporcao <= 0.68, f"análise ocupa {proporcao:.0%}"
        return True

    assert _drive(None, check, size=(140, 45))


def test_the_analysis_panels_use_the_full_column():
    """Empilhados, e não lado a lado: cada painel usa os 62% inteiros."""

    async def check(app, _pilot):
        coluna = app.query_one("#coluna-analise").size.width
        for selector in ("#painel-resumo", "#painel-alcance"):
            largura = app.query_one(selector).size.width
            assert largura >= coluna * 0.9, f"{selector} usa {largura} de {coluna}"
        return True

    assert _drive(_review(), check, size=(140, 45))


def test_wide_terminals_spread_the_dimensions_across_one_row():
    """Faixa compacta é faixa: seis colunas quando há largura para seis."""

    async def check(app, _pilot):
        faixa = str(app.query_one("#painel-dimensoes").content)
        # Uma linha de nomes e uma de severidades — nada de lista vertical.
        linhas = [item for item in faixa.split("\n") if item.strip()]
        assert len(linhas) == 2, f"faixa com {len(linhas)} linhas"
        assert "Escopo" in linhas[0] and "Operacional" in linhas[0]
        return True

    assert _drive(_review(), check, size=(140, 45))


def test_narrow_terminals_wrap_the_dimensions_instead_of_truncating():
    async def check(app, _pilot):
        faixa = str(app.query_one("#painel-dimensoes").content)
        linhas = [item for item in faixa.split("\n") if item.strip()]
        assert len(linhas) > 2, "em terminal estreito a faixa precisa quebrar"
        for rotulo in ("Escopo", "Regressão", "Operacional"):
            assert rotulo in faixa, f"{rotulo} sumiu ao estreitar"
        return True

    assert _drive(_review(), check, size=(78, 40))


def test_the_impact_panel_uses_two_columns_when_wide():
    """Doze linhas curtas empilhadas gastavam vinte linhas de altura."""

    async def check(app, _pilot):
        texto = str(app.query_one("#painel-alcance").content)
        primeira = texto.split("\n")[0]
        # Contagem crua e métrica derivada convivem na mesma linha.
        assert "Arquivos" in primeira and "Amplitude" in primeira
        return True

    assert _drive(_review(), check, size=(140, 45))


def test_the_impact_panel_stacks_when_narrow():
    async def check(app, _pilot):
        texto = str(app.query_one("#painel-alcance").content)
        primeira = texto.split("\n")[0]
        assert "Arquivos" in primeira and "Amplitude" not in primeira
        assert "Magnitude" in texto
        return True

    assert _drive(_review(), check, size=(78, 40))


def test_the_advanced_settings_are_grouped_by_question():
    """Onze campos em lista são uma lista; agrupados são quatro perguntas."""

    async def check(app, _pilot):
        from textual.widgets import Label

        textos = [str(item.content) for item in app.query(Label)]
        for grupo in ("AUTORIZAÇÃO", "EXECUÇÃO", "VALIDAÇÃO", "DEPENDÊNCIAS"):
            assert grupo in textos
        return True

    assert _drive(None, check)


def test_the_advanced_settings_use_two_columns_when_wide():
    async def check(app, pilot):
        _collapsible(app, "#avancadas").collapsed = False
        await pilot.pause()
        colunas = app.query(".grupo-coluna")
        assert len(colunas) == 2
        assert all(item.size.width > 0 for item in colunas)
        # Lado a lado: mesma linha de topo.
        assert colunas[0].region.y == colunas[1].region.y
        return True

    assert _drive(None, check, size=(140, 45))


def test_every_advanced_field_survived_the_grouping():
    """Reorganizar não é remover."""

    async def check(app, _pilot):
        from textual.widgets import Checkbox, Input, Select

        for selector in (
            "#permissoes",
            "#escopo-permitido",
            "#escopo-proibido",
            "#alvos",
            "#restricoes",
            "#criterios",
            "#testes",
            "#integracoes",
            "#banco",
        ):
            assert app.query_one(selector, Input)
        assert app.query_one("#operacao", Select)
        assert app.query_one("#rollback", Checkbox)
        return True

    assert _drive(None, check)


def test_the_scenario_titles_are_aligned_with_leaders():
    """A severidade é o que se percorre com o olho; ela precisa alinhar."""

    async def check(app, _pilot):
        titulos = [str(item.title) for item in app.query(".cenario")]
        assert titulos
        assert all("." in item for item in titulos), "sem condutor pontilhado"
        colunas = {item.rfind(" ") for item in titulos}
        assert len(colunas) == 1, "severidade não cai sempre na mesma coluna"
        return True

    assert _drive(_review(), check)


def test_the_exit_action_is_set_apart_from_the_flow():
    """Sair não é o próximo passo de nenhum fluxo."""

    async def check(app, _pilot):
        from textual.widgets import Button

        sair = app.query_one("#acao-sair", Button)
        exportar = app.query_one("#acao-exportar", Button)
        assert sair.has_class("discreto")
        # Empurrado para a direita por um espaçador, não encostado no fluxo.
        assert sair.region.x > exportar.region.right + 10
        return True

    assert _drive(_review(), check, size=(140, 45))


def test_the_status_bar_is_separated_from_the_buttons():
    """Mensagem colada no botão parece legenda de botão."""

    async def check(app, _pilot):
        mensagem = app.query_one("#mensagem")
        acoes = app.query_one("#acoes")
        assert mensagem.styles.height.value == 2
        assert mensagem.region.bottom <= acoes.region.y
        assert "Análise concluída" in str(mensagem.content)
        return True

    assert _drive(_clean(), check)


def test_no_action_falls_outside_a_narrow_screen():
    """Botão cortado é botão que parece ausente."""

    async def check(app, _pilot):
        from textual.widgets import Button

        largura = app.size.width
        for item in app.query("#acoes Button"):
            assert isinstance(item, Button)
            assert item.region.right <= largura, f"{item.id} sai da tela"
        return True

    assert _drive(_review(), check, size=(78, 40))


def test_the_primary_action_moves_to_reanalyse_after_an_analysis():
    """Antes da análise o passo é ANALISAR; depois dela, REANALISAR."""

    async def check(app, _pilot):
        from textual.widgets import Button

        assert app.query_one("#analisar", Button).variant == "primary"
        assert app.query_one("#acao-reanalisar", Button).variant == "primary"
        assert app.query_one("#acao-exportar", Button).variant == "default"
        return True

    assert _drive(_review(), check)


def test_the_primary_action_is_not_claimed_before_any_analysis():
    async def check(app, _pilot):
        from textual.widgets import Button

        assert app.query_one("#acao-reanalisar", Button).variant == "default"
        return True

    assert _drive(None, check)

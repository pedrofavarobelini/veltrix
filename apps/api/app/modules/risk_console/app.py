"""Risk Console — a TUI.

Escolha de tecnologia
---------------------

Textual, em Python, no mesmo processo do core. As alternativas foram
descartadas por razoes concretas, nao por gosto: Electron traria um runtime
inteiro para desenhar oito paineis de texto; uma segunda SPA React duplicaria
o front que ja existe e esta congelado; um servidor web separado acrescentaria
porta, credencial e um modo de falha novo entre o usuario e uma analise que
roda em milissegundos.

O que esta tela NAO faz
-----------------------

Ela nao decide. Nao existe aqui nenhuma regra que produza gate, severidade ou
aprovacao. Tudo o que aparece veio de `analysis.py`, que chama o mesmo core
que a API HTTP chama.

Os botoes desabilitados em BLOCK sao conveniencia de interface. A recusa de
verdade esta em `analysis.issue_contract` e `analysis.approved_prompt`, que
recusam do mesmo jeito se alguem chamar a funcao direto. Interface que fosse a
unica guarda seria uma guarda que se contorna com um clique fora de ordem.
"""

from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Checkbox, Input, Label, Select, Static, TextArea

from app.modules.risk_console.analysis import (
    ConsoleAnalysis,
    ConsoleOperationError,
    analyze,
    approved_prompt,
    issue_contract,
)
from app.modules.risk_console.branding import (
    COLOR_ACCENT,
    COLOR_BACKGROUND,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_MUTED,
    COLOR_OK,
    COLOR_PANEL,
    COLOR_TEXT,
    COLOR_WARN,
    PRODUCT_NAME,
    PRODUCT_SUBTITLE,
)
from app.modules.risk_console.domain import (
    ENVIRONMENTS,
    EXECUTORS,
    OPERATIONS,
    ConsoleInputError,
    ConsoleRequestInput,
    available_projects,
    split_list,
)
from app.modules.risk_console.export import as_json
from app.modules.risk_console.render import render_analysis
from app.modules.risk_engine.execution_contract_schemas import RiskGate

# Acoes que so fazem sentido com uma analise aprovada na tela.
_APPROVAL_ACTIONS = ("#acao-contrato", "#acao-copiar")


class RiskConsoleApp(App):
    """Console de risco pré-execução."""

    TITLE = PRODUCT_NAME
    SUB_TITLE = PRODUCT_SUBTITLE

    CSS = f"""
    Screen {{
        background: {COLOR_BACKGROUND};
        color: {COLOR_TEXT};
    }}
    #cabecalho {{
        background: {COLOR_PANEL};
        border: round {COLOR_ACCENT};
        padding: 0 2;
        margin: 0 0 1 0;
        height: auto;
    }}
    #titulo {{ color: {COLOR_ACCENT}; text-style: bold; }}
    #subtitulo {{ color: {COLOR_MUTED}; }}
    .painel {{
        background: {COLOR_PANEL};
        border: round {COLOR_BORDER};
        padding: 1 2;
        margin: 0 0 1 0;
        height: auto;
    }}
    .rotulo {{ color: {COLOR_MUTED}; margin: 1 0 0 0; }}
    .secao {{ color: {COLOR_ACCENT}; text-style: bold; margin: 1 0 0 0; }}
    #prompt {{ height: 8; border: round {COLOR_BORDER}; }}
    #acoes {{ height: auto; margin: 0 0 1 0; }}
    #acoes Button {{ margin: 0 1 0 0; }}
    #mensagem {{ height: auto; padding: 0 2; }}
    .erro {{ color: {COLOR_DANGER}; }}
    .aviso {{ color: {COLOR_WARN}; }}
    .ok {{ color: {COLOR_OK}; }}
    #resultado {{ height: auto; }}
    """

    BINDINGS = [
        ("ctrl+r", "analisar", "Analisar risco"),
        ("ctrl+q", "sair", "Sair"),
    ]

    def __init__(self, *, export_dir: Path | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.result: ConsoleAnalysis | None = None
        self._export_dir = export_dir or Path.cwd()

    # --- composicao -------------------------------------------------------

    def compose(self) -> ComposeResult:
        projects = available_projects()
        with Vertical(id="cabecalho"):
            yield Label(PRODUCT_NAME, id="titulo")
            yield Label(PRODUCT_SUBTITLE, id="subtitulo")

        with VerticalScroll():
            with Vertical(classes="painel", id="entrada"):
                yield Label("ENTRADA", classes="secao")

                yield Label("Projeto", classes="rotulo")
                yield Select(
                    [(item, item) for item in projects],
                    id="projeto",
                    allow_blank=False,
                    value=projects[0] if projects else Select.BLANK,
                )

                yield Label("Ambiente", classes="rotulo")
                yield Select(
                    [(label, label) for label, _ in ENVIRONMENTS],
                    id="ambiente",
                    allow_blank=False,
                    value=ENVIRONMENTS[0][0],
                )

                yield Label("Executor", classes="rotulo")
                yield Select(
                    [(label, label) for label, _ in EXECUTORS],
                    id="executor",
                    allow_blank=False,
                    value=EXECUTORS[0][0],
                )

                yield Label("Prompt", classes="rotulo")
                yield TextArea("", id="prompt")

                # Contexto da operacao. Sem estes campos o motor responde
                # BLOCK por permissao ausente em praticamente tudo — e o
                # console existiria para mostrar sempre a mesma tela.
                yield Label("Operação (vazio = inferida do prompt)", classes="rotulo")
                yield Select(
                    [(label, label) for label, _ in OPERATIONS],
                    id="operacao",
                    prompt="Inferir do prompt",
                    allow_blank=True,
                )

                yield Label("Permissões (separadas por vírgula)", classes="rotulo")
                yield Input(placeholder="write:billing", id="permissoes")

                yield Label("Escopo permitido", classes="rotulo")
                yield Input(placeholder="module:billing", id="escopo-permitido")

                yield Label("Escopo proibido", classes="rotulo")
                yield Input(placeholder="module:auth", id="escopo-proibido")

                yield Label("Alvos da operação", classes="rotulo")
                yield Input(placeholder="module:billing", id="alvos")

                yield Label("Restrições", classes="rotulo")
                yield Input(placeholder="somente local", id="restricoes")

                yield Label("Critérios de aceitação", classes="rotulo")
                yield Input(placeholder="suíte de billing passa", id="criterios")

                yield Label("Testes exigidos", classes="rotulo")
                yield Input(placeholder="billing", id="testes")

                yield Label("Integrações externas", classes="rotulo")
                yield Input(placeholder="stripe", id="integracoes")

                yield Label("Banco de dados", classes="rotulo")
                yield Input(placeholder="pedrocore", id="banco")

                yield Checkbox("Plano de rollback declarado", id="rollback")

                yield Button("ANALISAR RISCO", id="analisar", variant="primary")

            yield Static("", id="mensagem")

            with Horizontal(id="acoes"):
                yield Button("EDITAR PROMPT", id="acao-editar")
                yield Button("REANALISAR", id="acao-reanalisar")
                yield Button("EMITIR CONTRATO", id="acao-contrato")
                yield Button("COPIAR PROMPT APROVADO", id="acao-copiar")
                yield Button("EXPORTAR", id="acao-exportar")
                yield Button("SAIR", id="acao-sair")

            with Horizontal(id="acoes-detalhe"):
                yield Button("VER EVIDÊNCIA", id="acao-evidencia")
                yield Button("VER CONTRATO", id="acao-contrato-ver")

            yield Static("", id="resultado", classes="painel")

    def on_mount(self) -> None:
        self._reset_actions()
        self.query_one("#resultado", Static).display = False

    # --- estado das acoes -------------------------------------------------

    def _reset_actions(self) -> None:
        """Sem análise na tela, nenhuma ação de resultado faz sentido."""
        for selector in (
            "#acao-editar",
            "#acao-reanalisar",
            "#acao-exportar",
            "#acao-evidencia",
            "#acao-contrato-ver",
            *_APPROVAL_ACTIONS,
        ):
            self.query_one(selector, Button).disabled = True

    def _apply_gate_to_actions(self, result: ConsoleAnalysis) -> None:
        """Habilita o que o gate permite — e só o que ele permite.

        Em BLOCK, emitir contrato e copiar prompt aprovado ficam
        indisponíveis. Não é enfeite: são exatamente as duas ações que
        transformariam uma análise em autorização.
        """
        for selector in ("#acao-editar", "#acao-reanalisar", "#acao-exportar"):
            self.query_one(selector, Button).disabled = False

        self.query_one("#acao-evidencia", Button).disabled = (
            result.analysis.historical_evidence.sample_size == 0
        )
        self.query_one("#acao-contrato-ver", Button).disabled = True

        blocked = result.gate is RiskGate.BLOCK
        for selector in _APPROVAL_ACTIONS:
            self.query_one(selector, Button).disabled = blocked

    def _invalidate_binding(self) -> None:
        """O formulário mudou: o vínculo com a análise exibida caiu.

        Impede o caminho `analisa A -> edita para B -> copia B como aprovado`.
        Enquanto não houver nova análise, o que está na tela não corresponde ao
        que está no formulário, e as ações de aprovação ficam fora do alcance.
        """
        if self.result is None:
            return
        for selector in _APPROVAL_ACTIONS:
            self.query_one(selector, Button).disabled = True
        self._message(
            "O formulário mudou desde a última análise. Use REANALISAR para atualizar.",
            "aviso",
        )

    # --- mensagens --------------------------------------------------------

    def _message(self, text: str, style: str = "") -> None:
        widget = self.query_one("#mensagem", Static)
        widget.set_classes(style)
        widget.update(text)

    # --- coleta do formulario --------------------------------------------

    def _collect(self) -> ConsoleRequestInput:
        operation_label = self.query_one("#operacao", Select).value
        operation = None
        if operation_label is not Select.BLANK:
            operation = dict(OPERATIONS)[str(operation_label)]

        banco = self.query_one("#banco", Input).value.strip()
        return ConsoleRequestInput(
            project_id=str(self.query_one("#projeto", Select).value),
            environment_label=str(self.query_one("#ambiente", Select).value),
            executor_label=str(self.query_one("#executor", Select).value),
            prompt=self.query_one("#prompt", TextArea).text,
            operation=operation,
            permissions=split_list(self.query_one("#permissoes", Input).value),
            allowed_scope=split_list(self.query_one("#escopo-permitido", Input).value),
            forbidden_scope=split_list(self.query_one("#escopo-proibido", Input).value),
            targets=split_list(self.query_one("#alvos", Input).value),
            required_tests=split_list(self.query_one("#testes", Input).value),
            constraints=split_list(self.query_one("#restricoes", Input).value),
            acceptance_criteria=split_list(self.query_one("#criterios", Input).value),
            external_integrations=split_list(self.query_one("#integracoes", Input).value),
            database=banco or None,
            rollback_plan_present=self.query_one("#rollback", Checkbox).value,
        )

    # --- acoes ------------------------------------------------------------

    def action_analisar(self) -> None:
        try:
            result = analyze(self._collect())
        except ConsoleInputError as error:
            self._message(str(error), "erro")
            return
        except ConsoleOperationError as error:
            self._message(str(error), "erro")
            return

        self.result = result
        painel = self.query_one("#resultado", Static)
        painel.display = True
        painel.update(render_analysis(result))
        self._apply_gate_to_actions(result)
        self._message("Análise concluída. Nenhuma operação foi executada.", "ok")

    def action_sair(self) -> None:
        self.exit()

    @on(Button.Pressed, "#analisar")
    @on(Button.Pressed, "#acao-reanalisar")
    def _pressed_analyze(self) -> None:
        self.action_analisar()

    @on(Button.Pressed, "#acao-sair")
    def _pressed_exit(self) -> None:
        self.action_sair()

    @on(Button.Pressed, "#acao-editar")
    def _pressed_edit(self) -> None:
        self.query_one("#prompt", TextArea).focus()
        self._invalidate_binding()

    @on(Button.Pressed, "#acao-contrato")
    def _pressed_contract(self) -> None:
        if self.result is None:
            return
        try:
            contract = issue_contract(self.result)
        except ConsoleOperationError as error:
            self._message(str(error), "erro")
            return
        self._contract_id = contract.contract_id
        self.query_one("#acao-contrato-ver", Button).disabled = False
        self._message(f"Contrato emitido: {contract.contract_id}", "ok")

    @on(Button.Pressed, "#acao-contrato-ver")
    def _pressed_view_contract(self) -> None:
        contract_id = getattr(self, "_contract_id", None)
        if contract_id is None:
            self._message("Nenhum contrato emitido nesta análise.", "aviso")
            return
        self._message(f"Contrato vigente: {contract_id}", "ok")

    @on(Button.Pressed, "#acao-copiar")
    def _pressed_copy(self) -> None:
        if self.result is None:
            return
        try:
            text = approved_prompt(self.result, _rebuilt(self._collect()))
        except (ConsoleInputError, ConsoleOperationError) as error:
            self._message(str(error), "erro")
            return
        self.copy_to_clipboard(text)
        self._message(
            "Prompt aprovado copiado. O conteúdo não é gravado em disco.", "ok"
        )

    @on(Button.Pressed, "#acao-evidencia")
    def _pressed_evidence(self) -> None:
        if self.result is None:
            return
        evidence = self.result.analysis.historical_evidence
        self._message(
            f"Evidência histórica: {evidence.sample_size} registro(s), "
            f"situação {evidence.status}.",
            "ok",
        )

    @on(Button.Pressed, "#acao-exportar")
    def _pressed_export(self) -> None:
        if self.result is None:
            return
        destination = self._export_dir / f"risco-{self.result.analysis.analysis_id}.json"
        try:
            destination.write_text(as_json(self.result), encoding="utf-8")
        except OSError:
            # Caminho e permissao sao detalhe de ambiente; a mensagem diz o
            # que aconteceu sem descrever a arvore de diretorios da maquina.
            self._message("Não foi possível gravar o arquivo de exportação.", "erro")
            return
        self._message(f"Exportado (sanitizado) para {destination.name}", "ok")

    # --- invalidacao do vinculo ------------------------------------------

    @on(TextArea.Changed, "#prompt")
    def _prompt_changed(self) -> None:
        self._invalidate_binding()

    @on(Input.Changed)
    def _input_changed(self) -> None:
        self._invalidate_binding()

    @on(Select.Changed)
    def _select_changed(self) -> None:
        self._invalidate_binding()

    @on(Checkbox.Changed)
    def _checkbox_changed(self) -> None:
        self._invalidate_binding()


def _rebuilt(entry: ConsoleRequestInput):
    """Requisicao equivalente ao formulario atual, para comparar assinatura.

    A comparacao ignora `request_id` — ela e feita por
    `analysis.binding_signature`, que o normaliza.
    """
    from app.modules.risk_console.domain import build_request

    return build_request(entry)


def run(export_dir: Path | None = None) -> None:
    """Abre o console. Ponto de entrada usado pela CLI."""
    RiskConsoleApp(export_dir=export_dir).run()

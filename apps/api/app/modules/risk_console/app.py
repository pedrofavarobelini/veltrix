"""Risk Console — a TUI.

Escolha de tecnologia
---------------------

Textual, em Python, no mesmo processo do core. As alternativas foram
descartadas por razoes concretas, nao por gosto: Electron traria um runtime
inteiro para desenhar paineis de texto; uma segunda SPA React duplicaria o
front que ja existe e esta congelado; um servidor web separado acrescentaria
porta, credencial e um modo de falha novo entre o usuario e uma analise que
roda em milissegundos.

Como a tela esta organizada, e por que
--------------------------------------

O usuario chega aqui com seis perguntas e pouco tempo: o que este prompt faz,
qual o alcance, qual o risco principal, por que o Veltrix decidiu assim, posso
executar, e o que preciso corrigir.

A primeira versao respondia todas — em sequencia, numa pagina longa. Funcionava
e cansava: o veredito, que e a resposta procurada, ficava depois de varias
telas de cenario.

Agora a tela e um painel. Entrada a esquerda, analise a direita, gate com
destaque proprio e uma barra de acoes fixa no rodape. O que e detalhe —
cenario aberto, codigo interno, score — fica recolhido, disponivel a um toque
e sem disputar espaco com a decisao.

Onze campos de contexto viraram uma secao recolhida. Eles mudam o resultado de
verdade e nao foram removidos; so pararam de ser a primeira coisa que alguem
ve ao abrir a ferramenta.

O que esta tela NAO faz
-----------------------

Ela nao decide. Nao existe aqui nenhuma regra que produza gate, severidade ou
aprovacao. Tudo o que aparece veio de `analysis.py`, que chama o mesmo core
que a API HTTP chama.

Os botoes desabilitados em BLOCK sao conveniencia de interface. A recusa de
verdade esta em `analysis.issue_contract` e `analysis.approved_prompt`, que
recusam do mesmo jeito se alguem chamar a funcao direto. Interface que fosse a
unica guarda seria uma guarda que se contorna com um clique fora de ordem.

Acessibilidade
--------------

Cor e sempre REFORCO, nunca o unico portador de significado: severidade e gate
trazem o rotulo textual junto (BAIXO, ALTO, BLOQUEADO). A tela inteira e
navegavel por teclado, e o foco tem contorno visivel.
"""

from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Checkbox,
    Collapsible,
    Input,
    Label,
    Select,
    Static,
    TextArea,
)

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

from app.modules.risk_console.render import (
    render_blast_panel,
    render_dimensions_band,
    render_findings_panel,
    render_gate_banner,
    render_historical_panel,
    render_recommendations_panel,
    render_scenario_detail,
    render_scenarios_summary,
    render_summary_panel,
    scenario_title,
    render_technical_details,
)
from app.modules.risk_engine.execution_contract_schemas import RiskGate

# Acoes que so fazem sentido com uma analise aprovada na tela.
_APPROVAL_ACTIONS = ("#acao-contrato", "#acao-copiar")

# Abaixo desta largura, duas colunas viram uma. 100 colunas e onde o painel de
# entrada e o de analise deixam de caber lado a lado sem truncar rotulo.
_NARROW_WIDTH = 100

_EMPTY_STATE = (
    f"[{COLOR_MUTED}]Preencha o prompt e use ANALISAR RISCO.\n\n"
    "Nada é executado: a análise é sempre um ensaio.[/]"
)


class RiskConsoleApp(App):
    """Console de risco pré-execução."""

    TITLE = PRODUCT_NAME
    SUB_TITLE = PRODUCT_SUBTITLE

    CSS = f"""
    Screen {{
        background: {COLOR_BACKGROUND};
        color: {COLOR_TEXT};
    }}

    /* --- cabecalho compacto: uma linha, sem altura desperdicada -------- */
    #cabecalho {{
        dock: top;
        height: 1;
        background: {COLOR_BACKGROUND};
        padding: 0 2;
        color: {COLOR_TEXT};
    }}

    /* --- barra de acoes fixa no rodape --------------------------------- */
    #rodape {{
        dock: bottom;
        height: 5;
        background: {COLOR_BACKGROUND};
    }}
    #acoes {{
        height: 3;
        padding: 0 2;
    }}
    #acoes Button {{
        margin: 0 2 0 0;
        min-width: 10;
        height: 3;
    }}
    /* Hierarquia: a acao seguinte do fluxo tem peso, as de saida nao, e SAIR
       e apenas alcancavel. Nenhum comportamento muda com isso. */
    #acoes Button.discreto {{
        color: {COLOR_MUTED};
        margin: 0;
    }}
    #espacador {{ width: 1fr; height: 1; }}
    Screen.-estreito #espacador {{ display: none; }}
    /* Em 76 colunas os seis botoes nao cabem numa fileira, e SAIR ficava
       fora da tela. Uma grade de 3x2 mantem todos alcancaveis pelo mouse —
       pelo teclado eles ja eram, mas botao cortado e botao que parece
       ausente. */
    Screen.-estreito #acoes {{
        layout: grid;
        grid-size: 3 2;
        grid-gutter: 0 1;
        height: 6;
    }}
    Screen.-estreito #acoes Button {{ width: 100%; margin: 0; }}
    /* Faixa de status: separada dos botoes por uma linha propria, para que a
       mensagem nao pareca legenda de botao. */
    #mensagem {{
        height: 2;
        padding: 1 2 0 2;
    }}
    .erro {{ color: {COLOR_DANGER}; text-style: bold; }}
    .aviso {{ color: {COLOR_WARN}; }}
    .ok {{ color: {COLOR_OK}; }}

    /* --- corpo: duas colunas em terminal largo ------------------------- */
    #topo {{ layout: horizontal; height: auto; }}
    #coluna-entrada {{ width: 38%; height: auto; }}
    #coluna-analise {{ width: 62%; height: auto; }}

    Screen.-estreito #topo {{ layout: vertical; height: auto; }}
    Screen.-estreito #coluna-entrada,
    Screen.-estreito #coluna-analise {{ width: 100%; height: auto; }}
    Screen.-estreito #linha-detalhe {{ layout: vertical; height: auto; }}
    Screen.-estreito #linha-detalhe > Vertical {{ width: 100%; height: auto; }}

    /* --- paineis ------------------------------------------------------- */
    .painel {{
        background: {COLOR_PANEL};
        border: round {COLOR_BORDER};
        border-title-color: {COLOR_ACCENT};
        border-title-style: bold;
        padding: 0 1;
        margin: 0 1 1 0;
        height: auto;
    }}
    .painel:focus-within {{ border: round {COLOR_ACCENT}; }}

    #painel-entrada {{ height: auto; }}

    #linha-detalhe {{ layout: horizontal; height: auto; }}
    /* Quatro colunas iguais truncavam o titulo do cenario no meio da
       severidade ("... MÉD"), e severidade truncada quebra justamente a regra
       de nao depender de cor. Cenarios recebe mais largura porque carrega uma
       lista; os outros tres carregam texto corrido.

       Unidades `fr` e nao porcentagem: porcentagem somava 100% e as margens
       entre paineis empurravam o ultimo para fora da tela, comendo a borda
       direita. `fr` divide o que sobra DEPOIS das margens. */
    #linha-detalhe > Vertical {{ height: auto; }}
    #painel-cenarios {{ width: 3fr; }}
    #painel-historico {{ width: 2fr; }}
    #painel-achados {{ width: 3fr; }}
    #painel-recomendacoes {{ width: 3fr; }}

    /* --- gate: o veredito tem peso proprio ----------------------------- */
    #painel-gate {{
        height: auto;
        border: heavy {COLOR_BORDER};
        border-title-color: {COLOR_ACCENT};
        border-title-style: bold;
        padding: 0 2;
        margin: 0 1 1 0;
        text-align: center;
        background: {COLOR_PANEL};
    }}
    #painel-gate.-aprovado {{ border: heavy {COLOR_OK}; }}
    #painel-gate.-avisos {{ border: heavy {COLOR_WARN}; }}
    #painel-gate.-revisao {{ border: heavy {COLOR_WARN}; }}
    #painel-gate.-bloqueado {{ border: heavy {COLOR_DANGER}; }}

    /* --- entrada compacta ---------------------------------------------- */
    .linha-campo {{ height: 3; }}
    .linha-campo Label {{
        width: 11;
        content-align: left middle;
        height: 3;
        color: {COLOR_MUTED};
    }}
    .linha-campo Select {{ width: 1fr; }}
    /* `Label` nasce com largura automatica e por isso CORTA em vez de
       quebrar. Dentro das duas colunas das avancadas isso truncava a ajuda no
       meio da frase ("Capacidades que o exe"). Largura da coluna + altura
       automatica fazem o texto quebrar em duas linhas. */
    .rotulo {{ color: {COLOR_MUTED}; width: 100%; height: auto; }}
    .grupo {{
        color: {COLOR_ACCENT};
        text-style: bold;
        width: 100%;
        height: 1;
        margin: 1 0 0 0;
    }}
    #avancadas-colunas {{ layout: horizontal; height: auto; }}
    .grupo-coluna {{ width: 1fr; height: auto; padding: 0 1 0 0; }}
    Screen.-estreito #avancadas-colunas {{ layout: vertical; height: auto; }}
    Screen.-estreito .grupo-coluna {{ width: 100%; }}
    .ajuda {{ color: {COLOR_MUTED}; text-style: italic; width: 100%; height: auto; }}
    #prompt {{ height: 9; border: round {COLOR_BORDER}; }}
    #prompt:focus {{ border: round {COLOR_ACCENT}; }}
    #analisar {{ width: 100%; height: 3; }}

    Collapsible {{ border: none; background: {COLOR_PANEL}; padding: 0; }}
    CollapsibleTitle {{ color: {COLOR_ACCENT}; }}

    .conteudo {{ height: auto; }}
    """

    BINDINGS = [
        ("ctrl+r", "analisar", "Analisar risco"),
        ("ctrl+e", "editar", "Editar prompt"),
        ("ctrl+d", "avancadas", "Configurações avançadas"),
        ("ctrl+q", "sair", "Sair"),
    ]

    def __init__(self, *, export_dir: Path | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.result: ConsoleAnalysis | None = None
        self._export_dir = export_dir or Path.cwd()
        self._contract_id: str | None = None

    # --- composicao -------------------------------------------------------

    def compose(self) -> ComposeResult:
        # Titulo num canto e subtitulo no extremo oposto liam como dois
        # elementos sem relacao. Um bloco so, a esquerda, numa linha.
        yield Static(
            f"[bold {COLOR_ACCENT}]{PRODUCT_NAME}[/]"
            f"  [{COLOR_MUTED}]·  {PRODUCT_SUBTITLE}[/]",
            id="cabecalho",
        )

        with Vertical(id="rodape"):
            yield Static("", id="mensagem")
            with Horizontal(id="acoes"):
                yield Button("EDITAR PROMPT", id="acao-editar")
                yield Button("REANALISAR", id="acao-reanalisar")
                yield Button("EMITIR CONTRATO", id="acao-contrato")
                yield Button("COPIAR PROMPT", id="acao-copiar")
                yield Button("EXPORTAR", id="acao-exportar")
                # Empurra SAIR para a direita: sair nao e o proximo passo de
                # nenhum fluxo, e nao deveria estar encostado no que e.
                yield Static("", id="espacador")
                yield Button("SAIR", id="acao-sair", classes="discreto")

        with VerticalScroll(id="corpo"):
            with Horizontal(id="topo"):
                yield from self._compose_entrada()
                yield from self._compose_analise()

            yield Static("", classes="painel", id="painel-dimensoes")
            yield Static("", id="painel-gate")

            with Horizontal(id="linha-detalhe"):
                with Vertical(classes="painel", id="painel-cenarios"):
                    yield Static("", id="cenarios-resumo")
                    yield Vertical(id="cenarios-detalhe", classes="conteudo")
                with Vertical(classes="painel", id="painel-historico"):
                    yield Static("", id="historico-texto")
                with Vertical(classes="painel", id="painel-achados"):
                    yield Static("", id="achados-texto")
                with Vertical(classes="painel", id="painel-recomendacoes"):
                    yield Static("", id="recomendacoes-texto")

            with Collapsible(title="DETALHES TÉCNICOS", collapsed=True, id="tecnicos"):
                yield Static("", id="tecnicos-texto")

    def _compose_entrada(self) -> ComposeResult:
        projects = available_projects()
        with Vertical(id="coluna-entrada"):
            with Vertical(classes="painel", id="painel-entrada"):
                with Horizontal(classes="linha-campo"):
                    yield Label("Projeto")
                    yield Select(
                        [(item, item) for item in projects],
                        id="projeto",
                        allow_blank=False,
                        value=projects[0] if projects else Select.BLANK,
                    )
                with Horizontal(classes="linha-campo"):
                    yield Label("Ambiente")
                    yield Select(
                        [(label, label) for label, _ in ENVIRONMENTS],
                        id="ambiente",
                        allow_blank=False,
                        value=ENVIRONMENTS[0][0],
                    )
                with Horizontal(classes="linha-campo"):
                    yield Label("Executor")
                    yield Select(
                        [(label, label) for label, _ in EXECUTORS],
                        id="executor",
                        allow_blank=False,
                        value=EXECUTORS[0][0],
                    )

                yield Label("Prompt", classes="rotulo")
                yield TextArea("", id="prompt")

                # Recolhido por escolha: onze campos abertos empurrariam o
                # botao de analise para fora da tela e fariam a ferramenta
                # parecer um formulario, e nao um console.
                with Collapsible(
                    title="CONFIGURAÇÕES AVANÇADAS",
                    collapsed=True,
                    id="avancadas",
                ):
                    yield from self._compose_avancadas()

                yield Button("ANALISAR RISCO", id="analisar", variant="primary")

    def _compose_avancadas(self) -> ComposeResult:
        """Onze campos agrupados por PERGUNTA, nao por ordem de implementacao.

        Uma coluna unica de onze campos e uma lista; agrupada em autorizacao,
        execucao, validacao e dependencias, vira quatro perguntas curtas — e
        quem so precisa declarar permissao encontra a permissao sem ler o
        resto.
        """
        with Horizontal(id="avancadas-colunas"):
            with Vertical(classes="grupo-coluna"):
                yield Label("AUTORIZAÇÃO", classes="grupo")
                yield Label("Permissões", classes="rotulo")
                yield Label("Capacidades que o executor poderá usar.", classes="ajuda")
                yield Input(placeholder="write:billing", id="permissoes")

                yield Label("Escopo permitido", classes="rotulo")
                yield Label("Onde o agente poderá alterar.", classes="ajuda")
                yield Input(placeholder="module:billing", id="escopo-permitido")

                yield Label("Escopo proibido", classes="rotulo")
                yield Label("Áreas que nunca poderão mudar.", classes="ajuda")
                yield Input(placeholder="module:auth", id="escopo-proibido")

                yield Label("VALIDAÇÃO", classes="grupo")
                yield Label("Critérios de aceitação", classes="rotulo")
                yield Input(placeholder="suíte de billing passa", id="criterios")

                yield Label("Testes exigidos", classes="rotulo")
                yield Input(placeholder="billing", id="testes")

                yield Checkbox("Plano de rollback declarado", id="rollback")

            with Vertical(classes="grupo-coluna"):
                yield Label("EXECUÇÃO", classes="grupo")
                yield Label("Operação — opcional", classes="rotulo")
                yield Label("Se vazio, o Veltrix identifica pelo prompt.", classes="ajuda")
                yield Select(
                    [(label, label) for label, _ in OPERATIONS],
                    id="operacao",
                    prompt="Identificar pelo prompt",
                    allow_blank=True,
                )

                yield Label("Alvos da operação", classes="rotulo")
                yield Input(placeholder="module:billing", id="alvos")

                yield Label("Restrições", classes="rotulo")
                yield Input(placeholder="somente local", id="restricoes")

                yield Label("DEPENDÊNCIAS", classes="grupo")
                yield Label("Integrações externas", classes="rotulo")
                yield Input(placeholder="stripe", id="integracoes")

                yield Label("Banco de dados", classes="rotulo")
                yield Input(placeholder="pedrocore", id="banco")

    def _compose_analise(self) -> ComposeResult:
        # Empilhados, e nao lado a lado: assim cada painel ocupa os 62% da
        # coluna em vez de metade deles, e a altura somada acompanha a da
        # ENTRADA — que era de onde vinha o vazio a direita.
        with Vertical(id="coluna-analise"):
            yield Static(_EMPTY_STATE, classes="painel", id="painel-resumo")
            yield Static("", classes="painel", id="painel-alcance")

    def on_mount(self) -> None:
        for selector, title in (
            ("#painel-entrada", "ENTRADA"),
            ("#painel-resumo", "ANÁLISE DE RISCO"),
            ("#painel-alcance", "RAIO DE IMPACTO"),
            ("#painel-dimensoes", "DIMENSÕES DE RISCO"),
            ("#painel-gate", "GATE FINAL"),
            ("#painel-cenarios", "CENÁRIOS"),
            ("#painel-historico", "HISTÓRICO"),
            ("#painel-achados", "ACHADOS"),
            ("#painel-recomendacoes", "RECOMENDAÇÕES"),
        ):
            self.query_one(selector).border_title = title
        self._reset_actions()
        self._show_result_areas(False)
        self._apply_width(self.size.width)

    # --- responsividade ---------------------------------------------------

    def on_resize(self, event) -> None:
        self._apply_width(event.size.width)

    def _apply_width(self, width: int) -> None:
        """Em terminal estreito, duas colunas viram uma.

        Nada some: o que estava lado a lado passa a ficar empilhado, e o
        conteudo continua alcancavel por rolagem.
        """
        self.screen.set_class(width < _NARROW_WIDTH, "-estreito")

    # --- estado das acoes -------------------------------------------------

    def _reset_actions(self) -> None:
        for selector in (
            "#acao-editar",
            "#acao-reanalisar",
            "#acao-exportar",
            *_APPROVAL_ACTIONS,
        ):
            self.query_one(selector, Button).disabled = True

    def _show_result_areas(self, visible: bool) -> None:
        for selector in (
            "#painel-alcance",
            "#painel-dimensoes",
            "#painel-gate",
            "#linha-detalhe",
            "#tecnicos",
        ):
            self.query_one(selector).display = visible

    def _apply_gate_to_actions(self, result: ConsoleAnalysis) -> None:
        """Habilita o que o gate permite — e só o que ele permite.

        Em BLOCK, emitir contrato e copiar prompt aprovado ficam
        indisponíveis. Não é enfeite: são exatamente as duas ações que
        transformariam uma análise em autorização.
        """
        for selector in ("#acao-editar", "#acao-reanalisar", "#acao-exportar"):
            self.query_one(selector, Button).disabled = False

        # Com uma analise na tela, o proximo passo do fluxo deixa de ser
        # ANALISAR e passa a ser REANALISAR. O peso visual acompanha.
        self.query_one("#acao-reanalisar", Button).variant = "primary"

        blocked = result.gate is RiskGate.BLOCK
        for selector in _APPROVAL_ACTIONS:
            self.query_one(selector, Button).disabled = blocked

    def _invalidate_binding(self) -> None:
        """O formulário mudou: o vínculo com a análise exibida caiu.

        Impede o caminho `analisa A -> edita para B -> copia B como aprovado`.
        """
        if self.result is None:
            return
        for selector in _APPROVAL_ACTIONS:
            self.query_one(selector, Button).disabled = True
        self._message(
            "O formulário mudou desde a última análise. Use REANALISAR.", "aviso"
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

    # --- pintura do resultado --------------------------------------------

    _GATE_CLASSES = {
        RiskGate.PASS: "-aprovado",
        RiskGate.PASS_WITH_WARNINGS: "-avisos",
        RiskGate.REVIEW_REQUIRED: "-revisao",
        RiskGate.BLOCK: "-bloqueado",
    }

    async def _paint(self, result: ConsoleAnalysis) -> None:
        self.query_one("#painel-resumo", Static).update(render_summary_panel(result))

        # A faixa acompanha a largura real: seis dimensoes numa linha so em
        # terminal largo, tres em medio, duas em estreito. Fixar em tres
        # deixava dois tercos da faixa em branco depois que ela passou a
        # ocupar a largura inteira.
        largura = self.size.width
        colunas = 6 if largura >= 128 else (3 if largura >= _NARROW_WIDTH else 2)
        self.query_one("#painel-dimensoes", Static).update(
            render_dimensions_band(result, columns=colunas)
        )
        self.query_one("#painel-alcance", Static).update(
            render_blast_panel(result, columns=1 if largura < _NARROW_WIDTH else 2)
        )

        gate = self.query_one("#painel-gate", Static)
        gate.set_classes(self._GATE_CLASSES[result.gate])
        gate.update(render_gate_banner(result))

        self.query_one("#cenarios-resumo", Static).update(render_scenarios_summary(result))
        await self._mount_scenarios(result)

        self.query_one("#historico-texto", Static).update(render_historical_panel(result))
        self.query_one("#achados-texto", Static).update(render_findings_panel(result))
        self.query_one("#recomendacoes-texto", Static).update(
            render_recommendations_panel(result)
        )
        self.query_one("#tecnicos-texto", Static).update(render_technical_details(result))
        self._show_result_areas(True)

    async def _mount_scenarios(self, result: ConsoleAnalysis) -> None:
        """Um `Collapsible` por cenário — nada removido, só recolhido.

        A remocao e AGUARDADA antes de montar os novos. Sem isso, uma segunda
        analise tenta montar `cenario-0` enquanto o `cenario-0` anterior ainda
        existe, e o Textual recusa o id duplicado — o que quebrava reanalisar.
        """
        container = self.query_one("#cenarios-detalhe", Vertical)
        await container.remove_children()
        for index, item in enumerate(result.analysis.simulations):
            title = scenario_title(item)
            await container.mount(
                Collapsible(
                    Static(render_scenario_detail(item), classes="cenario-detalhe"),
                    title=title,
                    collapsed=True,
                    id=f"cenario-{index}",
                    classes="cenario",
                )
            )

    # --- acoes ------------------------------------------------------------

    async def action_analisar(self) -> None:
        try:
            result = analyze(self._collect())
        except (ConsoleInputError, ConsoleOperationError) as error:
            self._message(str(error), "erro")
            return

        self.result = result
        await self._paint(result)
        self._apply_gate_to_actions(result)
        self._message("Análise concluída. Nenhuma operação foi executada.", "ok")

    def action_editar(self) -> None:
        self.query_one("#prompt", TextArea).focus()
        self._invalidate_binding()

    def action_avancadas(self) -> None:
        collapsible = self.query_one("#avancadas", Collapsible)
        collapsible.collapsed = not collapsible.collapsed

    def action_sair(self) -> None:
        self.exit()

    @on(Button.Pressed, "#analisar")
    @on(Button.Pressed, "#acao-reanalisar")
    async def _pressed_analyze(self) -> None:
        await self.action_analisar()

    @on(Button.Pressed, "#acao-sair")
    def _pressed_exit(self) -> None:
        self.action_sair()

    @on(Button.Pressed, "#acao-editar")
    def _pressed_edit(self) -> None:
        self.action_editar()

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
        self._message(f"Contrato emitido: {contract.contract_id}", "ok")

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
        self._message("Prompt aprovado copiado. Nada é gravado em disco.", "ok")

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

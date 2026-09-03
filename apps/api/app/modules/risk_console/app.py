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
    TabbedContent,
    TabPane,
    Button,
    Checkbox,
    Collapsible,
    Input,
    Label,
    Select,
    Static,
    TextArea,
)

from app.modules.risk_console.projects import (
    GerenciarProjetosScreen,
    NovoProjetoScreen,
)
from app.modules.risk_console.auto_context import apply, propose, render_review
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
    project_display_name,
    ENVIRONMENTS,
    EXECUTORS,
    OPERATIONS,
    ConsoleInputError,
    ConsoleRequestInput,
    available_projects,
    build_request,
    split_list,
)
from app.modules.risk_console.export import as_json

from app.modules.risk_console.render import (
    render_all_recommendations,
    render_key_findings,
    render_key_recommendations,
    render_operation_summary,
    render_project_badge,
    render_top_risks,
    render_blast_panel,
    render_context_panel,
    render_dimensions_band,
    render_findings_panel,
    render_gate_banner,
    render_historical_panel,
    render_scenario_detail,
    render_scenarios_summary,
    scenario_title,
    render_technical_details,
)
from app.modules.risk_engine.execution_contract_schemas import RiskGate

# Acoes que so fazem sentido com uma analise aprovada na tela.
_APPROVAL_ACTIONS = ("#acao-contrato", "#acao-copiar")

# Abaixo desta largura, duas colunas viram uma. 100 colunas e onde o painel de
# entrada e o de analise deixam de caber lado a lado sem truncar rotulo.
_NARROW_WIDTH = 100


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
    /* A entrada ocupa a tela inteira no ESTADO 1. Antes ela vivia em 38% e o
       resto era painel vazio esperando um resultado que ainda nao existia. */
    #coluna-entrada {{ width: 100%; height: auto; }}

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

    /* Quatro colunas iguais truncavam o titulo do cenario no meio da
       severidade ("... MÉD"), e severidade truncada quebra justamente a regra
       de nao depender de cor. Cenarios recebe mais largura porque carrega uma
       lista; os outros tres carregam texto corrido.

       Unidades `fr` e nao porcentagem: porcentagem somava 100% e as margens
       entre paineis empurravam o ultimo para fora da tela, comendo a borda
       direita. `fr` divide o que sobra DEPOIS das margens. */
    #painel-revisao {{ height: auto; }}
    #acoes-revisao {{ height: 3; margin: 1 0 0 0; }}
    #acoes-revisao Button {{ margin: 0 2 0 0; }}

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
    Input {{ border: round {COLOR_BORDER}; }}
    Input:focus {{ border: round {COLOR_ACCENT}; }}
    /* A dica precisa parecer dica. Com onze campos, o contraste padrao do
       Textual era sinal fraco demais e a tela lia como preenchida. */
    Input > .input--placeholder {{
        color: {COLOR_MUTED};
        text-style: italic;
    }}
    #prompt {{ height: 9; border: round {COLOR_BORDER}; }}
    #prompt:focus {{ border: round {COLOR_ACCENT}; }}
    #analisar {{ width: 100%; height: 3; }}

    /* --- os tres estados sao exclusivos -------------------------------- */
    /* Entrada, revisao e resultado nunca dividem a tela. Antes eles
       coexistiam, e a primeira viewport misturava um formulario com paineis
       vazios de uma analise que ainda nao existia. */
    #estado-entrada, #estado-revisao, #estado-resultado {{ height: auto; }}

    /* --- faixa de identidade do projeto -------------------------------- */
    #projeto-badge {{ height: auto; padding: 0 0 1 0; }}
    #linha-projeto {{ height: 3; }}
    #linha-projeto Label {{
        width: 11;
        content-align: left middle;
        height: 3;
        color: {COLOR_MUTED};
    }}
    #linha-projeto Select {{ width: 1fr; }}
    #novo-projeto {{ width: 5; min-width: 5; margin: 0 0 0 1; }}
    #gerenciar-projetos {{
        color: {COLOR_MUTED};
        border: none;
        height: 1;
        margin: 0 0 1 0;
        padding: 0;
    }}

    /* --- resultado: resumo primeiro, detalhe sob demanda --------------- */
    #resultado-topo {{ layout: horizontal; height: auto; }}
    #painel-resumo-operacao {{ width: 1fr; }}
    #painel-riscos {{ width: 1fr; }}
    Screen.-estreito #resultado-topo {{ layout: vertical; height: auto; }}
    Screen.-estreito #painel-resumo-operacao,
    Screen.-estreito #painel-riscos {{ width: 100%; }}

    /* As abas existem para que apenas UMA superficie de detalhe seja
       renderizada por vez. Sem elas, seis paineis competiam pela mesma
       primeira tela. */
    #detalhes {{ height: auto; margin: 0 1 1 0; }}
    #detalhes TabPane {{ padding: 1 1; height: auto; }}
    #detalhes ContentSwitcher {{ height: auto; }}
    Tabs {{ background: {COLOR_PANEL}; }}

    Collapsible {{ border: none; background: {COLOR_PANEL}; padding: 0; }}
    CollapsibleTitle {{ color: {COLOR_ACCENT}; }}

    .conteudo {{ height: auto; }}
    """

    # Nenhum atalho sugere executar a operacao analisada: o Risk Engine nao
    # executa nada, e um `Ctrl+E` lido como "executar" seria uma promessa que
    # o produto inteiro existe para nao fazer.
    BINDINGS = [
        ("ctrl+j", "avancar", "Analisar / Confirmar"),
        ("ctrl+r", "analisar", "Analisar risco"),
        ("escape", "voltar", "Voltar"),
        ("ctrl+d", "avancadas", "Configurações avançadas"),
        ("ctrl+q", "sair", "Sair"),
    ]

    def __init__(self, *, export_dir: Path | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.result: ConsoleAnalysis | None = None
        self._proposal = None
        self._pending_entry = None
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
            # ESTADO 1 — entrada. Sozinho na tela: nenhum painel de resultado
            # vazio, nenhuma dimensao sem valor, nenhum gate em branco.
            with Vertical(id="estado-entrada"):
                yield from self._compose_entrada()

            # ESTADO 2 — revisao do contexto proposto. Confirmar aqui autoriza
            # a ANALISE, nunca a execucao.
            with Vertical(id="estado-revisao"):
                with Vertical(classes="painel", id="painel-revisao"):
                    yield Static("", id="revisao-texto")
                    with Horizontal(id="acoes-revisao"):
                        yield Button(
                            "CONFIRMAR E ANALISAR", id="revisao-confirmar", variant="primary"
                        )
                        yield Button("REVISAR DETALHES", id="revisao-detalhes")
                        yield Button("CANCELAR", id="revisao-cancelar")

            # ESTADO 3 — resultado. A ordem da leitura E a ordem da tela:
            # veredito, o que foi pedido, o que pesa, por que, o que fazer.
            with Vertical(id="estado-resultado"):
                yield Static("", id="painel-gate")

                with Horizontal(id="resultado-topo"):
                    yield Static("", classes="painel", id="painel-resumo-operacao")
                    yield Static("", classes="painel", id="painel-riscos")

                yield Static("", classes="painel", id="painel-porque")
                yield Static("", classes="painel", id="painel-acoes-sugeridas")

                # Toda a evidencia continua aqui, inteira. O que mudou e que
                # uma aba de cada vez ocupa a tela, em vez de seis.
                with TabbedContent(id="detalhes"):
                    with TabPane("RAIO DE IMPACTO", id="aba-alcance"):
                        yield Static("", id="painel-alcance")
                    with TabPane("DIMENSÕES", id="aba-dimensoes"):
                        yield Static("", id="painel-dimensoes")
                    with TabPane("CENÁRIOS", id="aba-cenarios"):
                        yield Static("", id="cenarios-resumo")
                        yield Vertical(id="cenarios-detalhe", classes="conteudo")
                    with TabPane("HISTÓRICO", id="aba-historico"):
                        yield Static("", id="historico-texto")
                    with TabPane("CONTEXTO", id="aba-contexto"):
                        yield Static("", id="contexto-texto")
                    with TabPane("DETALHES TÉCNICOS", id="aba-tecnicos"):
                        yield Static("", id="achados-texto")
                        yield Static("", id="recomendacoes-texto")
                        yield Static("", id="tecnicos-texto")

    def _compose_entrada(self) -> ComposeResult:
        opcoes = self._project_options()
        with Vertical(id="coluna-entrada"):
            with Vertical(classes="painel", id="painel-entrada"):
                with Horizontal(id="linha-projeto"):
                    yield Label("Projeto")
                    yield Select(
                        opcoes,
                        id="projeto",
                        allow_blank=False,
                        value=opcoes[0][1] if opcoes else Select.BLANK,
                    )
                    yield Button("+", id="novo-projeto")
                # Identidade do projeto em uma linha: nome, se ha manifesto, se
                # ha caminho. O caminho completo fica em GERENCIAR PROJETOS.
                yield Static("", id="projeto-badge")
                yield Button("GERENCIAR PROJETOS", id="gerenciar-projetos")
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
                yield Input(placeholder="ex.: write:<módulo>", id="permissoes")

                yield Label("Escopo permitido", classes="rotulo")
                yield Label("Onde o agente poderá alterar.", classes="ajuda")
                yield Input(placeholder="ex.: module:<nome>", id="escopo-permitido")

                yield Label("Escopo proibido", classes="rotulo")
                yield Label("Áreas que nunca poderão mudar.", classes="ajuda")
                yield Input(placeholder="ex.: module:<nome>", id="escopo-proibido")

                yield Label("VALIDAÇÃO", classes="grupo")
                yield Label("Critérios de aceitação", classes="rotulo")
                yield Input(placeholder="ex.: <critério de aceitação>", id="criterios")

                yield Label("Testes exigidos", classes="rotulo")
                yield Input(placeholder="ex.: <suíte de testes>", id="testes")

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
                yield Input(placeholder="ex.: module:<nome>", id="alvos")

                yield Label("Restrições", classes="rotulo")
                yield Input(placeholder="ex.: <restrição>", id="restricoes")

                yield Label("DEPENDÊNCIAS", classes="grupo")
                yield Label("Integrações externas", classes="rotulo")
                yield Input(placeholder="ex.: <serviço externo>", id="integracoes")

                yield Label("Banco de dados", classes="rotulo")
                yield Input(placeholder="ex.: <banco de dados>", id="banco")

    def on_mount(self) -> None:
        for selector, title in (
            ("#painel-entrada", "ENTRADA"),
            ("#painel-revisao", "REVISÃO DE CONTEXTO"),
            ("#painel-gate", "GATE FINAL"),
            ("#painel-resumo-operacao", "RESUMO DA OPERAÇÃO"),
            ("#painel-riscos", "PRINCIPAIS RISCOS"),
            ("#painel-porque", "POR QUÊ?"),
            ("#painel-acoes-sugeridas", "O QUE FAZER?"),
        ):
            self.query_one(selector).border_title = title
        self._reset_actions()
        self._show_state("entrada")
        self._refresh_project_badge()
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

    _STATES = ("entrada", "revisao", "resultado")

    def _show_state(self, state: str) -> None:
        """Um estado por vez. Os tres nunca dividem a tela.

        Era isso que fazia a primeira viewport misturar formulario, gate vazio
        e paineis de uma analise que ainda nao existia.
        """
        for nome in self._STATES:
            self.query_one(f"#estado-{nome}").display = nome == state
        self._state = state

    @property
    def state(self) -> str:
        """Estado visivel. Usado pelos testes de UX e pela navegacao."""
        return getattr(self, "_state", "entrada")

    def _project_options(self) -> list[tuple[str, str]]:
        """Rotulo legivel, valor sendo o `project_id`.

        O que viaja para o `RiskRequest` e o id — o nome de exibicao nunca
        substitui a identidade.
        """
        return [
            (project_display_name(item), item) for item in available_projects()
        ]

    def _refresh_project_badge(self) -> None:
        seletor = self.query_one("#projeto", Select)
        valor = seletor.value
        if valor is Select.BLANK:
            self.query_one("#projeto-badge", Static).update("")
            return
        self.query_one("#projeto-badge", Static).update(render_project_badge(str(valor)))

    def _reload_projects(self, select_id: str | None = None) -> None:
        """Recarrega o seletor depois de criar, editar ou arquivar."""
        seletor = self.query_one("#projeto", Select)
        anterior = seletor.value
        opcoes = self._project_options()
        seletor.set_options(opcoes)
        disponiveis = {valor for _, valor in opcoes}
        alvo = select_id if select_id in disponiveis else None
        if alvo is None and anterior is not Select.BLANK and str(anterior) in disponiveis:
            alvo = str(anterior)
        if alvo is None and opcoes:
            alvo = opcoes[0][1]
        if alvo is not None:
            seletor.value = alvo
        self._refresh_project_badge()

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
        """Pinta o resultado na ordem em que ele e lido.

        Gate, resumo, riscos, por que, o que fazer — e so entao as abas. Nada
        foi removido: o que era seis paineis simultaneos agora e uma visao
        primaria curta mais seis abas, uma aberta por vez.
        """
        gate = self.query_one("#painel-gate", Static)
        gate.set_classes(self._GATE_CLASSES[result.gate])
        gate.update(render_gate_banner(result))

        self.query_one("#painel-resumo-operacao", Static).update(
            render_operation_summary(result)
        )
        self.query_one("#painel-riscos", Static).update(render_top_risks(result))
        self.query_one("#painel-porque", Static).update(render_key_findings(result))
        self.query_one("#painel-acoes-sugeridas", Static).update(
            render_key_recommendations(result)
        )

        # --- abas: a evidencia inteira, uma superficie por vez -------------
        largura = self.size.width
        colunas = 6 if largura >= 128 else (3 if largura >= _NARROW_WIDTH else 2)
        self.query_one("#painel-dimensoes", Static).update(
            render_dimensions_band(result, columns=colunas)
        )
        self.query_one("#painel-alcance", Static).update(
            render_blast_panel(result, columns=1 if largura < _NARROW_WIDTH else 2)
        )
        self.query_one("#contexto-texto", Static).update(render_context_panel(result))
        self.query_one("#cenarios-resumo", Static).update(render_scenarios_summary(result))
        await self._mount_scenarios(result)
        self.query_one("#historico-texto", Static).update(render_historical_panel(result))
        self.query_one("#achados-texto", Static).update(render_findings_panel(result))
        self.query_one("#recomendacoes-texto", Static).update(
            render_all_recommendations(result)
        )
        self.query_one("#tecnicos-texto", Static).update(render_technical_details(result))

        # A aba de abertura e sempre a primeira: reabrir na aba que alguem
        # deixou aberta na analise anterior mostraria detalhe de um resultado
        # que nao esta mais na tela.
        self.query_one("#detalhes", TabbedContent).active = "aba-alcance"
        self._show_state("resultado")

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
        """Propoe o contexto. A analise so roda depois da confirmacao humana.

        Duas etapas de proposito: preencher contexto sozinho e analisar no
        mesmo clique faria o usuario descobrir o que foi inferido DEPOIS de o
        resultado existir — que e como a contaminacao anterior passou.
        """
        try:
            entrada = self._collect()
            # Valida ANTES de propor: prompt vazio, projeto sem capability e
            # ambiente invalido precisam falhar aqui, e nao depois de o
            # usuario revisar uma proposta que nunca poderia ser analisada.
            build_request(entrada)
            proposta = propose(entrada)
        except (ConsoleInputError, ConsoleOperationError) as error:
            self._message(str(error), "erro")
            return

        self._proposal = proposta
        self._pending_entry = entrada
        self.query_one("#revisao-texto", Static).update(render_review(proposta))
        self._show_state("revisao")
        self._message(
            f"{proposta.review_count} item(ns) inferido(s) para revisar. "
            "Confirmar autoriza apenas a análise.",
            "aviso",
        )

    async def action_confirmar(self) -> None:
        """Confirma o contexto e roda a analise.

        A confirmacao diz "o contexto e este". Ela nao diz "pode executar", e
        nao produz PASS: o gate continua sendo do Risk Engine.
        """
        if self._proposal is None or self._pending_entry is None:
            return
        try:
            entrada = apply(self._pending_entry, self._proposal)
            result = analyze(entrada)
        except (ConsoleInputError, ConsoleOperationError) as error:
            self._message(str(error), "erro")
            return

        self.result = result
        await self._paint(result)
        self._apply_gate_to_actions(result)
        self._message("Análise concluída. Nenhuma operação foi executada.", "ok")

    def action_editar(self) -> None:
        self._show_state("entrada")
        self.query_one("#prompt", TextArea).focus()
        self._invalidate_binding()

    async def action_avancar(self) -> None:
        """Ctrl+Enter: o proximo passo do estado atual.

        Analisar na entrada, confirmar na revisao, reanalisar no resultado.
        Nenhum deles executa a operacao analisada — o Risk Engine nunca
        executa, e o atalho nao pode sugerir o contrario.
        """
        if self.state == "revisao":
            await self.action_confirmar()
            return
        await self.action_analisar()

    def action_voltar(self) -> None:
        """Esc: um passo atras, sem descartar o que ja foi analisado."""
        if self.state == "revisao":
            self._descartar_proposta()
            return
        if self.state == "resultado":
            self._show_state("entrada")
            self._message("Entrada. A análise anterior continua disponível.", "")

    def _descartar_proposta(self) -> None:
        self._show_state("entrada")
        self._proposal = None
        self._pending_entry = None
        self._message("Proposta descartada. Nada foi analisado.", "aviso")

    def action_avancadas(self) -> None:
        collapsible = self.query_one("#avancadas", Collapsible)
        collapsible.collapsed = not collapsible.collapsed

    def action_sair(self) -> None:
        self.exit()

    @on(Button.Pressed, "#analisar")
    @on(Button.Pressed, "#acao-reanalisar")
    async def _pressed_analyze(self) -> None:
        await self.action_analisar()

    @on(Button.Pressed, "#revisao-confirmar")
    async def _pressed_confirm(self) -> None:
        await self.action_confirmar()

    @on(Button.Pressed, "#revisao-cancelar")
    def _pressed_cancel(self) -> None:
        self._descartar_proposta()

    @on(Button.Pressed, "#revisao-detalhes")
    def _pressed_details(self) -> None:
        """Volta a entrada com as Configuracoes Avancadas abertas."""
        self._show_state("entrada")
        self.query_one("#avancadas", Collapsible).collapsed = False
        self._message(
            "Configurações Avançadas abertas. Editar um campo o torna declarado.",
            "aviso",
        )

    @on(Button.Pressed, "#novo-projeto")
    def _pressed_new_project(self) -> None:
        def criado(project_id: str | None) -> None:
            if project_id is None:
                return
            # O projeto recem-criado ja fica selecionado: criar para em
            # seguida procurar na lista seria uma etapa sem proposito.
            self._reload_projects(project_id)
            self._message(f"Projeto criado e selecionado: {project_id}", "ok")

        self.push_screen(NovoProjetoScreen(), criado)

    @on(Button.Pressed, "#gerenciar-projetos")
    def _pressed_manage_projects(self) -> None:
        def alterado(project_id: str | None) -> None:
            self._reload_projects(project_id)
            if project_id is not None:
                self._message("Catálogo de projetos atualizado.", "ok")

        self.push_screen(GerenciarProjetosScreen(), alterado)

    @on(Select.Changed, "#projeto")
    def _project_changed(self) -> None:
        self._refresh_project_badge()

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

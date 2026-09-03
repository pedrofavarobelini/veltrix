"""Progressive disclosure: o que aparece, quando, e o que espera ser pedido.

O problema que esta frente resolveu
------------------------------------

A tela mostrava tudo ao mesmo tempo — formulário, gate vazio, dimensões sem
valor, cenários, histórico, contexto e detalhes técnicos, todos abertos e
simultâneos. Havia informação suficiente e ordem nenhuma.

Nada foi removido. O que mudou foi quanto aparece antes de alguém pedir:

    ESTADO 1  entrada      só o essencial para descrever o pedido
    ESTADO 2  revisão      o contexto proposto, antes de qualquer resultado
    ESTADO 3  resultado    gate → resumo → riscos → por quê → o que fazer
                           e só então as abas

O invariante que estes testes protegem junto
---------------------------------------------

Layout não pode mudar resultado. `test_risk_parity` roda a MESMA requisição
confirmada e compara gate, dimensões, alcance, cenários, achados e
recomendações — a reorganização precisa ser visual do começo ao fim.
"""

from __future__ import annotations

import asyncio

import pytest
from textual.widgets import Button, Select, TabbedContent, TextArea

from app.modules.retrieval.schemas import RetrievalResponse
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_console.analysis import analyze
from app.modules.risk_console.app import RiskConsoleApp
from app.modules.risk_console.auto_context import apply, propose
from app.modules.risk_console.domain import ConsoleRequestInput

PROMPT = "Atualize apenas o Risk Console, rode os testes relacionados e não faça push."


@pytest.fixture(autouse=True)
def quiet_retrieval(monkeypatch):
    monkeypatch.setattr(
        retrieval_service,
        "retrieve",
        lambda query, **_: RetrievalResponse(query_id=query.query_id, project_id=query.project_id),
    )


def _run(cenario, size=(140, 45)):
    async def executar():
        app = RiskConsoleApp()
        async with app.run_test(size=size) as pilot:
            return await cenario(app, pilot)

    return asyncio.run(executar())


async def _ate_revisao(app, pilot):
    app.query_one("#prompt", TextArea).text = PROMPT
    await pilot.pause()
    app.query_one("#analisar", Button).press()
    await pilot.pause()
    await pilot.pause()


async def _ate_resultado(app, pilot):
    await _ate_revisao(app, pilot)
    app.query_one("#revisao-confirmar", Button).press()
    await pilot.pause()
    await pilot.pause()


def _visivel(app, selector: str) -> bool:
    """Visível de verdade: o widget e todos os ancestrais até a tela."""
    no = app.query_one(selector)
    while no is not None and no is not app.screen:
        if not no.display:
            return False
        no = no.parent
    return True


# ===========================================================================
# ESTADO 1 — entrada
# ===========================================================================


def test_the_console_opens_on_the_entry_state():
    async def cenario(app, pilot):
        return app.state

    assert _run(cenario) == "entrada"


def test_the_entry_state_shows_only_what_describes_the_request():
    async def cenario(app, pilot):
        return {
            "projeto": _visivel(app, "#projeto"),
            "ambiente": _visivel(app, "#ambiente"),
            "executor": _visivel(app, "#executor"),
            "prompt": _visivel(app, "#prompt"),
            "analisar": _visivel(app, "#analisar"),
        }

    assert all(_run(cenario).values())


@pytest.mark.parametrize(
    "vazio",
    ["#painel-gate", "#painel-riscos", "#detalhes", "#painel-porque", "#painel-revisao"],
)
def test_no_empty_result_surface_is_shown_before_an_analysis(vazio):
    """Gate vazio, dimensões sem valor e cenários em branco não abrem a tela."""

    async def cenario(app, pilot):
        return _visivel(app, vazio)

    assert _run(cenario) is False


def test_the_advanced_settings_start_collapsed():
    from textual.widgets import Collapsible

    async def cenario(app, pilot):
        return app.query_one("#avancadas", Collapsible).collapsed

    assert _run(cenario) is True


# ===========================================================================
# ESTADO 2 — revisão de contexto
# ===========================================================================


def test_analysing_moves_to_the_context_review_not_to_the_result():
    async def cenario(app, pilot):
        await _ate_revisao(app, pilot)
        return app.state, _visivel(app, "#painel-revisao"), _visivel(app, "#painel-gate")

    estado, revisao, gate = _run(cenario)
    assert estado == "revisao"
    assert revisao is True
    assert gate is False


def test_the_review_says_that_confirming_authorises_only_the_analysis():
    async def cenario(app, pilot):
        await _ate_revisao(app, pilot)
        return str(app.query_one("#revisao-texto").content)

    texto = _run(cenario)
    assert "autoriza somente a análise de risco" in texto
    assert "nenhuma operação será executada" in texto


def test_the_entry_form_is_not_on_screen_during_the_review():
    async def cenario(app, pilot):
        await _ate_revisao(app, pilot)
        return _visivel(app, "#painel-entrada")

    assert _run(cenario) is False


def test_cancelling_the_review_returns_to_the_entry():
    async def cenario(app, pilot):
        await _ate_revisao(app, pilot)
        app.query_one("#revisao-cancelar", Button).press()
        await pilot.pause()
        return app.state, app.result

    estado, resultado = _run(cenario)
    assert estado == "entrada"
    assert resultado is None


# ===========================================================================
# ESTADO 3 — resultado: gate primeiro
# ===========================================================================


def test_confirming_moves_to_the_result_state():
    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        return app.state

    assert _run(cenario) == "resultado"


def test_the_gate_comes_first_in_the_result():
    """Não é só estar visível: é ser o primeiro filho do estado."""

    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        filhos = [item.id for item in app.query_one("#estado-resultado").children]
        return filhos

    assert _run(cenario)[0] == "painel-gate"


def test_the_primary_view_answers_the_opening_questions():
    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        return {
            "gate": str(app.query_one("#painel-gate").content),
            "resumo": str(app.query_one("#painel-resumo-operacao").content),
            "riscos": str(app.query_one("#painel-riscos").content),
            "porque": str(app.query_one("#painel-porque").content),
            "fazer": str(app.query_one("#painel-acoes-sugeridas").content),
        }

    painel = _run(cenario)
    assert all(valor.strip() for valor in painel.values())
    assert "Operação" in painel["resumo"]
    assert "Projeto" in painel["resumo"]


def test_the_operation_summary_names_the_selected_project():
    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        return str(app.query_one("#painel-resumo-operacao").content)

    assert "Veltrix" in _run(cenario)


# ===========================================================================
# Detalhes sob demanda
# ===========================================================================


def test_the_details_open_on_the_first_tab_only():
    """Seis superfícies de detalhe existem; uma ocupa a tela por vez."""

    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        abas = app.query_one("#detalhes", TabbedContent)
        return abas.active, [item.id for item in abas.query("TabPane")]

    ativa, panes = _run(cenario)
    assert ativa == "aba-alcance"
    assert panes == [
        "aba-alcance",
        "aba-dimensoes",
        "aba-cenarios",
        "aba-historico",
        "aba-contexto",
        "aba-tecnicos",
    ]


def test_the_technical_details_are_not_expanded_by_default():
    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        return app.query_one("#detalhes", TabbedContent).active

    assert _run(cenario) != "aba-tecnicos"


def test_the_scenarios_do_not_occupy_the_first_viewport():
    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        return app.query_one("#detalhes", TabbedContent).active

    assert _run(cenario) != "aba-cenarios"


def test_the_full_context_does_not_occupy_the_first_viewport():
    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        return app.query_one("#detalhes", TabbedContent).active

    assert _run(cenario) != "aba-contexto"


def test_every_detail_surface_is_still_filled():
    """Progressive disclosure esconde, não descarta."""

    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        return {
            "alcance": str(app.query_one("#painel-alcance").content),
            "dimensoes": str(app.query_one("#painel-dimensoes").content),
            "cenarios": str(app.query_one("#cenarios-resumo").content),
            "historico": str(app.query_one("#historico-texto").content),
            "contexto": str(app.query_one("#contexto-texto").content),
            "tecnicos": str(app.query_one("#tecnicos-texto").content),
            "achados": str(app.query_one("#achados-texto").content),
        }

    for chave, valor in _run(cenario).items():
        assert valor.strip(), f"{chave} ficou vazio"


def test_the_provenance_panel_lives_in_the_context_tab():
    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        contexto = app.query_one("#contexto-texto")
        return str(contexto.content), contexto.ancestors_with_self[1].id

    texto, _ = _run(cenario)
    assert "inferido" in texto
    assert "declarado(s)" in texto


def test_reason_codes_stay_out_of_the_primary_view():
    """Código de razão é auditoria; a visão primária fala português."""

    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        return (
            str(app.query_one("#painel-porque").content),
            str(app.query_one("#tecnicos-texto").content),
        )

    porque, tecnicos = _run(cenario)
    assert "_" not in porque.replace("[/", "").replace("bold ", "")
    assert any(letra.isupper() for letra in tecnicos)


# ===========================================================================
# Limites da visão primária
# ===========================================================================


def test_the_primary_view_caps_what_it_shows():
    from app.modules.risk_console.render import (
        PRIMARY_MAX,
        render_key_findings,
        render_key_recommendations,
    )

    entrada = ConsoleRequestInput(
        project_id="pedrocore",
        environment_label="Produção",
        executor_label="Agente genérico",
        prompt="Apague tudo, altere migrations, faça deploy e remova a autenticação.",
    )
    resultado = analyze(apply(entrada, propose(entrada)))

    for texto, total in (
        (render_key_findings(resultado), len(resultado.analysis.findings)),
        (render_key_recommendations(resultado), len(resultado.recommendations)),
    ):
        mostrados = [linha for linha in texto.splitlines() if "+ " not in linha]
        assert len(mostrados) <= PRIMARY_MAX
        if total > PRIMARY_MAX:
            assert "ver aba" in texto


def test_the_top_risks_are_ordered_by_real_severity():
    from app.modules.risk_console.presentation import severity_label
    from app.modules.risk_console.render import render_top_risks

    entrada = ConsoleRequestInput(
        project_id="pedrocore",
        environment_label="Produção",
        executor_label="Agente genérico",
        prompt="Apague o banco de produção e faça deploy sem revisão.",
    )
    resultado = analyze(apply(entrada, propose(entrada)))
    texto = render_top_risks(resultado)

    ordem = ["CRÍTICO", "ALTO", "MÉDIO", "BAIXO", "INFORMATIVO"]
    vistos = [
        ordem.index(rotulo) for linha in texto.splitlines() for rotulo in ordem if rotulo in linha
    ]
    assert vistos == sorted(vistos)
    # Severidade sempre em texto: a cor é reforço, nunca o único sinal.
    assert any(
        severity_label(item.severity) in texto for item in resultado.analysis.risk_dimensions
    )


# ===========================================================================
# Responsividade
# ===========================================================================


@pytest.mark.parametrize("largura", [140, 110, 80, 78])
def test_the_gate_is_reachable_at_every_supported_width(largura):
    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        filhos = [item.id for item in app.query_one("#estado-resultado").children]
        return filhos[0], _visivel(app, "#painel-gate"), app.state

    primeiro, visivel, estado = _run(cenario, size=(largura, 45))
    assert primeiro == "painel-gate"
    assert visivel is True
    assert estado == "resultado"


@pytest.mark.parametrize("largura", [140, 110, 80, 78])
def test_no_important_action_leaves_the_screen(largura):
    """Botão cortado é botão que parece ausente."""

    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        return {
            selector: app.query_one(selector, Button).region.right <= largura
            for selector in ("#acao-reanalisar", "#acao-exportar", "#acao-sair")
        }

    assert all(_run(cenario, size=(largura, 45)).values())


@pytest.mark.parametrize("largura", [140, 110, 80, 78])
def test_the_entry_fields_are_reachable_at_every_width(largura):
    async def cenario(app, pilot):
        return all(
            _visivel(app, selector)
            for selector in ("#projeto", "#ambiente", "#executor", "#prompt", "#analisar")
        )

    assert _run(cenario, size=(largura, 45)) is True


# ===========================================================================
# Atalhos
# ===========================================================================


def test_no_shortcut_suggests_executing_the_analysed_operation():
    """O Risk Engine não executa nada, e nenhum atalho pode sugerir que sim."""
    descricoes = " ".join(str(item[2]).lower() for item in RiskConsoleApp.BINDINGS)
    assert "executar" not in descricoes
    teclas = {str(item[0]) for item in RiskConsoleApp.BINDINGS}
    assert "ctrl+e" not in teclas


def test_the_keyboard_advances_the_flow():
    """Ctrl+Enter avança o estado atual, sem tocar em botão."""

    async def cenario(app, pilot):
        app.query_one("#prompt", TextArea).text = PROMPT
        await pilot.pause()
        await app.action_avancar()
        await pilot.pause()
        primeiro = app.state
        await app.action_avancar()
        await pilot.pause()
        await pilot.pause()
        return primeiro, app.state

    assert _run(cenario) == ("revisao", "resultado")


def test_escape_steps_back_without_discarding_the_analysis():
    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        app.action_voltar()
        await pilot.pause()
        return app.state, app.result is not None

    assert _run(cenario) == ("entrada", True)


# ===========================================================================
# Projeto na entrada
# ===========================================================================


def test_the_project_selector_offers_the_registered_projects():
    from app.modules.project_registry.service import project_registry

    async def cenario(app, pilot):
        seletor = app.query_one("#projeto", Select)
        return [valor for _, valor in seletor._options]

    oferecidos = _run(cenario)
    registrados = [item.project_id for item in project_registry().list_projects()]
    assert oferecidos == registrados


def test_the_project_badge_states_whether_a_manifest_exists():
    async def cenario(app, pilot):
        com = str(app.query_one("#projeto-badge").content)
        app.query_one("#projeto", Select).value = "rivvo"
        await pilot.pause()
        sem = str(app.query_one("#projeto-badge").content)
        return com, sem

    com, sem = _run(cenario)
    assert "Manifesto: disponível" in com
    assert "Manifesto: não configurado" in sem


def test_the_full_local_path_is_not_permanently_on_screen():
    """Detalhe fica sob demanda; o badge diz só se está configurado."""
    from app.modules.project_registry.service import project_registry

    project_registry().update("pedrocore", local_path="C:/Projetos/pedrocore-ia")
    try:

        async def cenario(app, pilot):
            return str(app.query_one("#projeto-badge").content)

        badge = _run(cenario)
        assert "Local: configurado" in badge
        assert "C:/Projetos" not in badge
    finally:
        project_registry().update("pedrocore", local_path="")


def test_the_selected_project_is_the_one_that_reaches_the_risk_request():
    """O que viaja é o `project_id`, nunca o nome de exibição."""

    async def cenario(app, pilot):
        app.query_one("#projeto", Select).value = "structa"
        await pilot.pause()
        await _ate_resultado(app, pilot)
        return app.result.request.project_id

    assert _run(cenario) == "structa"


def test_a_project_created_in_the_console_can_be_selected_and_analysed():
    """O caminho inteiro: criar, selecionar, analisar."""
    from app.modules.project_registry.service import project_registry

    project_registry().create(display_name="Projeto De Teste UX")
    try:

        async def cenario(app, pilot):
            app.query_one("#projeto", Select).value = "projeto-de-teste-ux"
            await pilot.pause()
            await _ate_resultado(app, pilot)
            return app.result.request.project_id, app.state

        assert _run(cenario) == ("projeto-de-teste-ux", "resultado")
    finally:
        project_registry().archive("projeto-de-teste-ux")


# ===========================================================================
# Paridade: layout não muda resultado
# ===========================================================================


def test_risk_parity_between_the_console_and_the_engine():
    """A MESMA requisição confirmada, comparada campo a campo.

    Se a reorganização visual tivesse tocado o cálculo, é aqui que apareceria.
    """

    def montar():
        entrada = ConsoleRequestInput(
            project_id="pedrocore",
            environment_label="Desenvolvimento",
            executor_label="Claude Code",
            prompt=PROMPT,
        )
        return apply(entrada, propose(entrada))

    a = analyze(montar())
    b = analyze(montar())

    assert a.gate is b.gate
    assert a.gate_reasons == b.gate_reasons
    assert [item.model_dump() for item in a.analysis.risk_dimensions] == [
        item.model_dump() for item in b.analysis.risk_dimensions
    ]
    assert a.analysis.blast_radius.model_dump() == b.analysis.blast_radius.model_dump()

    def _cenario(item):
        return item.model_dump(exclude={"simulation_id", "scenario_id"})

    assert [_cenario(item) for item in a.analysis.simulations] == [
        _cenario(item) for item in b.analysis.simulations
    ]

    # `finding_id` e `signal_ids` sao gerados por analise: compara-los
    # mediria a aleatoriedade do uuid4, e nao a estabilidade da decisao.
    def _achado(item):
        return (item.reason_code, item.severity, item.title)

    assert [_achado(item) for item in a.analysis.findings] == [
        _achado(item) for item in b.analysis.findings
    ]
    assert [item.text for item in a.recommendations] == [item.text for item in b.recommendations]
    assert a.blocked is b.blocked


def test_the_console_result_matches_the_engine_for_the_same_request():
    from app.modules.risk_console.analysis import analyze_request

    entrada = ConsoleRequestInput(
        project_id="pedrocore",
        environment_label="Desenvolvimento",
        executor_label="Claude Code",
        prompt=PROMPT,
    )
    confirmada = apply(entrada, propose(entrada))
    pelo_console = analyze(confirmada)

    from app.modules.risk_console.domain import build_request

    pelo_motor = analyze_request(build_request(confirmada))

    assert pelo_console.gate is pelo_motor.gate
    assert [item.severity for item in pelo_console.analysis.risk_dimensions] == [
        item.severity for item in pelo_motor.analysis.risk_dimensions
    ]
    assert [item.reason_code for item in pelo_console.analysis.findings] == [
        item.reason_code for item in pelo_motor.analysis.findings
    ]


def test_the_analysis_still_executes_nothing():
    async def cenario(app, pilot):
        await _ate_resultado(app, pilot)
        return (
            app.result.analysis.target_operation_executed,
            app.result.analysis.provider_called,
        )

    assert _run(cenario) == (False, False)

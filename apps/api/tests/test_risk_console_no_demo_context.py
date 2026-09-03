"""Regressão da contaminação encontrada na homologação humana.

O que aconteceu
---------------

As Configurações Avançadas usavam valores de domínio plausíveis como
placeholder — `write:billing`, `module:auth`, `stripe`, `pedrocore`. Onze
campos exibindo texto plausível fazem a tela ler como formulário **preenchido**,
e não como formulário vazio com dicas.

Quem abriu o console tratou aqueles valores como o estado atual. A análise saiu
com contexto de billing, auth e integração externa que ninguém quis declarar —
e apareceram riscos de dados e migração que não pertenciam ao pedido.

O mecanismo nunca submeteu placeholder: `Input.value` sempre foi vazio. O
defeito foi de **design**, e o efeito foi real.

O que estes casos protegem
--------------------------

1. nenhum valor de demonstração é submetido a partir de um console recém-aberto;
2. um pedido limitado ao Risk Console não produz contexto de billing, banco ou
   integração externa sem declaração;
3. a origem de cada fato — declarado, inferido, padrão, desconhecido — não se
   mistura em silêncio.
"""

from __future__ import annotations

import asyncio

import pytest

from app.modules.retrieval.schemas import RetrievalResponse
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_console.analysis import analyze
from app.modules.risk_console.domain import (
    ConsoleRequestInput,
    Provenance,
    build_request,
    context_provenance,
    declared_context_fields,
)
from app.modules.risk_console.presentation import RULE_EXPLANATIONS, humanize_finding
from app.modules.risk_console.render import (
    render_context_panel,
    render_findings_panel,
    render_technical_details,
)

# Os valores exatos que apareceram na homologação. Se qualquer um deles
# reaparecer como valor submetido, estes testes falham.
VALORES_DEMO = (
    "write:billing",
    "module:billing",
    "module:auth",
    "billing",
    "stripe",
    "somente local",
    "suíte de billing passa",
)

PROMPT_CONSOLE = (
    "Melhorar o espaçamento dos painéis do Risk Console e o alinhamento "
    "dos rótulos na tela de entrada."
)


@pytest.fixture(autouse=True)
def quiet_retrieval(monkeypatch):
    monkeypatch.setattr(
        retrieval_service,
        "retrieve",
        lambda query, **_: RetrievalResponse(
            query_id=query.query_id, project_id=query.project_id
        ),
    )


def _console_entry(**overrides) -> ConsoleRequestInput:
    valores = dict(
        project_id="pedrocore",
        environment_label="Desenvolvimento",
        executor_label="Claude Code",
        prompt=PROMPT_CONSOLE,
    )
    valores.update(overrides)
    return ConsoleRequestInput(**valores)


# ===========================================================================
# 1. Nenhum valor de demonstração é submetido
# ===========================================================================


def test_no_advanced_placeholder_is_a_plausible_domain_value():
    """A causa raiz: dica que parece valor convida a ser aceita como valor."""
    from app.modules.risk_console.app import RiskConsoleApp

    async def cenario():
        from textual.widgets import Input

        app = RiskConsoleApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.pause()
            return [item.placeholder for item in app.query(Input)]

    placeholders = asyncio.run(cenario())
    assert placeholders, "nenhum campo avançado encontrado"
    for dica in placeholders:
        assert dica.startswith("ex.:"), f"placeholder sem marca de exemplo: {dica!r}"
        assert "<" in dica and ">" in dica, (
            f"placeholder {dica!r} ainda parece um valor concreto; uma dica "
            "precisa ser impossível de confundir com estado do formulário"
        )
        for demo in VALORES_DEMO:
            assert demo not in dica, f"valor de demonstração ainda em uso: {demo}"


def test_a_freshly_opened_console_submits_only_what_the_prompt_supports():
    """Contexto resolvido precisa ser rastreável ao prompt ou ao projeto."""
    from app.modules.risk_console.app import RiskConsoleApp

    async def cenario():
        from textual.widgets import Button, TextArea

        app = RiskConsoleApp()
        async with app.run_test(size=(140, 45)) as pilot:
            # Nada é tocado além do prompt: console recém-aberto.
            app.query_one("#prompt", TextArea).text = PROMPT_CONSOLE
            await pilot.pause()
            app.query_one("#analisar", Button).press()
            await pilot.pause()
            await pilot.pause()
            app.query_one("#revisao-confirmar", Button).press()
            await pilot.pause()
            await pilot.pause()
            return app.result

    resultado = asyncio.run(cenario())
    assert resultado is not None

    # Com o Auto Context, o contexto deixa de vir vazio — mas TUDO o que vem
    # precisa ser rastreavel ao prompt ou a superficie declarada do projeto.
    # O que nao pode aparecer e valor que ninguem citou.
    pedido = resultado.request
    assert pedido.context.external_integrations == []
    assert pedido.context.constraints == []
    assert pedido.context.acceptance_criteria == []
    assert pedido.context.database is None
    assert pedido.context.rollback_plan_present is False

    # O alvo inferido veio da area declarada citada no proprio prompt.
    assert pedido.requested_operation.targets == ["risk_console"]
    assert pedido.context.allowed_scope == ["module:risk_console"]


def test_no_demo_value_reaches_the_engine_from_an_empty_form():
    """A asserção direta contra os valores que apareceram na homologação."""
    from app.modules.risk_console.app import RiskConsoleApp

    async def cenario():
        from textual.widgets import Button, TextArea

        app = RiskConsoleApp()
        async with app.run_test(size=(140, 45)) as pilot:
            app.query_one("#prompt", TextArea).text = PROMPT_CONSOLE
            await pilot.pause()
            app.query_one("#analisar", Button).press()
            await pilot.pause()
            await pilot.pause()
            app.query_one("#revisao-confirmar", Button).press()
            await pilot.pause()
            await pilot.pause()
            return app.result.request.model_dump_json()

    submetido = asyncio.run(cenario()).lower()
    for demo in VALORES_DEMO:
        assert demo.lower() not in submetido, (
            f"valor de demonstração {demo!r} foi submetido a partir de um "
            "console recém-aberto"
        )


# ===========================================================================
# 2. Um pedido sobre o Risk Console não vira risco de dados ou migração
# ===========================================================================


def test_a_risk_console_prompt_does_not_produce_database_context():
    """O caso exato que a homologação encontrou."""
    resultado = analyze(_console_entry())
    pedido = resultado.request

    assert pedido.context.database is None
    assert pedido.context.external_integrations == []

    # Olha o CONTEXTO e os ALVOS, e nao o JSON inteiro: `schema_version` e um
    # campo do proprio contrato, e casaria com "schema" sem haver contaminacao.
    contexto = " ".join(
        [
            *pedido.permissions,
            *pedido.context.allowed_scope,
            *pedido.context.forbidden_scope,
            *pedido.context.external_integrations,
            *pedido.context.required_tests,
            *pedido.requested_operation.targets,
            pedido.context.database or "",
        ]
    ).lower()
    for termo in ("billing", "stripe", "auth", "migration", "schema"):
        assert termo not in contexto, f"contexto de {termo!r} apareceu sem declaração"


def test_a_risk_console_prompt_triggers_no_data_or_migration_rule():
    resultado = analyze(_console_entry())
    codigos = {item.reason_code for item in resultado.analysis.deterministic_rules}
    for proibido in (
        "DATABASE_MIGRATION",
        "SCHEMA_CHANGE",
        "DELETE_OPERATION",
        "AUTH_AUTHZ_CHANGE",
        "EXTERNAL_INTEGRATION",
    ):
        assert proibido not in codigos, f"{proibido} apareceu sem declaração"


def test_data_and_migration_dimensions_stay_informational():
    from app.modules.risk_engine.pre_execution_schemas import RiskDimensionName
    from app.modules.risk_engine.schemas import RiskSeverity

    resultado = analyze(_console_entry())
    por_dimensao = {i.dimension: i.severity for i in resultado.analysis.risk_dimensions}
    assert por_dimensao[RiskDimensionName.DATA] is RiskSeverity.INFO
    assert por_dimensao[RiskDimensionName.MIGRATION] is RiskSeverity.INFO


def test_no_data_corruption_or_migration_scenario_is_emitted():
    """Cenário irrelevante emitido treina quem lê a ignorar a lista."""
    resultado = analyze(_console_entry())
    nomes = {item.scenario for item in resultado.analysis.simulations}
    assert "data_corruption" not in nomes
    assert "migration_failure" not in nomes
    assert "external_service_failure" not in nomes


def test_declaring_a_database_is_what_brings_migration_risk_back():
    """A ausência de risco não é cegueira: declarado, o risco aparece."""
    resultado = analyze(
        _console_entry(
            prompt="Executar a migration para alterar o schema da tabela de billing",
            database="pedrocore",
            permissions=["migrate:billing"],
        )
    )
    codigos = {item.reason_code for item in resultado.analysis.deterministic_rules}
    assert "DATABASE_MIGRATION" in codigos
    assert resultado.request.context.database == "pedrocore"


# ===========================================================================
# 3. Proveniência não se mistura em silêncio
# ===========================================================================


def test_an_empty_form_declares_nothing():
    assert declared_context_fields(_console_entry()) == []


def test_untouched_selects_are_defaulted_not_declared():
    """O humano não escolheu 'Desenvolvimento'; o console escolheu por ele."""
    origem = context_provenance(_console_entry())
    assert origem["project_id"] is Provenance.DEFAULTED
    assert origem["environment"] is Provenance.DEFAULTED
    assert origem["executor"] is Provenance.DEFAULTED


def test_a_changed_select_becomes_declared():
    origem = context_provenance(_console_entry(environment_label="Produção"))
    assert origem["environment"] is Provenance.DECLARED


def test_an_operation_left_blank_is_inferred_never_declared():
    origem = context_provenance(_console_entry())
    assert origem["operation"] is Provenance.INFERRED


def test_an_operation_chosen_by_hand_is_declared():
    from app.modules.risk_engine.schemas import OperationKind

    origem = context_provenance(_console_entry(operation=OperationKind.WRITE))
    assert origem["operation"] is Provenance.DECLARED


def test_absent_context_is_unknown_not_false():
    """Checkbox desmarcada é 'ninguém declarou', não 'não há plano'."""
    origem = context_provenance(_console_entry())
    assert origem["rollback_plan_present"] is Provenance.UNKNOWN
    assert origem["permissions"] is Provenance.UNKNOWN
    assert origem["database"] is Provenance.UNKNOWN


def test_declared_fields_are_reported_as_declared():
    entrada = _console_entry(
        permissions=["write:risk_console"], allowed_scope=["module:risk_console"]
    )
    assert declared_context_fields(entrada) == ["allowed_scope", "permissions"]


def test_the_result_carries_the_provenance_of_its_context():
    resultado = analyze(_console_entry())
    assert resultado.provenance
    assert resultado.provenance["permissions"] is Provenance.UNKNOWN


def test_the_context_panel_shows_what_was_not_declared():
    """Contaminação silenciosa foi o problema; visibilidade é a defesa."""
    painel = render_context_panel(analyze(_console_entry()))
    assert "—" in painel
    assert "padrão" in painel
    assert "inferido" in painel
    assert "0 campo(s) declarado(s)" in painel


def test_the_context_panel_counts_declared_fields():
    resultado = analyze(_console_entry(permissions=["write:risk_console"]))
    assert "1 campo(s) declarado(s)" in render_context_panel(resultado)


# ===========================================================================
# 4. Reason code sai dos ACHADOS e continua nos DETALHES TÉCNICOS
# ===========================================================================


def test_a_rule_finding_is_rendered_as_a_human_sentence():
    assert (
        humanize_finding("Regra determinística acionada: database_migration.")
        == "O pedido envolve migração de banco de dados."
    )


def test_every_deterministic_rule_has_a_human_explanation():
    """Regra sem frase humana volta a expor o identificador ao usuário."""
    from app.modules.risk_engine.rules import _RULES

    for regra in _RULES:
        assert regra.rule_id in RULE_EXPLANATIONS, (
            f"regra {regra.rule_id!r} sem explicação humana"
        )


def test_a_finding_that_is_already_human_passes_through_untouched():
    original = "O pedido não delimita operação, escopo, validação e reversão."
    assert humanize_finding(original) == original


def test_reason_codes_are_absent_from_the_findings_panel():
    resultado = analyze(
        _console_entry(
            prompt="Executar a migration para alterar o schema da tabela de billing",
            permissions=["migrate:billing"],
            database="pedrocore",
        )
    )
    achados = render_findings_panel(resultado)
    assert "database_migration" not in achados
    assert "schema_change" not in achados
    assert "Regra determinística acionada" not in achados
    assert "migração de banco de dados" in achados


def test_reason_codes_remain_available_in_technical_details():
    """Fora da leitura, não fora do alcance de quem audita."""
    resultado = analyze(
        _console_entry(
            prompt="Executar a migration para alterar o schema da tabela de billing",
            permissions=["migrate:billing"],
            database="pedrocore",
        )
    )
    tecnicos = render_technical_details(resultado)
    assert "DATABASE_MIGRATION" in tecnicos
    assert "database_migration" in tecnicos


# ===========================================================================
# 5. O mecanismo oficial continua sendo o único a inferir
# ===========================================================================


def test_the_operation_is_inferred_by_the_engine_table_not_by_the_console():
    from app.modules.risk_engine.analyzers import infer_operation_kind

    entrada = _console_entry(prompt="Alterar o layout do Risk Console")
    pedido = build_request(entrada)
    assert pedido.requested_operation.kind is infer_operation_kind(entrada.prompt)


def test_an_unrecognisable_prompt_stays_unknown_instead_of_guessing():
    """Não saber a operação é um fato; inventá-la seria pior que bloquear."""
    from app.modules.risk_engine.schemas import OperationKind

    pedido = build_request(_console_entry(prompt="O painel da direita, ontem."))
    assert pedido.requested_operation.kind is OperationKind.UNKNOWN


def test_improving_something_is_recognised_as_writing():
    """"Melhorar o espaçamento" É uma alteração.

    A lacuna apareceu quando a classificação de alvo passou a depender do
    verbo: sem "melhorar" na tabela, nenhum verbo de mutação precedia a área,
    e o alvo sumia — o oposto de inventar escopo, mas errado do mesmo jeito.
    """
    from app.modules.risk_engine.schemas import OperationKind

    pedido = build_request(
        _console_entry(prompt="Melhorar o espaçamento dos painéis do Risk Console")
    )
    assert pedido.requested_operation.kind is OperationKind.WRITE

"""Auto Context — resolução automática de contexto antes da análise.

O que esta camada resolve, e o que ela nunca pode fazer
------------------------------------------------------

Resolve: onze campos avançados deixam de ser obrigatórios no fluxo diário.

Nunca pode: autorizar. O princípio que atravessa todos os casos abaixo é

    capacidade pedida  !=  permissão concedida

    pedida  ∩  executor  ∩  projeto  ∩  política  =  efetiva

O prompt pode pedir `git.push`. Isso não torna push permitido, e metade destes
casos existe para provar exatamente isso.
"""

from __future__ import annotations

import asyncio

import pytest

from app.modules.retrieval.schemas import RetrievalResponse
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_console.auto_context import apply, propose, render_review
from app.modules.risk_console.domain import ConsoleRequestInput
from app.modules.risk_intake.builder import auto_context_builder
from app.modules.risk_intake.capabilities import (
    EXECUTOR_PROFILES,
    PROJECT_SURFACES,
    TechnicalCapability,
    executor_profile,
    project_surface,
)
from app.modules.risk_intake.schemas import (
    Confidence,
    ContextOrigin,
    EffectivePermission,
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


def _entry(prompt: str, **overrides) -> ConsoleRequestInput:
    valores = dict(
        project_id="pedrocore",
        environment_label="Desenvolvimento",
        executor_label="Claude Code",
        prompt=prompt,
    )
    valores.update(overrides)
    return ConsoleRequestInput(**valores)


def _build(prompt: str, **kwargs):
    valores = dict(
        prompt=prompt,
        project_id="pedrocore",
        environment="development",
        executor="claude-code",
    )
    valores.update(kwargs)
    return auto_context_builder.build(**valores)


def _permission(proposta, capability):
    return proposta.permission(capability)


# ===========================================================================
# Casos obrigatórios
# ===========================================================================


def test_case_a_update_the_console_run_tests_do_not_push():
    """"Atualize apenas o Risk Console, rode os testes e não faça push." """
    proposta = _build("Atualize apenas o Risk Console, rode os testes e não faça push.")

    operacao = proposta.field("operation")
    assert operacao.values[0] in {"WRITE", "EXECUTE"}

    assert "risk_console" in proposta.field("targets").values

    push = _permission(proposta, TechnicalCapability.GIT_PUSH)
    assert push.forbidden_by_prompt is True
    assert push.effective is EffectivePermission.FORBIDDEN

    testes = _permission(proposta, TechnicalCapability.TESTS)
    assert testes.requested is True

    banco = proposta.field("database")
    assert banco.origin is ContextOrigin.UNKNOWN
    assert _permission(proposta, TechnicalCapability.MIGRATION).requested is False


def test_case_b_change_the_schema_and_run_a_migration():
    """"Altere o schema e execute uma migration." """
    proposta = _build("Altere o schema e execute uma migration.")

    assert proposta.field("operation").values == ("MIGRATE",)
    assert _permission(proposta, TechnicalCapability.MIGRATION).requested is True

    rollback = proposta.field("rollback_requirement")
    assert rollback.values == ("required",)
    assert rollback.origin is ContextOrigin.POLICY_DERIVED


def test_case_b_preserves_the_migration_risk_downstream():
    """A proposta não pode apagar o risco que o pedido realmente tem."""
    from app.modules.risk_console.analysis import analyze

    entrada = _entry("Altere o schema e execute uma migration.")
    resultado = analyze(apply(entrada, propose(entrada)))
    codigos = {i.reason_code for i in resultado.analysis.deterministic_rules}
    assert "DATABASE_MIGRATION" in codigos
    assert "SCHEMA_CHANGE" in codigos


def test_case_c_docs_only_nothing_else():
    """"Atualize apenas documentação. Não altere código, banco ou migrations." """
    proposta = _build(
        "Atualize apenas documentação. Não altere código, banco ou migrations."
    )
    assert "documentação" in proposta.field("targets").values

    for capacidade in (TechnicalCapability.DATABASE, TechnicalCapability.MIGRATION):
        decisao = _permission(proposta, capacidade)
        assert decisao.requested is False
        assert decisao.forbidden_by_prompt is True
        assert decisao.effective is EffectivePermission.FORBIDDEN

    assert proposta.field("operation").values == ("WRITE",)


def test_case_c_fabricates_no_migration():
    from app.modules.risk_console.analysis import analyze

    entrada = _entry(
        "Atualize apenas documentação. Não altere código, banco ou migrations."
    )
    resultado = analyze(apply(entrada, propose(entrada)))
    codigos = {i.reason_code for i in resultado.analysis.deterministic_rules}
    assert "DATABASE_MIGRATION" not in codigos
    assert "SCHEMA_CHANGE" not in codigos


def test_case_d_commit_but_do_not_push():
    """"Faça commit, mas não faça push." """
    proposta = _build("Faça commit, mas não faça push.")

    commit = _permission(proposta, TechnicalCapability.GIT_COMMIT)
    push = _permission(proposta, TechnicalCapability.GIT_PUSH)

    assert commit.requested is True
    assert push.requested is False
    assert push.forbidden_by_prompt is True
    assert push.effective is EffectivePermission.FORBIDDEN


def test_case_e_an_ambiguous_prompt_invents_no_broad_scope():
    """"corrija tudo" — ambiguidade não vira autorização ampla."""
    proposta = _build("corrija tudo")

    alvos = proposta.field("targets")
    assert alvos.values == ()
    assert alvos.origin is ContextOrigin.UNKNOWN
    assert alvos.confirmation_required is True

    escopo = proposta.field("allowed_scope")
    assert escopo.values == ()
    assert escopo.origin is ContextOrigin.UNKNOWN


def test_case_e_an_ambiguous_prompt_proposes_no_permission():
    """Sem alvo, nenhuma permissão é proposta — o motor bloqueia, e é o certo."""
    from app.modules.risk_console.analysis import analyze
    from app.modules.risk_engine.execution_contract_schemas import RiskGate

    entrada = _entry("corrija tudo")
    aplicada = apply(entrada, propose(entrada))
    assert aplicada.permissions == []

    resultado = analyze(aplicada)
    assert resultado.gate is RiskGate.BLOCK
    assert "PERMISSION_CONFLICT" in resultado.gate_reasons


def test_case_f_a_capability_the_executor_lacks_is_never_granted():
    """Executor sem a capacidade: pedido continua pedido, não vira permissão."""
    proposta = _build("Faça push das alterações.", executor="generic-agent")

    push = _permission(proposta, TechnicalCapability.GIT_PUSH)
    assert push.requested is True
    assert push.executor_supports is False
    assert push.effective is EffectivePermission.FORBIDDEN
    assert "EXECUTOR_LACKS_CAPABILITY" in push.reason_codes
    assert push in proposta.conflicts


def test_case_g_a_policy_denial_never_becomes_a_grant():
    """Política nega: pedido segue registrado, permissão efetiva não sai."""
    proposta = _build(
        "Execute a migration em produção.",
        environment="ambiente-que-nao-existe",
    )
    migracao = _permission(proposta, TechnicalCapability.MIGRATION)
    assert migracao.requested is True
    assert migracao.policy_allows is False
    assert migracao.effective is EffectivePermission.FORBIDDEN
    assert "POLICY_DENIED" in migracao.reason_codes


def test_case_g_the_risk_gate_still_decides():
    """Auto Context não substitui o gate: quem decide continua sendo o motor."""
    from app.modules.risk_console.analysis import analyze

    entrada = _entry("Altere o schema e execute uma migration.")
    resultado = analyze(apply(entrada, propose(entrada)))
    assert resultado.gate is not None
    assert resultado.gate_reasons


# ===========================================================================
# Interseção de permissão
# ===========================================================================


def test_requesting_a_capability_is_not_receiving_it():
    """O princípio, isolado."""
    proposta = _build("Faça push.", executor="generic-agent")
    push = _permission(proposta, TechnicalCapability.GIT_PUSH)
    assert push.requested is True
    assert push.effective is not EffectivePermission.GRANTED


def test_a_capability_not_requested_is_unknown_not_granted():
    proposta = _build("Leia a documentação.")
    deploy = _permission(proposta, TechnicalCapability.DEPLOYMENT)
    assert deploy.requested is False
    assert deploy.effective is EffectivePermission.UNKNOWN
    assert deploy.capability not in proposta.granted()


def test_an_unknown_project_grants_nothing():
    """Projeto sem superfície declarada não recebe permissão por omissão."""
    proposta = _build("Altere o módulo.", project_id="projeto-fantasma")
    escrita = _permission(proposta, TechnicalCapability.FILESYSTEM_WRITE)
    assert escrita.requested is True
    assert escrita.effective is EffectivePermission.UNKNOWN
    assert "PROJECT_UNKNOWN" in escrita.reason_codes


def test_an_unknown_executor_grants_nothing():
    proposta = _build("Altere o módulo.", executor="executor-desconhecido")
    escrita = _permission(proposta, TechnicalCapability.FILESYSTEM_WRITE)
    assert escrita.effective is EffectivePermission.UNKNOWN
    assert "EXECUTOR_UNKNOWN" in escrita.reason_codes


def test_a_prompt_prohibition_beats_every_other_layer():
    """O humano dizendo 'não faça' é o sinal mais forte que existe."""
    proposta = _build("Altere o Risk Console, mas não faça push.")
    push = _permission(proposta, TechnicalCapability.GIT_PUSH)
    assert push.effective is EffectivePermission.FORBIDDEN
    assert push.reason_codes[0] == "FORBIDDEN_BY_PROMPT"


def test_only_granted_capabilities_become_submitted_permissions():
    """Capacidade pedida e negada NÃO entra na requisição: ela é conflito."""
    entrada = _entry("Atualize o Risk Console e faça push.", executor_label="Agente genérico")
    proposta = propose(entrada)
    aplicada = apply(entrada, proposta)
    assert not any("push" in item for item in aplicada.permissions)


def test_conflicts_are_surfaced_never_hidden():
    proposta = _build("Faça push.", executor="generic-agent")
    assert proposta.conflicts
    assert "CONFLITO" in render_review(proposta)


# ===========================================================================
# Proveniência
# ===========================================================================


def test_a_declared_field_is_never_overwritten_by_inference():
    proposta = _build(
        "Atualize o Risk Console.",
        declared={"targets": ("module:escolhido-a-mao",)},
    )
    alvos = proposta.field("targets")
    assert alvos.origin is ContextOrigin.DECLARED
    assert alvos.values == ("module:escolhido-a-mao",)


def test_policy_is_not_presented_as_a_user_declaration():
    """"Política disse" e "você disse" não podem se confundir."""
    proposta = _build("Altere o schema e execute uma migration.")
    assert proposta.field("rollback_requirement").origin is ContextOrigin.POLICY_DERIVED
    assert proposta.field("effective_permissions").origin is ContextOrigin.POLICY_DERIVED


def test_inference_is_marked_as_inference():
    proposta = _build("Atualize o Risk Console.")
    assert proposta.field("targets").origin is ContextOrigin.INFERRED


def test_confidence_is_categorical_never_a_fake_percentage():
    """Precisão que o método não sustenta é decoração."""
    proposta = _build("Atualize o Risk Console.")
    for campo in proposta.fields:
        assert campo.confidence in {Confidence.HIGH, Confidence.MEDIUM, Confidence.LOW}


def test_every_proposed_field_explains_itself():
    proposta = _build("Atualize o Risk Console e rode os testes.")
    for campo in proposta.fields:
        assert campo.reason and campo.reason[0].isupper()


def test_mutating_inferences_require_confirmation():
    """O que muda estado e não veio do humano precisa de revisão."""
    proposta = _build("Atualize o Risk Console.")
    assert proposta.field("operation").confirmation_required is True
    assert proposta.review_count > 0


def test_the_counts_match_the_fields():
    proposta = _build("Atualize o Risk Console e rode os testes.")
    total = (
        proposta.declared_count
        + proposta.inferred_count
        + proposta.policy_count
        + proposta.unknown_count
    )
    assert total == len(proposta.fields)


# ===========================================================================
# Segurança: o que o Auto Context nunca pode fazer
# ===========================================================================


def test_the_proposal_declares_it_authorizes_nothing():
    proposta = _build("Atualize o Risk Console.")
    assert proposta.authorizes_execution is False
    assert proposta.replaces_risk_gate is False
    assert proposta.ai_was_authority is False


def test_the_proposal_never_removes_a_forbidden_scope():
    entrada = _entry(
        "Atualize o Risk Console.", forbidden_scope=["module:auth", "module:billing"]
    )
    aplicada = apply(entrada, propose(entrada))
    assert "module:auth" in aplicada.forbidden_scope
    assert "module:billing" in aplicada.forbidden_scope


def test_a_prompt_prohibition_is_added_to_the_forbidden_scope():
    entrada = _entry("Atualize o Risk Console. Não faça push.")
    aplicada = apply(entrada, propose(entrada))
    assert "git.push" in aplicada.forbidden_scope


def test_unknown_never_becomes_allowed():
    proposta = _build("Leia a documentação.")
    for decisao in proposta.permissions:
        if decisao.effective is EffectivePermission.UNKNOWN:
            assert decisao.capability not in proposta.granted()


def test_the_builder_never_executes_the_target_operation():
    """Propor não é executar, e o objeto diz isso de si mesmo."""
    from app.modules.risk_console.analysis import analyze

    entrada = _entry("Execute os testes do Risk Console.")
    resultado = analyze(apply(entrada, propose(entrada)))
    assert resultado.analysis.target_operation_executed is False
    assert resultado.analysis.provider_called is False


def test_confirming_the_context_does_not_produce_an_automatic_pass():
    """Confirmar contexto != aprovar execução."""
    from app.modules.risk_console.analysis import analyze
    from app.modules.risk_engine.execution_contract_schemas import RiskGate

    entrada = _entry("corrija tudo")
    resultado = analyze(apply(entrada, propose(entrada)))
    assert resultado.gate is not RiskGate.PASS


# ===========================================================================
# Neutralidade e fallback
# ===========================================================================


def test_no_project_is_named_in_the_builder():
    """`if project == "..."` no core genérico é dívida, não atalho."""
    import ast
    import inspect

    from app.modules.risk_intake import builder as modulo

    arvore = ast.parse(inspect.getsource(modulo))
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            no.body = [
                item
                for item in no.body
                if not (
                    isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant)
                )
            ]
    codigo = ast.unparse(arvore).lower()
    for nome in ("pedrocore", "veltrix", "finguard", "structa", "elyra"):
        assert nome not in codigo


def test_registries_are_declarations_not_branches():
    """Projeto e executor novos entram por declaração, sem tocar em código."""
    assert project_surface("pedrocore") is not None
    assert project_surface("projeto-novo") is None
    assert executor_profile("claude-code") is not None
    assert executor_profile("executor-novo") is None
    assert set(EXECUTOR_PROFILES) >= {"claude-code", "codex", "generic-agent", "manual"}
    assert "pedrocore" in PROJECT_SURFACES


def test_the_builder_works_without_any_ai():
    """O Risk Console precisa continuar funcional sem provider."""
    proposta = _build("Atualize o Risk Console e rode os testes.")
    assert proposta.fields
    assert proposta.ai_was_authority is False


def test_an_executor_profile_informs_capability_not_authorisation():
    perfil = executor_profile("claude-code")
    assert perfil.supports(TechnicalCapability.GIT_PUSH)
    # Mesmo suportando, a permissao so sai da interseccao.
    proposta = _build("Não faça push.", executor="claude-code")
    assert _permission(proposta, TechnicalCapability.GIT_PUSH).effective is (
        EffectivePermission.FORBIDDEN
    )


# ===========================================================================
# TUI: revisão, confirmação e invalidação
# ===========================================================================


def _drive(prompt: str, check, size=(140, 45)):
    from app.modules.risk_console.app import RiskConsoleApp

    async def cenario():
        from textual.widgets import Button, TextArea

        app = RiskConsoleApp()
        async with app.run_test(size=size) as pilot:
            app.query_one("#prompt", TextArea).text = prompt
            await pilot.pause()
            app.query_one("#analisar", Button).press()
            await pilot.pause()
            await pilot.pause()
            return await check(app, pilot)

    return asyncio.run(cenario())


def test_analysing_opens_the_review_step_before_any_result():
    async def check(app, _pilot):
        assert app.query_one("#painel-revisao").display is True
        assert app.result is None, "a análise rodou sem confirmação humana"
        return True

    assert _drive("Atualize o Risk Console.", check)


def test_the_review_panel_explains_what_confirmation_means():
    async def check(app, _pilot):
        texto = str(app.query_one("#revisao-texto").content)
        assert "autoriza somente a análise de risco" in texto
        assert "nenhuma operação será executada" in texto
        return True

    assert _drive("Atualize o Risk Console.", check)


def test_the_review_panel_groups_by_origin():
    async def check(app, _pilot):
        texto = str(app.query_one("#revisao-texto").content)
        assert "INFERIDO" in texto
        assert "POLICY" in texto
        assert "requer(em) revisão" in texto
        return True

    assert _drive("Atualize o Risk Console e rode os testes.", check)


def test_confirming_runs_the_analysis():
    async def check(app, pilot):
        from textual.widgets import Button

        app.query_one("#revisao-confirmar", Button).press()
        await pilot.pause()
        await pilot.pause()
        assert app.result is not None
        assert app.query_one("#painel-revisao").display is False
        return True

    assert _drive("Atualize o Risk Console.", check)


def test_cancelling_discards_the_proposal_without_analysing():
    async def check(app, pilot):
        from textual.widgets import Button

        app.query_one("#revisao-cancelar", Button).press()
        await pilot.pause()
        assert app.result is None
        assert app.query_one("#painel-revisao").display is False
        assert "descartada" in str(app.query_one("#mensagem").content)
        return True

    assert _drive("Atualize o Risk Console.", check)


def test_reviewing_details_opens_the_advanced_settings():
    async def check(app, pilot):
        from textual.widgets import Button, Collapsible

        app.query_one("#revisao-detalhes", Button).press()
        await pilot.pause()
        assert app.query_one("#avancadas", Collapsible).collapsed is False
        return True

    assert _drive("Atualize o Risk Console.", check)


def test_a_manual_edit_takes_precedence_over_the_proposal():
    """Editar um campo o torna declarado, e a inferência não o sobrescreve."""
    entrada = _entry(
        "Atualize o Risk Console.", targets=["module:escolhido-a-mao"]
    )
    aplicada = apply(entrada, propose(entrada))
    assert aplicada.targets == ["module:escolhido-a-mao"]


def test_editing_after_an_analysis_still_invalidates_the_binding():
    """A garantia anterior não pode regredir com o fluxo novo."""
    from app.modules.risk_console.app import RiskConsoleApp

    async def cenario():
        from textual.widgets import Button, TextArea

        app = RiskConsoleApp()
        async with app.run_test(size=(140, 45)) as pilot:
            app.query_one("#prompt", TextArea).text = "Atualize o Risk Console."
            await pilot.pause()
            app.query_one("#analisar", Button).press()
            await pilot.pause()
            await pilot.pause()
            app.query_one("#revisao-confirmar", Button).press()
            await pilot.pause()
            await pilot.pause()
            antes = app.query_one("#acao-copiar", Button).disabled

            app.query_one("#prompt", TextArea).text = "Outro pedido diferente."
            await pilot.pause()
            return antes, app.query_one("#acao-copiar", Button).disabled

    _antes, depois = asyncio.run(cenario())
    assert depois is True, "edição depois da análise precisa invalidar a aprovação"


def test_an_empty_prompt_is_refused_before_any_proposal():
    async def check(app, _pilot):
        assert app.query_one("#painel-revisao").display is False
        assert "Prompt vazio" in str(app.query_one("#mensagem").content)
        return True

    assert _drive("   ", check)

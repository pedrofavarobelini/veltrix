"""Duas inconsistências semânticas encontradas na homologação do fluxo completo.

BUG 1 — confirmação virava declaração
-------------------------------------

Na revisão o sistema mostrava corretamente `0 declarados · 6 inferidos ·
2 políticas`. Depois de `CONFIRMAR E ANALISAR`, o painel `CONTEXTO` passava a
mostrar os mesmos valores como **DECLARADOS**.

Clicar "confirmar" não significa que o usuário declarou o fato. A causa era
`context_provenance` classificar todo campo não vazio como `DECLARED` — ela
via "tem valor" e concluía "foi digitado", sem nenhuma memória de origem.

BUG 2 — executar um teste virava autorização para alterá-lo
-----------------------------------------------------------

    "Atualize apenas o Risk Console, rode os testes relacionados..."

produzia `module:testes` no escopo de **mutação**. Executar um teste é
verificação, não alteração — e escopo de mutação é autorização.

O invariante
------------

    origem  !=  revisão
    executar um alvo  !=  poder alterá-lo
"""

from __future__ import annotations

import asyncio

import pytest

from app.modules.retrieval.schemas import RetrievalResponse
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_console.analysis import analyze
from app.modules.risk_console.auto_context import apply, propose
from app.modules.risk_console.domain import (
    ConsoleRequestInput,
    Provenance,
    confirmed_fields,
    context_provenance,
)
from app.modules.risk_console.render import render_context_panel
from app.modules.risk_intake.builder import _classify_areas
from app.modules.risk_intake.capabilities import project_surface
from app.modules.risk_intake.schemas import ContextOrigin

PROMPT = (
    "Atualize apenas o Risk Console, rode os testes relacionados e não faça push."
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


def _entry(prompt: str = PROMPT, **overrides) -> ConsoleRequestInput:
    valores = dict(
        project_id="pedrocore",
        environment_label="Desenvolvimento",
        executor_label="Claude Code",
        prompt=prompt,
    )
    valores.update(overrides)
    return ConsoleRequestInput(**valores)


def _confirmed(prompt: str = PROMPT, **overrides) -> ConsoleRequestInput:
    entrada = _entry(prompt, **overrides)
    return apply(entrada, propose(entrada))


# ===========================================================================
# BUG 1 — a origem sobrevive à confirmação
# ===========================================================================


def test_before_confirmation_nothing_is_declared():
    """O estado que a revisão mostrava, e que estava certo."""
    proposta = propose(_entry())
    assert proposta.declared_count == 0
    assert proposta.inferred_count > 0
    assert proposta.policy_count > 0


def test_confirming_never_turns_an_inference_into_a_declaration():
    """O bug, em uma asserção."""
    origem = context_provenance(_confirmed())
    for campo in ("operation", "targets", "allowed_scope", "required_tests"):
        assert origem[campo] is not Provenance.DECLARED, (
            f"{campo} virou DECLARED só por ter sido confirmado"
        )


def test_an_inferred_field_stays_inferred_after_confirmation():
    origem = context_provenance(_confirmed())
    assert origem["operation"] is Provenance.INFERRED
    assert origem["targets"] is Provenance.INFERRED
    assert origem["allowed_scope"] is Provenance.INFERRED


def test_a_policy_derived_field_stays_policy_derived():
    """"A regra disse" não pode virar "você disse"."""
    assert context_provenance(_confirmed())["permissions"] is (
        Provenance.POLICY_DERIVED
    )


def test_confirmation_is_recorded_as_separate_metadata():
    """Preferência arquitetural: origem de um lado, revisão do outro."""
    aplicada = _confirmed()
    confirmados = confirmed_fields(aplicada)
    assert "operation" in confirmados
    assert "targets" in confirmados
    # E a origem continua sendo a origem.
    assert aplicada.resolved_origins["operation"] == ContextOrigin.INFERRED.value


def test_only_something_actually_typed_is_declared():
    """A definição de DECLARED, testada diretamente."""
    aplicada = _confirmed(permissions=["write:risk_console"])
    origem = context_provenance(aplicada)
    assert origem["permissions"] is Provenance.DECLARED
    assert origem["targets"] is Provenance.INFERRED


def test_a_hand_written_field_survives_the_proposal_as_declared():
    entrada = _entry(targets=["module:escolhido-a-mao"])
    aplicada = apply(entrada, propose(entrada))
    assert context_provenance(aplicada)["targets"] is Provenance.DECLARED
    assert aplicada.targets == ["module:escolhido-a-mao"]


def test_the_context_panel_shows_inferred_with_a_confirmation_mark():
    painel = render_context_panel(analyze(_confirmed()))
    assert "inferido ✓" in painel
    assert "revisado(s) e confirmado(s)" in painel


def test_the_context_panel_still_reports_zero_declared_after_confirming():
    """A contagem da revisão e a do painel precisam concordar."""
    assert "0 campo(s) declarado(s)" in render_context_panel(analyze(_confirmed()))


def test_the_analysis_result_carries_the_confirmation_set():
    resultado = analyze(_confirmed())
    assert "operation" in resultado.confirmed
    assert resultado.provenance["operation"] is Provenance.INFERRED


def test_an_unconfirmed_entry_carries_no_confirmation():
    resultado = analyze(_entry(permissions=["write:x"], allowed_scope=["module:x"]))
    assert resultado.confirmed == frozenset()


# ===========================================================================
# BUG 2 — alvo de mutação × alvo de verificação
# ===========================================================================


def _areas(prompt: str):
    return _classify_areas(prompt, project_surface("pedrocore").areas)


def test_running_tests_does_not_make_tests_a_mutation_target():
    """O caso exato da homologação."""
    mutacao, verificacao = _areas(PROMPT)
    assert mutacao == ["risk_console"]
    assert "testes" in verificacao
    assert "testes" not in mutacao


def test_the_mutation_scope_excludes_the_verification_target():
    """Escopo de mutação é autorização: executar não amplia o que se pode alterar."""
    aplicada = _confirmed()
    assert aplicada.targets == ["risk_console"]
    assert aplicada.allowed_scope == ["module:risk_console"]
    assert "module:testes" not in aplicada.allowed_scope


def test_the_tests_become_the_required_verification():
    aplicada = _confirmed()
    assert aplicada.required_tests == ["testes"]


def test_explicitly_changing_the_tests_makes_them_a_mutation_target():
    """"altere os testes" — aí sim testes é alvo de alteração."""
    mutacao, _verificacao = _areas("Altere os testes do Risk Console.")
    assert "testes" in mutacao


def test_a_verification_only_prompt_has_no_mutation_target():
    mutacao, verificacao = _areas("Rode os testes.")
    assert mutacao == []
    assert "testes" in verificacao


def test_the_nearest_preceding_verb_decides_not_the_whole_sentence():
    """A vírgula não separa orações aqui; os verbos governam trechos."""
    mutacao, verificacao = _areas("Atualize a documentação e rode os testes.")
    assert "documentação" in mutacao
    assert "testes" in verificacao


def test_an_area_without_a_preceding_verb_is_never_a_mutation_target():
    """Assumir mutação por omissão seria ampliar escopo por omissão."""
    mutacao, _verificacao = _areas("Risk Console")
    assert mutacao == []


def test_a_forbidden_clause_contributes_no_target_at_all():
    """A correção de negação não pode regredir com esta."""
    mutacao, verificacao = _areas(
        "Atualize a documentação. Não altere o risk engine."
    )
    assert "risk_engine" not in mutacao
    assert "risk_engine" not in verificacao


# ===========================================================================
# Segurança: confirmar não autoriza
# ===========================================================================


def test_confirmation_still_authorises_nothing():
    proposta = propose(_entry())
    assert proposta.authorizes_execution is False
    assert proposta.replaces_risk_gate is False


def test_a_confirmed_field_is_not_a_granted_permission():
    """USER_CONFIRMED não é permission granted."""
    from app.modules.risk_intake.capabilities import TechnicalCapability
    from app.modules.risk_intake.schemas import EffectivePermission

    entrada = _entry("Atualize o Risk Console e faça push.", executor_label="Agente genérico")
    proposta = propose(entrada)
    push = proposta.permission(TechnicalCapability.GIT_PUSH)
    assert push.requested is True
    assert push.effective is not EffectivePermission.GRANTED

    aplicada = apply(entrada, proposta)
    assert not any("push" in item for item in aplicada.permissions)


def test_the_gate_still_decides_after_confirmation():
    from app.modules.risk_engine.execution_contract_schemas import RiskGate

    resultado = analyze(_confirmed())
    assert resultado.gate in set(RiskGate)
    assert resultado.gate_reasons


def test_confirming_does_not_execute_the_target_operation():
    resultado = analyze(_confirmed())
    assert resultado.analysis.target_operation_executed is False
    assert resultado.analysis.provider_called is False


# ===========================================================================
# TUI — o fluxo completo
# ===========================================================================


def test_the_full_flow_preserves_provenance_through_the_ui():
    """Da revisão até o painel de contexto, sem virar declaração."""
    from app.modules.risk_console.app import RiskConsoleApp

    async def cenario():
        from textual.widgets import Button, TextArea

        app = RiskConsoleApp()
        async with app.run_test(size=(140, 45)) as pilot:
            app.query_one("#prompt", TextArea).text = PROMPT
            await pilot.pause()
            app.query_one("#analisar", Button).press()
            await pilot.pause()
            await pilot.pause()
            revisao = str(app.query_one("#revisao-texto").content)

            app.query_one("#revisao-confirmar", Button).press()
            await pilot.pause()
            await pilot.pause()
            return revisao, str(app.query_one("#contexto-texto").content), app.result

    revisao, contexto, resultado = asyncio.run(cenario())

    assert "0 declarado(s)" in revisao
    assert "inferido ✓" in contexto
    assert "0 campo(s) declarado(s)" in contexto
    assert resultado.provenance["targets"] is Provenance.INFERRED
    assert resultado.request.requested_operation.targets == ["risk_console"]

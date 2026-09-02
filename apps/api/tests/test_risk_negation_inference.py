"""Polaridade de menção — o segundo bug encontrado na homologação humana.

O que aconteceu
---------------

O prompt dizia, textualmente:

    "Não altere Risk Engine, contratos, schemas, migrations, banco de dados,
     autenticação ou outros módulos. Não faça push. Não execute comandos
     destrutivos."

E o Risk Engine respondia:

    Intenção = MIGRAR BANCO
    Dados = CRÍTICO · Migração = CRÍTICO
    cenário de falha de migração

A frase dizia o contrário do que o motor entendeu. A causa era casamento de
substring sem contexto (`term in texto`), em dois lugares: a inferência de
operação e as regras determinísticas.

O invariante que estes casos protegem
-------------------------------------

    menção          !=  intenção
    menção negada   !=  operação solicitada
    alvo proibido   !=  alvo afetado

E o contrário também precisa continuar valendo: **detecção positiva real não
pode enfraquecer**. Metade destes casos existe para isso.
"""

from __future__ import annotations

import pytest

from app.modules.retrieval.schemas import RetrievalResponse
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_console.analysis import analyze
from app.modules.risk_console.domain import ConsoleRequestInput
from app.modules.risk_engine.analyzers import (
    forbidden_operation_terms,
    infer_operation_kind,
)
from app.modules.risk_engine.polarity import (
    AFFIRMATIVE,
    Polarity,
    affirmative_text,
    forbidden_text,
    mention_polarity,
    split_clauses,
)
from app.modules.risk_engine.pre_execution_schemas import RiskDimensionName
from app.modules.risk_engine.schemas import OperationKind, RiskSeverity

# O prompt exato da homologação.
PROMPT_HOMOLOGACAO = (
    "Faça uma alteração apenas no Risk Console. "
    "Não altere Risk Engine, contratos, schemas, migrations, banco de dados, "
    "autenticação ou outros módulos. "
    "Execute os testes. "
    "Não faça push. "
    "Não execute comandos destrutivos."
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


def _analyse(prompt: str, **overrides):
    valores = dict(
        project_id="pedrocore",
        environment_label="Desenvolvimento",
        executor_label="Claude Code",
        prompt=prompt,
    )
    valores.update(overrides)
    return analyze(ConsoleRequestInput(**valores))


# ===========================================================================
# 1. O caso exato da homologação
# ===========================================================================


def test_the_homologation_prompt_is_not_read_as_a_migration():
    """O bug relatado, em uma asserção."""
    resultado = _analyse(PROMPT_HOMOLOGACAO)
    assert resultado.analysis.foundation.intent.operation is not OperationKind.MIGRATE


def test_the_real_operation_survives_the_fix():
    """Corrigir não pode virar cegueira: o pedido pede executar testes."""
    resultado = _analyse(PROMPT_HOMOLOGACAO)
    assert resultado.analysis.foundation.intent.operation in {
        OperationKind.WRITE,
        OperationKind.EXECUTE,
    }


def test_data_risk_is_not_critical_because_of_a_negated_sentence():
    resultado = _analyse(PROMPT_HOMOLOGACAO)
    por_dimensao = {i.dimension: i.severity for i in resultado.analysis.risk_dimensions}
    assert por_dimensao[RiskDimensionName.DATA] is RiskSeverity.INFO


def test_migration_risk_is_not_critical_because_of_a_negated_sentence():
    resultado = _analyse(PROMPT_HOMOLOGACAO)
    por_dimensao = {i.dimension: i.severity for i in resultado.analysis.risk_dimensions}
    assert por_dimensao[RiskDimensionName.MIGRATION] is RiskSeverity.INFO


def test_no_migration_or_data_rule_fires_from_a_prohibition():
    resultado = _analyse(PROMPT_HOMOLOGACAO)
    codigos = {i.reason_code for i in resultado.analysis.deterministic_rules}
    for proibido in ("DATABASE_MIGRATION", "SCHEMA_CHANGE", "AUTH_AUTHZ_CHANGE"):
        assert proibido not in codigos


def test_no_migration_scenario_appears_from_a_prohibition():
    resultado = _analyse(PROMPT_HOMOLOGACAO)
    nomes = {i.scenario for i in resultado.analysis.simulations}
    assert "migration_failure" not in nomes
    assert "data_corruption" not in nomes


def test_the_blast_radius_is_not_inflated_by_a_prohibition():
    resultado = _analyse(PROMPT_HOMOLOGACAO)
    assert resultado.analysis.blast_radius.magnitude is RiskSeverity.INFO


def test_the_prohibition_is_recorded_instead_of_vanishing():
    """Some-la seria esconder o que o pedido disse."""
    resultado = _analyse(PROMPT_HOMOLOGACAO)
    assert "migration" in resultado.analysis.foundation.intent.forbidden_mentions


def test_the_context_panel_still_reports_no_declared_advanced_field():
    """A correção anterior não pode regredir com esta."""
    from app.modules.risk_console.render import render_context_panel

    painel = render_context_panel(_analyse(PROMPT_HOMOLOGACAO))
    assert "0 campo(s) declarado(s)" in painel
    assert "Proibido pelo prompt" in painel


# ===========================================================================
# 2. Exemplos obrigatórios do enunciado
# ===========================================================================


@pytest.mark.parametrize(
    "prompt,esperado",
    [
        ("execute uma migration", OperationKind.MIGRATE),
        ("crie uma migration para a tabela de contas", OperationKind.MIGRATE),
        ("faça o deploy para produção", OperationKind.DEPLOY),
        ("leia o relatório e audite os totais", OperationKind.READ),
    ],
)
def test_an_affirmative_request_is_still_detected(prompt, esperado):
    """Detecção positiva real não pode enfraquecer."""
    assert infer_operation_kind(prompt) is esperado


@pytest.mark.parametrize(
    "prompt",
    [
        "não execute migration",
        "não crie migration",
        "nunca execute uma migration",
        "jamais rode uma migration",
        "é proibido executar migration",
        "evite executar migration",
        "sem executar migration",
    ],
)
def test_a_forbidden_migration_is_never_a_requested_migration(prompt):
    assert infer_operation_kind(prompt) is not OperationKind.MIGRATE


def test_do_not_touch_the_database_is_a_constraint_not_an_operation():
    resultado = _analyse("não altere o banco de dados")
    assert resultado.analysis.foundation.intent.operation is not OperationKind.MIGRATE
    assert resultado.request.context.database is None


def test_do_not_push_is_not_a_requested_effect():
    assert infer_operation_kind("não faça push") is OperationKind.UNKNOWN


def test_do_not_run_destructive_commands_is_not_a_requested_execution():
    assert infer_operation_kind("não execute comandos destrutivos") is (
        OperationKind.UNKNOWN
    )


def test_write_here_but_not_in_the_database():
    """O contraste separa as duas polaridades na mesma frase."""
    prompt = "altere o módulo de relatórios, mas não toque no banco"
    assert infer_operation_kind(prompt) is OperationKind.WRITE
    assert "banco" in forbidden_text(prompt).lower()


# ===========================================================================
# 3. Controles positivos exigidos
# ===========================================================================


def test_an_explicit_schema_change_still_reports_migration_risk():
    """"Altere o schema do banco, crie e execute uma migration." """
    resultado = _analyse(
        "Altere o schema do banco, crie e execute uma migration.",
        permissions=["migrate:core"],
        database="core",
    )
    codigos = {i.reason_code for i in resultado.analysis.deterministic_rules}
    assert "DATABASE_MIGRATION" in codigos
    assert "SCHEMA_CHANGE" in codigos
    por_dimensao = {i.dimension: i.severity for i in resultado.analysis.risk_dimensions}
    assert por_dimensao[RiskDimensionName.MIGRATION] is not RiskSeverity.INFO


def test_do_not_change_the_database_update_only_the_docs():
    """"Não altere o banco. Atualize apenas a documentação." """
    resultado = _analyse("Não altere o banco. Atualize apenas a documentação.")
    codigos = {i.reason_code for i in resultado.analysis.deterministic_rules}
    assert "DATABASE_MIGRATION" not in codigos
    assert resultado.request.context.database is None


def test_do_not_push_but_do_commit():
    """"Não faça push; faça commit." """
    prompt = "Não faça push; faça commit."
    afirmativo = affirmative_text(prompt).lower()
    proibido = forbidden_text(prompt).lower()
    assert "commit" in afirmativo
    assert "push" in proibido
    assert "push" not in afirmativo


def test_do_not_delete_only_read():
    """"Não delete arquivos; apenas leia." """
    prompt = "Não delete arquivos; apenas leia."
    assert infer_operation_kind(prompt) is OperationKind.READ
    resultado = _analyse(prompt, permissions=["read:docs"])
    codigos = {i.reason_code for i in resultado.analysis.deterministic_rules}
    assert "DELETE_OPERATION" not in codigos


def test_an_explicit_delete_is_still_detected():
    resultado = _analyse("Delete os arquivos temporários do módulo de relatórios.")
    codigos = {i.reason_code for i in resultado.analysis.deterministic_rules}
    assert "DELETE_OPERATION" in codigos


def test_an_explicit_auth_change_is_still_detected():
    resultado = _analyse("Altere a política de authorization do módulo de acesso.")
    codigos = {i.reason_code for i in resultado.analysis.deterministic_rules}
    assert "AUTH_AUTHZ_CHANGE" in codigos


# ===========================================================================
# 4. O modelo de polaridade
# ===========================================================================


def test_the_polarity_model_has_the_five_declared_states():
    assert {item.value for item in Polarity} == {
        "REQUESTED",
        "ALLOWED",
        "FORBIDDEN",
        "NEGATED",
        "UNKNOWN",
    }


def test_only_requested_and_allowed_count_as_affirmative():
    """Proibido e negado nunca alimentam inferência."""
    assert AFFIRMATIVE == {Polarity.REQUESTED, Polarity.ALLOWED}
    assert Polarity.FORBIDDEN not in AFFIRMATIVE
    assert Polarity.NEGATED not in AFFIRMATIVE


@pytest.mark.parametrize(
    "prompt,esperado",
    [
        ("execute a migration", Polarity.REQUESTED),
        ("não execute a migration", Polarity.FORBIDDEN),
        ("nunca execute a migration", Polarity.FORBIDDEN),
        ("pode executar a migration se necessário", Polarity.ALLOWED),
    ],
)
def test_clause_polarity_is_classified_by_its_marker(prompt, esperado):
    clausulas = split_clauses(prompt)
    assert len(clausulas) == 1
    assert clausulas[0].polarity is esperado


def test_a_term_mentioned_in_both_polarities_counts_as_requested():
    """Pedir algo e depois restringi-lo continua sendo pedir."""
    prompt = "execute a migration; não execute a migration em produção"
    assert mention_polarity(prompt, "migration") is Polarity.REQUESTED


def test_an_unmentioned_term_is_unknown():
    assert mention_polarity("altere o layout", "migration") is Polarity.UNKNOWN


def test_an_empty_prompt_yields_no_clauses():
    assert split_clauses("") == ()
    assert affirmative_text("   ") == ""


def test_a_prompt_with_only_prohibitions_has_no_affirmative_text():
    assert affirmative_text("Não faça push. Não execute nada.") == ""


def test_forbidden_operation_terms_lists_what_was_prohibited():
    termos = forbidden_operation_terms(PROMPT_HOMOLOGACAO)
    assert "migration" in termos
    # O que foi PEDIDO nao entra na lista de proibicoes.
    assert "execute" not in termos


def test_structured_declarations_are_not_filtered_by_polarity():
    """Alvo declarado é afirmação por construção; negação não se aplica a ele.

    Se o consumidor declara `module:auth` como alvo, ele está pedindo — e
    filtrar isso por polaridade faria uma declaração explícita ser ignorada.
    """
    resultado = _analyse(
        "Ajuste o módulo indicado.",
        targets=["module:auth"],
        permissions=["write:auth"],
        allowed_scope=["module:auth"],
    )
    codigos = {i.reason_code for i in resultado.analysis.deterministic_rules}
    assert "AUTH_AUTHZ_CHANGE" in codigos

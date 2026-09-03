"""Conflito falso de escopo: o mesmo recurso escrito de duas formas.

O que a homologação mostrou
---------------------------

O Auto Context propunha, para o mesmo módulo:

    alvo             risk_console
    escopo permitido module:risk_console

e o Risk Engine respondia `SCOPE_UNBOUNDED` — "um ou mais alvos não pertencem
ao escopo permitido conhecido" — com risco de escopo ALTO.

Nada estava fora do escopo. `"risk_console" != "module:risk_console"` como
string, e a comparação era de strings cruas.

O invariante
------------

    mesmo recurso semântico  →  mesma identidade canônica
    recursos diferentes      →  continuam diferentes

A segunda linha é a que importa mais. Canonicalizar não pode virar um jeito de
fazer um alvo casar com um escopo que não o contém: `module:risk_console` e
`module:auth` seguem sendo conflito real, e `file:billing/service.py` NÃO passa
a pertencer a `module:billing`.

Sobre o que estes testes afirmam
--------------------------------

Eles afirmam que o desencontro de GRAFIA sumiu. Nenhum deles afirma que o gate
é PASS: o gate continua decidindo pelos fatos do pedido, e o CASO F verifica
apenas que `SCOPE_UNBOUNDED` não aparece — qualquer que seja o gate.
"""

from __future__ import annotations

import pytest

from app.modules.retrieval.schemas import RetrievalResponse
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_console.analysis import analyze
from app.modules.risk_console.auto_context import apply, propose
from app.modules.risk_console.domain import ConsoleRequestInput
from app.modules.risk_engine.analyzers import ScopeAnalyzer
from app.modules.risk_engine.scope import canonical_scope, canonical_scopes
from app.modules.risk_engine.schemas import (
    ExecutionIntent,
    OperationKind,
    ResolvedContext,
)

PROMPT_HOMOLOGACAO = (
    "Atualize apenas o Risk Console, rode os testes relacionados e não faça push. "
    "Não altere banco de dados, migrations, autenticação, contratos, schemas ou "
    "outros módulos. Não execute comandos destrutivos."
)


@pytest.fixture(autouse=True)
def quiet_retrieval(monkeypatch):
    monkeypatch.setattr(
        retrieval_service,
        "retrieve",
        lambda query, **_: RetrievalResponse(query_id=query.query_id, project_id=query.project_id),
    )


def _scope(targets: list[str], allowed: list[str], forbidden: list[str] | None = None):
    intent = ExecutionIntent(
        operation=OperationKind.WRITE,
        inferred_operation=OperationKind.WRITE,
        targets=targets,
        mutating=True,
        destructive=False,
        external_effects=False,
        explicit_intent=True,
        intent_consistent=True,
    )
    context = ResolvedContext(
        project_id="pedrocore",
        environment="dev",
        agent_id="claude-code",
        allowed_scope=allowed,
        forbidden_scope=forbidden or [],
    )
    return ScopeAnalyzer().analyze(intent, context)


# ===========================================================================
# A identidade canônica, isolada
# ===========================================================================


def test_a_bare_name_takes_the_default_kind():
    assert canonical_scope("risk_console") == "module:risk_console"


def test_an_already_typed_name_is_left_alone():
    assert canonical_scope("module:risk_console") == "module:risk_console"
    assert canonical_scope("file:billing/service.py") == "file:billing/service.py"


def test_canonicalisation_is_idempotent():
    """Aplicar duas vezes não pode produzir `module:module:x`."""
    uma = canonical_scope("risk_console")
    assert canonical_scope(uma) == uma


def test_the_two_spellings_collapse_to_one_entry():
    assert canonical_scopes(["risk_console", "module:risk_console"]) == ["module:risk_console"]


def test_an_unknown_prefix_is_a_name_not_a_kind():
    """`urgente:agora` não declara tipo; é um nome que contém dois-pontos."""
    assert canonical_scope("urgente:agora") == "module:urgente:agora"


# ===========================================================================
# CASO A — o caso da homologação, no comparador
# ===========================================================================


def test_case_a_bare_target_belongs_to_the_typed_scope():
    analise = _scope(["risk_console"], ["module:risk_console"])
    assert analise.targets_in_scope == ["module:risk_console"]
    assert analise.targets_outside_scope == []
    assert analise.bounded is True


# ===========================================================================
# CASO B — as duas pontas já canônicas
# ===========================================================================


def test_case_b_a_typed_target_belongs_to_the_same_typed_scope():
    analise = _scope(["module:risk_console"], ["module:risk_console"])
    assert analise.targets_in_scope == ["module:risk_console"]
    assert analise.bounded is True


# ===========================================================================
# CASO C — módulo diferente continua sendo conflito
# ===========================================================================


def test_case_c_a_different_module_does_not_belong():
    analise = _scope(["risk_console"], ["module:auth"])
    assert analise.targets_in_scope == []
    assert analise.targets_outside_scope == ["module:risk_console"]
    assert analise.bounded is False


# ===========================================================================
# CASO D — outro recurso continua fora
# ===========================================================================


def test_case_d_an_unrelated_target_does_not_belong():
    analise = _scope(["database"], ["module:risk_console"])
    assert analise.targets_outside_scope == ["module:database"]
    assert analise.bounded is False


# ===========================================================================
# CASO E — proibição continua valendo através da grafia
# ===========================================================================


def test_case_e_a_forbidden_resource_is_caught_in_either_spelling():
    """Escrever o alvo sem o prefixo não é rota de fuga da proibição."""
    analise = _scope(["auth"], ["module:auth"], forbidden=["module:auth"])
    assert analise.forbidden_targets == ["module:auth"]
    assert analise.bounded is False


def test_case_e_the_conflict_survives_the_mirror_spelling():
    analise = _scope(["module:auth"], ["module:auth"], forbidden=["auth"])
    assert analise.forbidden_targets == ["module:auth"]


# ===========================================================================
# CASO F — o prompt da homologação, fim a fim
# ===========================================================================


def _homologacao():
    entrada = ConsoleRequestInput(
        project_id="pedrocore",
        environment_label="Desenvolvimento",
        executor_label="Claude Code",
        prompt=PROMPT_HOMOLOGACAO,
    )
    return apply(entrada, propose(entrada))


def test_case_f_the_producer_emits_one_spelling_for_one_resource():
    """A origem do defeito: alvo cru contra escopo prefixado."""
    aplicada = _homologacao()
    assert aplicada.targets == ["module:risk_console"]
    assert aplicada.allowed_scope == ["module:risk_console"]


def test_case_f_the_target_is_inside_the_proposed_scope():
    escopo = analyze(_homologacao()).analysis.foundation.scope
    assert escopo.targets_outside_scope == []
    assert escopo.unknown_targets == []


def test_case_f_no_false_scope_finding_is_emitted():
    """A única afirmação sobre o resultado: o achado FALSO sumiu.

    Nada aqui diz que o gate é PASS. O gate segue decidindo pelos outros fatos
    do pedido, e este teste continua válido se ele mudar.
    """
    codigos = {item.reason_code for item in analyze(_homologacao()).analysis.findings}
    assert "SCOPE_UNBOUNDED" not in codigos


def test_case_f_scope_risk_is_no_longer_driven_by_a_spelling_mismatch():
    resultado = analyze(_homologacao())
    escopo = next(
        item for item in resultado.analysis.risk_dimensions if item.dimension.value == "scope_risk"
    )
    assert escopo.severity.value != "HIGH"


# ===========================================================================
# O limite: canonicalizar não pode afrouxar a verificação
# ===========================================================================


def test_a_file_does_not_become_a_member_of_a_module():
    """Hierarquia seria alargamento de escopo, e alargar escopo é afrouxar."""
    analise = _scope(["file:billing/service.py"], ["module:billing"])
    assert analise.targets_outside_scope == ["file:billing/service.py"]
    assert analise.bounded is False


def test_a_module_does_not_absorb_a_similarly_named_one():
    analise = _scope(["risk_console_legacy"], ["module:risk_console"])
    assert analise.bounded is False


def test_an_empty_allowed_scope_still_leaves_the_target_unknown():
    """Sem escopo declarado não há escopo satisfeito."""
    analise = _scope(["risk_console"], [])
    assert analise.unknown_targets == ["module:risk_console"]
    assert analise.bounded is False

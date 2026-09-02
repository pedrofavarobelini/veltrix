"""E2 — Policy Engine V1.

O foco e o caminho desonesto e o caminho descuidado: consumidor tentando
liberar a si mesmo, atributo ausente virando permissao, ordem de regra
afrouxando decisao, e regra quebrada abrindo passagem.
"""

from __future__ import annotations

import pytest

from app.modules.policy_engine.rules import RULES, rules_for
from app.modules.policy_engine.schemas import (
    PolicyDecision,
    PolicyDomain,
    PolicyEffect,
    PolicyRequest,
    decision_for,
)
from app.modules.policy_engine.service import policy_engine_service

BASE = dict(project_id="pedrocore", environment="development", producer="pedrocore-ci")


def _request(**overrides) -> PolicyRequest:
    values = {"domain": PolicyDomain.RUNTIME, "action": "analyze", **BASE}
    values.update(overrides)
    return PolicyRequest(**values)


# --- decisao ---------------------------------------------------------------


def test_a_clean_request_is_allowed_with_a_reason():
    """Permitir sem dizer por quê não é auditável."""
    result = policy_engine_service.evaluate(_request())
    assert result.decision is PolicyDecision.ALLOW
    assert result.reason_codes == ["POLICY_REQUIREMENTS_SATISFIED"]
    assert result.allowed is True


def test_the_most_restrictive_effect_always_wins():
    """Um `deny` não é apagado por um `allow` que venha depois."""
    assert decision_for([PolicyEffect.ALLOW, PolicyEffect.DENY]) is PolicyDecision.DENY
    assert decision_for([PolicyEffect.DENY, PolicyEffect.ALLOW]) is PolicyDecision.DENY
    assert (
        decision_for([PolicyEffect.CONDITION, PolicyEffect.REVIEW])
        is PolicyDecision.REVIEW_REQUIRED
    )


def test_the_order_of_the_rules_cannot_change_the_decision():
    """Política que dependesse da ordem seria política por sorteio."""
    efeitos = [PolicyEffect.ALLOW, PolicyEffect.CONDITION, PolicyEffect.DENY]
    assert decision_for(efeitos) is decision_for(list(reversed(efeitos)))


# --- fail-closed -----------------------------------------------------------


def test_an_unknown_environment_is_denied_not_assumed_to_be_development():
    result = policy_engine_service.evaluate(_request(environment="qualquer-coisa"))
    assert result.decision is PolicyDecision.DENY
    assert "PRODUCTION_REQUIRES_DECLARED_ENVIRONMENT" in result.reason_codes


@pytest.mark.parametrize("project", ["unknown", "shared_or_unknown"])
def test_an_unidentified_project_does_not_inherit_trust(project):
    result = policy_engine_service.evaluate(_request(project_id=project))
    assert result.decision is PolicyDecision.DENY
    assert "UNKNOWN_PROJECT_IS_NOT_TRUSTED" in result.reason_codes


def test_a_missing_attribute_counts_as_absent_never_as_yes():
    """Aprender exige consentimento declarado; silêncio não é consentimento."""
    result = policy_engine_service.evaluate(
        _request(domain=PolicyDomain.LEARNING, action="promote")
    )
    assert result.decision is PolicyDecision.DENY
    assert "TRAINING_REQUIRES_EXPLICIT_CONSENT" in result.reason_codes


def test_a_broken_rule_becomes_review_never_permission(monkeypatch):
    """Regra que explode não pode virar passagem livre.

    `PolicyRule` e frozen de proposito, entao a regra quebrada e CONSTRUIDA e
    injetada — o que tambem e mais fiel: e assim que uma regra defeituosa
    chegaria em producao.
    """
    import dataclasses

    from app.modules.policy_engine import service as modulo

    def explode(_request):
        raise RuntimeError("regra quebrada")

    quebrada = dataclasses.replace(RULES[0], matches=explode)
    monkeypatch.setattr(modulo, "rules_for", lambda _domain: (quebrada,))

    result = policy_engine_service.evaluate(_request())
    assert result.decision is not PolicyDecision.ALLOW
    assert "POLICY_RULE_EVALUATION_FAILED" in result.reason_codes


# --- invariantes da arquitetura -------------------------------------------


def test_automatic_collection_is_refused_as_an_executable_invariant():
    result = policy_engine_service.evaluate(
        _request(
            domain=PolicyDomain.LEARNING,
            action="collect",
            attributes={"automatic_collection": True, "training_consent": "true"},
        )
    )
    assert result.decision is PolicyDecision.DENY
    assert "AUTOMATIC_COLLECTION_IS_FORBIDDEN" in result.reason_codes


def test_the_core_never_accepts_delegated_execution():
    result = policy_engine_service.evaluate(
        _request(
            domain=PolicyDomain.EXECUTION,
            action="run",
            attributes={"requests_target_execution": True},
        )
    )
    assert result.decision is PolicyDecision.DENY
    assert "EXECUTION_IS_NEVER_DELEGATED" in result.reason_codes


def test_a_real_provider_call_requires_explicit_opt_in():
    negado = policy_engine_service.evaluate(
        _request(
            domain=PolicyDomain.PROVIDER,
            action="complete",
            attributes={"real_provider_call": True},
        )
    )
    assert negado.decision is PolicyDecision.DENY

    liberado = policy_engine_service.evaluate(
        _request(
            domain=PolicyDomain.PROVIDER,
            action="complete",
            attributes={"real_provider_call": True, "real_provider_opt_in": "true"},
        )
    )
    assert liberado.allowed


def test_a_raw_payload_is_allowed_only_under_a_stated_condition():
    result = policy_engine_service.evaluate(
        _request(attributes={"carries_raw_payload": True})
    )
    assert result.decision is PolicyDecision.ALLOW_WITH_CONDITIONS
    assert result.conditions == ["persistir apenas metadados sanitizados"]
    assert result.allowed is True


def test_production_mutation_needs_human_review():
    result = policy_engine_service.evaluate(
        _request(environment="production", attributes={"mutating": True})
    )
    assert result.decision is PolicyDecision.REVIEW_REQUIRED
    assert result.allowed is False


# --- autoridade ------------------------------------------------------------


def test_the_consumer_has_nowhere_to_declare_its_own_verdict():
    """A proteção é a ausência do campo, não só a varredura."""
    proibidos = {"decision", "allow", "allowed", "approved", "policy_version", "effect"}
    assert not (set(PolicyRequest.model_fields) & proibidos)


def test_extra_fields_are_refused_by_the_request_contract():
    with pytest.raises(Exception):
        PolicyRequest(domain=PolicyDomain.RUNTIME, action="a", decision="ALLOW", **BASE)


def test_no_rule_names_a_specific_project():
    """`if project == 'finguard'` no core genérico é dívida, não atalho."""
    import ast
    import inspect

    from app.modules.policy_engine import rules as modulo

    # Docstring e comentario CITAM o anti-padrao de proposito; o que nao pode
    # existir e o nome do projeto no codigo executavel.
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
    for nome in ("finguard", "structa", "elyra", "rivvo", "orlabyte", "replaydock"):
        assert nome not in codigo, f"regra cita o projeto {nome}"


# --- determinismo e auditoria ---------------------------------------------


def test_the_same_question_yields_the_same_policy_id():
    primeiro = policy_engine_service.evaluate(_request(attributes={"mutating": True}))
    segundo = policy_engine_service.evaluate(_request(attributes={"mutating": True}))
    assert primeiro.policy_id == segundo.policy_id
    assert primeiro.decision is segundo.decision


def test_a_different_question_yields_a_different_policy_id():
    primeiro = policy_engine_service.evaluate(_request())
    segundo = policy_engine_service.evaluate(_request(action="outra-acao"))
    assert primeiro.policy_id != segundo.policy_id


def test_every_evaluation_declares_no_provider_was_called():
    result = policy_engine_service.evaluate(_request())
    assert result.provider_called is False
    assert result.deterministic is True


def test_every_matched_rule_explains_itself_in_portuguese():
    result = policy_engine_service.evaluate(_request(environment="inexistente"))
    for item in result.matched_rules:
        assert item.explanation and item.explanation[0].isupper()
        assert item.rule_id and item.rule_version


def test_universal_rules_apply_to_every_domain():
    """Ação de learning em ambiente desconhecido continua em ambiente desconhecido."""
    for domain in PolicyDomain:
        ids = {rule.rule_id for rule in rules_for(domain)}
        assert "environment.declared" in ids
        assert "capability.unknown_project" in ids


def test_the_correlation_id_survives_the_evaluation():
    result = policy_engine_service.evaluate(_request(correlation_id="corr-123"))
    assert result.correlation_id == "corr-123"

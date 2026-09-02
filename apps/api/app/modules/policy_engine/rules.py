"""Regras transversais do Policy Engine, declaradas em um lugar so.

Cada regra e um dado, nao um `if` escondido: tem id, versao, dominio, efeito,
codigo de motivo e explicacao em portugues. Isso e o que permite responder
"por que isto foi negado" sem abrir o codigo.

Criterio para uma regra morar AQUI
----------------------------------

Ela precisa ser transversal — valer para mais de um dominio ou ser consultada
por mais de um chamador. Regra que pertence a um dominio so continua no
dominio: o gate do Risk decide risco, o circuito decide provider, e trazer
qualquer um dos dois para ca os tiraria do lugar onde sao testados a fundo.

Nenhuma regra cita projeto por nome
-----------------------------------

Nao ha `if project == "finguard"`. Onde a decisao depende do consumidor, ela
depende do que ele DECLARA no Capability Manifest — e um projeto novo passa a
ser atendido por declarar o que faz, sem tocar neste arquivo.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.modules.policy_engine.schemas import (
    PolicyDomain,
    PolicyEffect,
    PolicyRequest,
    PolicyRuleMatch,
)

RULE_VERSION = "1.0"

# --- codigos de motivo ----------------------------------------------------

PRODUCTION_REQUIRES_DECLARED_ENVIRONMENT = "PRODUCTION_REQUIRES_DECLARED_ENVIRONMENT"
UNKNOWN_PROJECT_IS_NOT_TRUSTED = "UNKNOWN_PROJECT_IS_NOT_TRUSTED"
CAPABILITY_NOT_DECLARED = "CAPABILITY_NOT_DECLARED"
EXECUTION_IS_NEVER_DELEGATED = "EXECUTION_IS_NEVER_DELEGATED"
AUTOMATIC_COLLECTION_IS_FORBIDDEN = "AUTOMATIC_COLLECTION_IS_FORBIDDEN"
TRAINING_REQUIRES_EXPLICIT_CONSENT = "TRAINING_REQUIRES_EXPLICIT_CONSENT"
RAW_PAYLOAD_IS_NOT_PERSISTED = "RAW_PAYLOAD_IS_NOT_PERSISTED"
PRODUCTION_MUTATION_NEEDS_REVIEW = "PRODUCTION_MUTATION_NEEDS_REVIEW"
REAL_PROVIDER_REQUIRES_OPT_IN = "REAL_PROVIDER_REQUIRES_OPT_IN"
POLICY_REQUIREMENTS_SATISFIED = "POLICY_REQUIREMENTS_SATISFIED"

_PRODUCTION = {"prod", "production", "producao", "produção"}
_KNOWN_ENVIRONMENTS = {"development", "dev", "test", "testing", "staging"} | _PRODUCTION

# `shared_or_unknown` e o namespace que uma credencial sem projeto recebe.
# Ele existe para nao mentir sobre identidade — e por isso nao pode carregar
# a confianca de um projeto de verdade.
_UNKNOWN_PROJECTS = {"unknown", "shared_or_unknown", ""}


@dataclass(frozen=True, slots=True)
class PolicyRule:
    """Regra declarativa. `matches` le apenas atributos declarados."""

    rule_id: str
    domain: PolicyDomain
    effect: PolicyEffect
    reason_code: str
    explanation: str
    matches: Callable[[PolicyRequest], bool]
    condition: str | None = None
    version: str = RULE_VERSION

    def evaluate(self, request: PolicyRequest) -> PolicyRuleMatch | None:
        if not self.matches(request):
            return None
        return PolicyRuleMatch(
            rule_id=self.rule_id,
            rule_version=self.version,
            domain=self.domain,
            effect=self.effect,
            reason_code=self.reason_code,
            explanation=self.explanation,
        )


def _flag(request: PolicyRequest, name: str) -> bool:
    """Atributo booleano declarado. Ausente conta como falso, nunca como sim."""
    return bool(request.attributes.get(name))


def _text(request: PolicyRequest, name: str) -> str:
    value = request.attributes.get(name)
    return str(value).strip().lower() if value is not None else ""


def _is_production(request: PolicyRequest) -> bool:
    return request.environment.strip().lower() in _PRODUCTION


RULES: tuple[PolicyRule, ...] = (
    # --- ambiente ---------------------------------------------------------
    PolicyRule(
        rule_id="environment.declared",
        domain=PolicyDomain.ENVIRONMENT,
        effect=PolicyEffect.DENY,
        reason_code=PRODUCTION_REQUIRES_DECLARED_ENVIRONMENT,
        explanation=(
            "Ambiente não reconhecido. Um ambiente desconhecido não pode ser "
            "tratado como desenvolvimento por conveniência."
        ),
        matches=lambda request: request.environment.strip().lower()
        not in _KNOWN_ENVIRONMENTS,
    ),
    # --- identidade -------------------------------------------------------
    PolicyRule(
        rule_id="capability.unknown_project",
        domain=PolicyDomain.CAPABILITY,
        effect=PolicyEffect.DENY,
        reason_code=UNKNOWN_PROJECT_IS_NOT_TRUSTED,
        explanation=(
            "Projeto não identificado não recebe a confiança de um projeto "
            "registrado; identidade não se presume."
        ),
        matches=lambda request: request.project_id.strip().lower()
        in _UNKNOWN_PROJECTS,
    ),
    PolicyRule(
        rule_id="capability.declared",
        domain=PolicyDomain.CAPABILITY,
        effect=PolicyEffect.DENY,
        reason_code=CAPABILITY_NOT_DECLARED,
        explanation=(
            "O consumidor não declara a capability exigida por esta ação no "
            "Capability Manifest."
        ),
        matches=lambda request: _text(request, "capability_declared") == "false",
    ),
    # --- execucao ---------------------------------------------------------
    PolicyRule(
        rule_id="execution.never_delegated",
        domain=PolicyDomain.EXECUTION,
        effect=PolicyEffect.DENY,
        reason_code=EXECUTION_IS_NEVER_DELEGATED,
        explanation=(
            "O Veltrix analisa e governa; ele não executa comando, não "
            "escreve e não deleta em nome do consumidor."
        ),
        matches=lambda request: _flag(request, "requests_target_execution"),
    ),
    PolicyRule(
        rule_id="execution.production_mutation",
        domain=PolicyDomain.EXECUTION,
        effect=PolicyEffect.REVIEW,
        reason_code=PRODUCTION_MUTATION_NEEDS_REVIEW,
        explanation=(
            "Operação que modifica estado em produção exige revisão humana "
            "registrada antes de seguir."
        ),
        matches=lambda request: _is_production(request) and _flag(request, "mutating"),
    ),
    # --- aprendizado ------------------------------------------------------
    PolicyRule(
        rule_id="learning.automatic_collection",
        domain=PolicyDomain.LEARNING,
        effect=PolicyEffect.DENY,
        reason_code=AUTOMATIC_COLLECTION_IS_FORBIDDEN,
        explanation=(
            "Coleta automática para treinamento é proibida: dado operacional "
            "não vira candidato de treino por acontecer."
        ),
        matches=lambda request: _flag(request, "automatic_collection"),
    ),
    PolicyRule(
        rule_id="learning.explicit_consent",
        domain=PolicyDomain.LEARNING,
        effect=PolicyEffect.DENY,
        reason_code=TRAINING_REQUIRES_EXPLICIT_CONSENT,
        explanation=(
            "Promoção a exemplo de treino exige consentimento explícito "
            "declarado; ausência de recusa não é consentimento."
        ),
        matches=lambda request: request.domain is PolicyDomain.LEARNING
        and _text(request, "training_consent") != "true",
    ),
    # --- privacidade ------------------------------------------------------
    PolicyRule(
        rule_id="privacy.raw_payload",
        domain=PolicyDomain.PRIVACY,
        effect=PolicyEffect.CONDITION,
        reason_code=RAW_PAYLOAD_IS_NOT_PERSISTED,
        explanation=(
            "Payload bruto não é persistido: apenas metadados sanitizados "
            "atravessam esta fronteira."
        ),
        condition="persistir apenas metadados sanitizados",
        matches=lambda request: _flag(request, "carries_raw_payload"),
    ),
    # --- provider ---------------------------------------------------------
    PolicyRule(
        rule_id="provider.real_call_opt_in",
        domain=PolicyDomain.PROVIDER,
        effect=PolicyEffect.DENY,
        reason_code=REAL_PROVIDER_REQUIRES_OPT_IN,
        explanation=(
            "Chamada a provider real exige opt-in explícito; o default nunca "
            "gasta crédito de ninguém por acidente."
        ),
        matches=lambda request: _flag(request, "real_provider_call")
        and _text(request, "real_provider_opt_in") != "true",
    ),
)


def rules_for(domain: PolicyDomain) -> tuple[PolicyRule, ...]:
    """Regras do dominio mais as que valem para qualquer dominio.

    Ambiente, identidade e execucao sao avaliadas sempre: uma acao de
    `learning` num ambiente desconhecido continua sendo uma acao num ambiente
    desconhecido.
    """
    universais = {
        PolicyDomain.ENVIRONMENT,
        PolicyDomain.CAPABILITY,
        PolicyDomain.EXECUTION,
        PolicyDomain.PRIVACY,
    }
    return tuple(
        rule for rule in RULES if rule.domain is domain or rule.domain in universais
    )

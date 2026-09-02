"""Policy Engine V1 — decisao declarativa, versionada e explicavel.

O problema
----------

As regras de policy do Veltrix existiam, funcionavam e estavam espalhadas:
regex em `policy_enforcement`, checagem de capability em `universal_contracts`,
gate em `risk_engine`, autorizacao de provider em `provider_authorization`.
Cada uma decidia bem o seu pedaco, e nenhuma sabia dizer, sozinha, "sob qual
politica, em qual versao, por qual motivo".

O que esta camada acrescenta
----------------------------

Um vocabulario comum de decisao: `policy_id`, `policy_version`, `decision` e
`reason_codes`. Toda decisao passa a ser rastreavel ate a regra que a produziu.

O que ela NAO faz
-----------------

Nao vira um rules engine universal. As regras que ja pertencem a um dominio —
o gate do Risk, o circuito de provider — continuam la, porque mudar de casa
nao as tornaria mais corretas e as tiraria do lugar onde sao testadas.

Aqui ficam apenas as decisoes TRANSVERSAIS: as que atravessam dominios e
precisavam ser respondidas do mesmo jeito em cada um.

A regra que atravessa tudo
--------------------------

    AI interpreta. Policy decide.

Nenhuma avaliacao consulta provider, modelo ou texto livre interpretado por
IA. A decisao e funcao dos ATRIBUTOS DECLARADOS, e por isso e reproduzivel:
os mesmos atributos produzem a mesma decisao, hoje e daqui a um ano.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

POLICY_ENGINE_VERSION = "policy-engine-v1"


class PolicyDecision(str, Enum):
    """O que a politica respondeu.

    `DENY` e terminal e nao e negociavel por consumidor. `REVIEW_REQUIRED`
    existe para o caso em que a politica sabe que nao sabe: melhor devolver a
    duvida a um humano do que converter incerteza em permissao.
    """

    ALLOW = "ALLOW"
    ALLOW_WITH_CONDITIONS = "ALLOW_WITH_CONDITIONS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    DENY = "DENY"


class PolicyDomain(str, Enum):
    """Dominio transversal ao qual a regra pertence."""

    RUNTIME = "runtime"
    PROVIDER = "provider"
    RISK = "risk"
    EVIDENCE = "evidence"
    LEARNING = "learning"
    PRIVACY = "privacy"
    CAPABILITY = "capability"
    ENVIRONMENT = "environment"
    EXECUTION = "execution"


class PolicyEffect(str, Enum):
    """Efeito declarado de uma regra que casou."""

    ALLOW = "allow"
    CONDITION = "condition"
    REVIEW = "review"
    DENY = "deny"


# A ordem importa e e deliberada: um `deny` nunca e apagado por um `allow`
# posterior, e a decisao final e sempre a mais restritiva encontrada. Politica
# que pudesse ser afrouxada pela ordem das regras seria politica por sorteio.
_SEVERITY = {
    PolicyEffect.ALLOW: 0,
    PolicyEffect.CONDITION: 1,
    PolicyEffect.REVIEW: 2,
    PolicyEffect.DENY: 3,
}

_EFFECT_TO_DECISION = {
    PolicyEffect.ALLOW: PolicyDecision.ALLOW,
    PolicyEffect.CONDITION: PolicyDecision.ALLOW_WITH_CONDITIONS,
    PolicyEffect.REVIEW: PolicyDecision.REVIEW_REQUIRED,
    PolicyEffect.DENY: PolicyDecision.DENY,
}


def decision_for(effects: list[PolicyEffect]) -> PolicyDecision:
    """A decisao e o efeito mais restritivo entre os que casaram."""
    if not effects:
        return PolicyDecision.ALLOW
    strongest = max(effects, key=lambda item: _SEVERITY[item])
    return _EFFECT_TO_DECISION[strongest]


class PolicyRequest(BaseModel):
    """O que se quer fazer, declarado como FATO.

    O consumidor descreve; ele nao conclui. Nao existem campos `decision`,
    `allow`, `approved` ou `policy_version` de entrada — a ausencia deles e
    parte do contrato, do mesmo modo que no contrato universal de risco.
    """

    model_config = ConfigDict(extra="forbid")

    domain: PolicyDomain
    action: str = Field(..., min_length=1, max_length=128)
    project_id: str = Field(..., min_length=1, max_length=128)
    environment: str = Field(..., min_length=1, max_length=32)
    producer: str = Field(..., min_length=1, max_length=64)

    # Atributos declarados. Sao dados, nunca instrucoes: nenhum valor aqui
    # vira condicao de codigo por si so — as regras e que os interpretam.
    attributes: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict, max_length=50
    )
    correlation_id: str | None = Field(default=None, max_length=128)


class PolicyRuleMatch(BaseModel):
    """Uma regra que casou, com o motivo pelo qual casou."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    rule_version: str
    domain: PolicyDomain
    effect: PolicyEffect
    reason_code: str
    explanation: str


class PolicyEvaluation(BaseModel):
    """Resultado auditavel de uma avaliacao de politica.

    `deterministic` e `Literal[True]` porque esta camada nao tem caminho
    nao-deterministico: se um dia alguem quiser acrescentar um, o tipo vai
    forcar a conversa em vez de deixar passar em silencio.
    """

    model_config = ConfigDict(extra="forbid")

    policy_id: str
    policy_version: Literal["policy-engine-v1"] = POLICY_ENGINE_VERSION
    decision: PolicyDecision
    domain: PolicyDomain
    action: str
    project_id: str
    reason_codes: list[str] = Field(default_factory=list)
    matched_rules: list[PolicyRuleMatch] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    correlation_id: str | None = None
    deterministic: Literal[True] = True
    provider_called: Literal[False] = False

    @property
    def allowed(self) -> bool:
        """Só ALLOW e ALLOW_WITH_CONDITIONS liberam."""
        return self.decision in {
            PolicyDecision.ALLOW,
            PolicyDecision.ALLOW_WITH_CONDITIONS,
        }

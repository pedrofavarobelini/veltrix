"""Proposta de contexto: o que o Veltrix resolveu sozinho, e com que base.

O que este objeto é
-------------------

Uma PROPOSTA. Não é autorização, não é análise e não é gate. É o que o sistema
acha que o pedido significa, com a origem e a confiança de cada peça, para um
humano confirmar antes de a análise rodar.

    ContextProposal → confirmação humana → RiskRequest → Risk Engine → Gate

A confirmação diz "sim, o contexto é este". Ela não diz "sim, pode executar".

Por que confiança é categórica
------------------------------

`HIGH`, `MEDIUM`, `LOW`. Não há `93%`.

Um percentual exigiria uma distribuição que este sistema não tem: a inferência
é casamento de termos declarados sobre texto segmentado por polaridade. Inventar
duas casas decimais daria ao leitor uma precisão que o método não sustenta, e
número decorativo é pior que categoria honesta.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.risk_intake.capabilities import TechnicalCapability

AUTO_CONTEXT_VERSION = "auto-context-v1"


class Confidence(str, Enum):
    """Quanto se pode confiar no que foi inferido."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ContextOrigin(str, Enum):
    """De onde veio cada peça do contexto.

    Espelha `risk_console.domain.Provenance` e acrescenta `POLICY_DERIVED`:
    política não pode ser apresentada como declaração do usuário. Quem lê
    precisa distinguir "você disse" de "a regra disse".
    """

    DECLARED = "DECLARED"
    USER_CONFIRMED = "USER_CONFIRMED"
    INFERRED = "INFERRED"
    POLICY_DERIVED = "POLICY_DERIVED"
    DEFAULTED = "DEFAULTED"
    UNKNOWN = "UNKNOWN"


class EffectivePermission(str, Enum):
    """O resultado da interseção das quatro camadas."""

    GRANTED = "GRANTED"
    FORBIDDEN = "FORBIDDEN"
    # Faltou base para decidir. Nunca é tratado como permitido.
    UNKNOWN = "UNKNOWN"


class ProposedField(BaseModel):
    """Um campo do contexto, com a origem e o porquê."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=64)
    values: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    origin: ContextOrigin
    confidence: Confidence
    reason: str = Field(..., min_length=1, max_length=256)
    # Marcado quando a peça muda o resultado e não foi declarada pelo humano.
    confirmation_required: bool = False

    @property
    def known(self) -> bool:
        return self.origin is not ContextOrigin.UNKNOWN


class PermissionDecision(BaseModel):
    """A interseção, aberta camada a camada.

    O princípio que ela existe para impor:

        capacidade pedida  !=  permissão concedida

    O prompt pode pedir `git.push`. Isso não torna push permitido.
    """

    model_config = ConfigDict(extra="forbid")

    capability: TechnicalCapability
    requested: bool
    forbidden_by_prompt: bool
    executor_supports: bool
    project_has: bool
    policy_allows: bool
    effective: EffectivePermission
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    explanation: str = Field(..., min_length=1, max_length=256)

    @property
    def conflict(self) -> bool:
        """Pedido explicitamente e negado por alguma camada."""
        return self.requested and self.effective is not EffectivePermission.GRANTED


class ContextProposal(BaseModel):
    """O que será submetido, se o humano confirmar."""

    model_config = ConfigDict(extra="forbid")

    proposal_version: Literal["auto-context-v1"] = AUTO_CONTEXT_VERSION
    project_id: str
    environment: str
    executor: str

    fields: list[ProposedField] = Field(default_factory=list)
    permissions: list[PermissionDecision] = Field(default_factory=list)

    # Declarados no próprio objeto para que uma proposta exportada carregue as
    # próprias garantias, sem depender de quem a leu saber da regra.
    authorizes_execution: Literal[False] = False
    replaces_risk_gate: Literal[False] = False
    ai_was_authority: Literal[False] = False

    # --- contagens para a tela de revisão ---------------------------------

    def _count(self, origin: ContextOrigin) -> int:
        return sum(1 for item in self.fields if item.origin is origin)

    @property
    def declared_count(self) -> int:
        return self._count(ContextOrigin.DECLARED) + self._count(
            ContextOrigin.USER_CONFIRMED
        )

    @property
    def inferred_count(self) -> int:
        return self._count(ContextOrigin.INFERRED)

    @property
    def policy_count(self) -> int:
        return self._count(ContextOrigin.POLICY_DERIVED)

    @property
    def unknown_count(self) -> int:
        return self._count(ContextOrigin.UNKNOWN)

    @property
    def review_count(self) -> int:
        """Peças que mudam o resultado e não vieram do humano."""
        return sum(1 for item in self.fields if item.confirmation_required)

    @property
    def conflicts(self) -> list[PermissionDecision]:
        """Capacidades pedidas que alguma camada negou.

        Conflito nunca é escondido: ele é a informação mais importante da
        proposta, porque é onde o pedido e a realidade discordam.
        """
        return [item for item in self.permissions if item.conflict]

    def field(self, name: str) -> ProposedField | None:
        for item in self.fields:
            if item.field == name:
                return item
        return None

    def permission(self, capability: TechnicalCapability) -> PermissionDecision | None:
        for item in self.permissions:
            if item.capability is capability:
                return item
        return None

    def granted(self) -> list[TechnicalCapability]:
        return [
            item.capability
            for item in self.permissions
            if item.effective is EffectivePermission.GRANTED
        ]

    def forbidden(self) -> list[TechnicalCapability]:
        return [
            item.capability
            for item in self.permissions
            if item.effective is EffectivePermission.FORBIDDEN
        ]

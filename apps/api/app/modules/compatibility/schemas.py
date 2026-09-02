"""E11 — Matriz de compatibilidade.

A pergunta que ela existe para responder
----------------------------------------

    "Este consumidor pode usar esta capability com estas versões?"

Hoje a resposta existia espalhada: o manifesto dizia o que o projeto declara,
o registro de versoes dizia se um contrato ainda vale, o catalogo dizia se um
provider esta homologado. Juntar as tres para responder uma pergunta era um
exercicio manual — e exercicio manual nao entra em CI.

Como ela evita virar acoplamento
--------------------------------

A matriz nao guarda linha por projeto. Ela CALCULA a resposta a partir do que
cada camada ja declara. Um consumidor novo passa a ser respondido por existir
no Capability Manifest, sem que este modulo mude.

`UNKNOWN` e uma resposta de primeira classe
-------------------------------------------

Nao saber e diferente de ser incompativel, e as duas coisas exigem acoes
diferentes: `INCOMPATIBLE` manda parar, `UNKNOWN` manda descobrir. Colapsar as
duas em "nao" faria alguem tratar ignorancia como veredito.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

COMPATIBILITY_MATRIX_VERSION = "compatibility-matrix-v1"


class CompatibilityStatus(str, Enum):
    """O veredito da matriz para uma combinacao."""

    SUPPORTED = "SUPPORTED"
    DEPRECATED = "DEPRECATED"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"


# Do mais restritivo para o menos. Como no Policy Engine, o pior achado manda:
# uma combinacao com uma peca incompativel nao vira suportada porque as outras
# pecas estavam boas.
_SEVERITY = {
    CompatibilityStatus.SUPPORTED: 0,
    CompatibilityStatus.DEPRECATED: 1,
    CompatibilityStatus.UNKNOWN: 2,
    CompatibilityStatus.INCOMPATIBLE: 3,
}


def worst(statuses: list[CompatibilityStatus]) -> CompatibilityStatus:
    if not statuses:
        return CompatibilityStatus.UNKNOWN
    return max(statuses, key=lambda item: _SEVERITY[item])


class CompatibilityDimension(str, Enum):
    """O que foi conferido. Cada uma vem de uma camada que ja existia."""

    PROJECT = "project"
    CAPABILITY = "capability"
    CONTRACT_VERSION = "contract_version"
    SDK_VERSION = "sdk_version"
    RISK_VERSION = "risk_version"
    POLICY_VERSION = "policy_version"
    ASSET_VERSION = "asset_version"
    PROVIDER_MODEL = "provider_model"


class CompatibilityFinding(BaseModel):
    """Um achado por dimensao, com o motivo em portugues."""

    model_config = ConfigDict(extra="forbid")

    dimension: CompatibilityDimension
    subject: str
    status: CompatibilityStatus
    reason_code: str
    explanation: str


class CompatibilityQuery(BaseModel):
    """A pergunta. Declara FATO; nao declara resposta."""

    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(..., min_length=1, max_length=128)
    capability: str = Field(..., min_length=1, max_length=64)
    contract_versions: tuple[str, ...] = Field(default_factory=tuple, max_length=20)
    sdk_version: str | None = Field(default=None, max_length=32)
    risk_version: str | None = Field(default=None, max_length=64)
    policy_version: str | None = Field(default=None, max_length=64)
    asset_versions: tuple[str, ...] = Field(default_factory=tuple, max_length=20)
    provider_model: str | None = Field(default=None, max_length=128)


class CompatibilityAnswer(BaseModel):
    """A resposta, com a conta aberta.

    `findings` existe para que o veredito seja conferivel dimensao a dimensao.
    Um `INCOMPATIBLE` sem dizer o que e incompativel obriga a adivinhar.
    """

    model_config = ConfigDict(extra="forbid")

    matrix_version: Literal["compatibility-matrix-v1"] = COMPATIBILITY_MATRIX_VERSION
    project_id: str
    capability: str
    status: CompatibilityStatus
    findings: list[CompatibilityFinding] = Field(default_factory=list)
    blocking: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def usable(self) -> bool:
        """Só SUPPORTED e DEPRECATED permitem uso; DEPRECATED com aviso."""
        return self.status in {
            CompatibilityStatus.SUPPORTED,
            CompatibilityStatus.DEPRECATED,
        }

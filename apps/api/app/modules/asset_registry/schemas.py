"""E8 — Registry versionado de prompts e configuracoes governadas.

O que entra, e o que nunca entra
--------------------------------

Entra ASSET GOVERNADO: system prompt, template, configuracao de routing, de
avaliacao, de risco. Coisas que o PedroCore escreve, versiona e responde por.

Nao entra prompt de usuario. Guardar indiscriminadamente o que consumidores
enviam transformaria um registry de configuracao num repositorio de dados
alheios — e a fronteira `Operational Data != Training Candidate` existe
justamente para isso nao acontecer por conveniencia.

Segredo nunca entra
-------------------

Verificado na entrada, e nao na revisao. Um registry versionado guarda para
sempre: um segredo que entra e um segredo que fica em todas as versoes
seguintes, inclusive nas que ninguem mais le.

Hash e proveniencia
-------------------

Cada versao carrega o hash do proprio conteudo. E o que permite dizer "esta e
exatamente a versao que rodou" sem confiar na numeracao — numero se digita
errado, hash nao.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ASSET_REGISTRY_VERSION = "asset-registry-v1"


class AssetKind(str, Enum):
    """Tipos governados. Cada um corresponde a algo que o core ja produz."""

    SYSTEM_PROMPT = "system_prompt"
    PROMPT_TEMPLATE = "prompt_template"
    ROUTING_CONFIG = "routing_config"
    EVALUATION_CONFIG = "evaluation_config"
    RISK_CONFIG = "risk_config"


class AssetStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ROLLED_BACK = "ROLLED_BACK"


_ALLOWED: dict[AssetStatus, frozenset[AssetStatus]] = {
    AssetStatus.DRAFT: frozenset({AssetStatus.ACTIVE, AssetStatus.DEPRECATED}),
    AssetStatus.ACTIVE: frozenset({AssetStatus.DEPRECATED, AssetStatus.ROLLED_BACK}),
    AssetStatus.DEPRECATED: frozenset({AssetStatus.ACTIVE}),
    AssetStatus.ROLLED_BACK: frozenset({AssetStatus.ACTIVE, AssetStatus.DEPRECATED}),
}


def transition_allowed(current: AssetStatus, target: AssetStatus) -> bool:
    return target in _ALLOWED[current]


# Formas de segredo. Conservador de proposito: recusar demais custa uma
# pergunta, aceitar de menos custa uma rotacao de credencial.
_SECRET_SHAPE = re.compile(
    r"(?i)\b(api[_-]?key|apikey|secret|password|senha|token|bearer|authorization)"
    r"\s*[:=]\s*\S|"
    r"[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s/@]+@|"
    r"\b(sk|pk|ghp|gho|xox[baprs])[-_][A-Za-z0-9_-]{16,}\b|"
    r"-----BEGIN[^-]{0,40}PRIVATE KEY-----"
)


def content_hash(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


class AssetVersion(BaseModel):
    """Uma versao imutavel de um asset governado."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    asset_id: str = Field(..., min_length=3, max_length=128)
    version: int = Field(..., ge=1)
    registry_version: Literal["asset-registry-v1"] = ASSET_REGISTRY_VERSION

    kind: AssetKind
    status: AssetStatus = AssetStatus.DRAFT
    content: str = Field(..., min_length=1, max_length=32000)
    content_hash: str = Field(..., pattern=r"^sha256:[a-f0-9]{64}$")

    provenance: str = Field(..., min_length=1, max_length=128)
    author: str = Field(..., min_length=1, max_length=64)
    change_reason: str = Field(..., min_length=3, max_length=512)
    created_at: datetime

    compatible_policy_version: str | None = Field(default=None, max_length=64)
    compatible_contract_versions: tuple[str, ...] = Field(
        default_factory=tuple, max_length=20
    )

    @field_validator("content")
    @classmethod
    def _content_carries_no_secret(cls, value: str) -> str:
        """Recusa na entrada. Um registry guarda para sempre."""
        if _SECRET_SHAPE.search(value):
            raise ValueError(
                "conteúdo tem forma de segredo e não pode entrar no registry: "
                "asset governado é configuração, nunca credencial"
            )
        return value

    @field_validator("content_hash")
    @classmethod
    def _hash_matches_nothing_on_its_own(cls, value: str) -> str:
        """O formato e conferido aqui; a correspondencia, no validador final."""
        return value

    @model_validator(mode="after")
    def _hash_matches_the_content(self) -> AssetVersion:
        """O hash precisa ser o hash DESTE conteudo.

        Sem isto, alguem poderia gravar conteudo novo com hash antigo e a
        rastreabilidade viraria decoracao — o campo diria uma coisa e o texto
        seria outra.
        """
        if self.content_hash != content_hash(self.content):
            raise ValueError("content_hash não corresponde ao conteúdo declarado")
        return self


class AssetRecord(BaseModel):
    """Um asset e a sua historia de versoes."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str
    kind: AssetKind
    versions: list[AssetVersion] = Field(default_factory=list)

    @property
    def active(self) -> AssetVersion | None:
        """A versao vigente. No maximo uma, por construcao do servico."""
        ativas = [item for item in self.versions if item.status is AssetStatus.ACTIVE]
        return ativas[-1] if ativas else None

    @property
    def latest(self) -> AssetVersion | None:
        return self.versions[-1] if self.versions else None

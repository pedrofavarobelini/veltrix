"""E5 — Model Registry e pipeline de promocao.

O problema
----------

O catalogo de providers ja sabia quais providers existem e quais estao
homologados. O que nao existia era o registro de MODELO com ciclo de vida: um
modelo novo entrava em uso porque alguem mudou uma configuracao, e nao porque
passou por evidencia.

A regra que este modulo impoe
-----------------------------

    Nenhum modelo vai para producao sem evidencia de avaliacao.

Promocao exige um `evaluation_id` real e um estado anterior de `APPROVED`. Nao
ha caminho de `REGISTERED` direto para `PROMOTED`, e nao ha promocao sem
evidencia — nem com a melhor das intencoes.

Separacao deliberada
--------------------

    Evaluation produz evidencia.  Registry decide promocao.

Sao camadas diferentes de proposito: quem mede nao deveria ser quem aprova, e
juntar as duas faria a nota depender de quem precisa dela.

Rollback e de primeira classe
-----------------------------

`ROLLED_BACK` existe porque toda promocao precisa ter volta. Um registro que
so soubesse avancar seria um registro que obriga a acertar de primeira.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MODEL_REGISTRY_VERSION = "model-registry-v1"


class ModelStatus(str, Enum):
    """Ciclo de vida de um modelo registrado."""

    REGISTERED = "REGISTERED"
    CANDIDATE = "CANDIDATE"
    EVALUATING = "EVALUATING"
    APPROVED = "APPROVED"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"
    DEPRECATED = "DEPRECATED"


# Transicoes permitidas. A tabela e explicita porque um grafo implicito de
# estados e onde se esconde o atalho que leva direto a producao.
_ALLOWED: dict[ModelStatus, frozenset[ModelStatus]] = {
    ModelStatus.REGISTERED: frozenset({ModelStatus.CANDIDATE, ModelStatus.DEPRECATED}),
    ModelStatus.CANDIDATE: frozenset(
        {ModelStatus.EVALUATING, ModelStatus.REJECTED, ModelStatus.DEPRECATED}
    ),
    ModelStatus.EVALUATING: frozenset(
        {ModelStatus.APPROVED, ModelStatus.REJECTED, ModelStatus.CANDIDATE}
    ),
    ModelStatus.APPROVED: frozenset(
        {ModelStatus.PROMOTED, ModelStatus.REJECTED, ModelStatus.DEPRECATED}
    ),
    ModelStatus.PROMOTED: frozenset({ModelStatus.ROLLED_BACK, ModelStatus.DEPRECATED}),
    ModelStatus.ROLLED_BACK: frozenset({ModelStatus.CANDIDATE, ModelStatus.DEPRECATED}),
    ModelStatus.REJECTED: frozenset({ModelStatus.CANDIDATE, ModelStatus.DEPRECATED}),
    ModelStatus.DEPRECATED: frozenset(),
}

# Estados que exigem evidencia de avaliacao para serem alcancados.
_REQUIRES_EVIDENCE = frozenset({ModelStatus.APPROVED, ModelStatus.PROMOTED})


def transition_allowed(current: ModelStatus, target: ModelStatus) -> bool:
    return target in _ALLOWED[current]


def requires_evidence(target: ModelStatus) -> bool:
    return target in _REQUIRES_EVIDENCE


class ModelCapability(str, Enum):
    """O que o modelo sabe fazer, declarado — nao inferido do nome."""

    TEXT = "text"
    VISION = "vision"
    OCR = "ocr"
    EMBEDDING = "embedding"
    STRUCTURED_OUTPUT = "structured_output"
    LONG_CONTEXT = "long_context"


class ModelEntry(BaseModel):
    """Um modelo registrado, com o estado e a evidencia que o sustenta."""

    model_config = ConfigDict(extra="forbid")

    model_key: str = Field(..., min_length=3, max_length=128)
    provider: str = Field(..., min_length=1, max_length=64)
    model_name: str = Field(..., min_length=1, max_length=96)
    model_version: str = Field(..., min_length=1, max_length=64)
    registry_version: Literal["model-registry-v1"] = MODEL_REGISTRY_VERSION

    status: ModelStatus = ModelStatus.REGISTERED
    capabilities: tuple[ModelCapability, ...] = Field(default_factory=tuple)

    # Ponteiros para a evidencia, nunca a evidencia em si.
    evaluation_ids: tuple[str, ...] = Field(default_factory=tuple, max_length=50)
    compatible_asset_ids: tuple[str, ...] = Field(default_factory=tuple, max_length=50)
    compatible_policy_version: str | None = Field(default=None, max_length=64)

    created_at: datetime
    promoted_at: datetime | None = None
    rejected_at: datetime | None = None
    rolled_back_at: datetime | None = None

    notes: str | None = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def _state_and_evidence_agree(self) -> ModelEntry:
        """Um estado que exige evidencia nao pode existir sem ela.

        A validacao vive no SCHEMA, e nao so no servico: um registro
        reconstruido de um dump tambem precisa passar por aqui, e um dump e
        exatamente por onde um estado invalido entraria sem ser notado.
        """
        if self.status in _REQUIRES_EVIDENCE and not self.evaluation_ids:
            raise ValueError(
                f"status {self.status.value} exige ao menos uma evaluation_id; "
                "promoção sem evidência não é promoção"
            )
        if self.status is ModelStatus.PROMOTED and self.promoted_at is None:
            raise ValueError("modelo PROMOTED precisa registrar promoted_at")
        return self

    @property
    def usable_in_production(self) -> bool:
        return self.status is ModelStatus.PROMOTED


class ModelTransition(BaseModel):
    """Registro imutavel de uma mudanca de estado."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_key: str
    from_status: ModelStatus
    to_status: ModelStatus
    reason: str = Field(..., min_length=3, max_length=512)
    evaluation_id: str | None = None
    actor: str = Field(..., min_length=1, max_length=64)
    occurred_at: datetime

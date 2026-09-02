"""E9 — Unified Audit Trail e correlacao transversal.

O problema
----------

Cada camada registrava o que fazia, e cada uma registrava a sua maneira. Para
seguir UMA operacao — do consumidor ao provider, ao risco, ao contrato, a
evidencia — era preciso cruzar identificadores diferentes na mao, e nem sempre
dava.

O que esta camada acrescenta
----------------------------

Um `correlation_id` que atravessa as etapas, e uma trilha de FATOS MINIMOS por
etapa: quem, o que, quando, em qual projeto, sob qual politica, com qual
resultado, referenciando o que ja existe.

O que ela deliberadamente NAO faz
---------------------------------

Nao duplica payload. A trilha guarda REFERENCIA (`analysis_id`, `contract_id`,
`evidence_id`) e nao conteudo — copiar o payload de cada etapa dobraria a
superficie de vazamento e dobraria o custo de armazenamento para responder a
mesma pergunta.

Privacidade
-----------

Prompt bruto, segredo e credencial nunca entram. O que entra e o tipo do fato
e o ponteiro para onde ele mora. Uma trilha que precisasse do conteudo para
ser util seria uma trilha que ninguem poderia exportar.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AUDIT_TRAIL_VERSION = "audit-trail-v1"

# Formato aberto o suficiente para o consumidor gerar o seu, restrito o
# bastante para nao virar campo de texto livre — e para nao caber um segredo.
_CORRELATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")


class AuditStage(str, Enum):
    """Etapas que uma operacao pode atravessar.

    Derivadas dos fluxos que existem hoje. Uma etapa sem fluxo correspondente
    seria uma promessa que a trilha nao sabe cumprir.
    """

    CONSUMER = "consumer"
    REQUEST = "request"
    POLICY = "policy"
    RUNTIME = "runtime"
    ROUTING = "routing"
    PROVIDER = "provider"
    RETRIEVAL = "retrieval"
    RISK = "risk"
    CONTRACT = "contract"
    EXECUTION = "execution"
    EVIDENCE = "evidence"
    EVALUATION = "evaluation"
    LEARNING = "learning"


class AuditOutcome(str, Enum):
    OK = "ok"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"


class AuditEvent(BaseModel):
    """Um fato registrado em uma etapa.

    `references` aponta para onde o detalhe mora — nunca traz o detalhe.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(..., min_length=8, max_length=128)
    correlation_id: str = Field(..., min_length=8, max_length=128)
    trail_version: Literal["audit-trail-v1"] = AUDIT_TRAIL_VERSION

    stage: AuditStage
    action: str = Field(..., min_length=1, max_length=128)
    outcome: AuditOutcome

    project_id: str = Field(..., min_length=1, max_length=128)
    producer: str = Field(..., min_length=1, max_length=64)
    environment: str = Field(..., min_length=1, max_length=32)
    occurred_at: datetime

    policy_id: str | None = Field(default=None, max_length=128)
    policy_version: str | None = Field(default=None, max_length=64)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple, max_length=20)

    # Ponteiros para o detalhe, jamais o detalhe.
    references: dict[str, str] = Field(default_factory=dict, max_length=20)

    # Declarado no proprio registro para que uma trilha exportada carregue a
    # propria garantia, sem depender de quem a leu saber da regra.
    contains_raw_payload: Literal[False] = False

    @field_validator("correlation_id")
    @classmethod
    def _correlation_is_an_identifier(cls, value: str) -> str:
        if not _CORRELATION_ID.match(value):
            raise ValueError(
                "correlation_id deve ser um identificador curto e não secreto"
            )
        return value

    @field_validator("references")
    @classmethod
    def _references_are_pointers_not_content(cls, value: dict[str, str]) -> dict[str, str]:
        """Referencia e um id, nao um texto.

        O limite de tamanho e a defesa concreta: um prompt inteiro nao cabe
        num campo de 128 caracteres, entao ninguem o coloca ali por engano.
        """
        for chave, referencia in value.items():
            if len(chave) > 64:
                raise ValueError(f"chave de referência longa demais: {chave[:20]}...")
            if len(referencia) > 128:
                raise ValueError(
                    f"referência '{chave}' parece conteúdo, não ponteiro: "
                    "a trilha guarda identificadores, não payload"
                )
        return value


class AuditTrail(BaseModel):
    """A operacao inteira, em ordem, sob um unico `correlation_id`."""

    model_config = ConfigDict(extra="forbid")

    correlation_id: str
    trail_version: Literal["audit-trail-v1"] = AUDIT_TRAIL_VERSION
    project_id: str
    events: list[AuditEvent] = Field(default_factory=list)

    @property
    def stages(self) -> list[AuditStage]:
        return [item.stage for item in self.events]

    @property
    def blocked(self) -> bool:
        return any(item.outcome is AuditOutcome.BLOCKED for item in self.events)

    @property
    def failed(self) -> bool:
        return any(item.outcome is AuditOutcome.FAILED for item in self.events)

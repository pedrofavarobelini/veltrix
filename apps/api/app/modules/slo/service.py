"""E10 — SLO e saude operacional.

O que ja existia
----------------

`observability` guarda execucoes. `provider_health` abre e fecha circuito. As
duas respondem perguntas locais; nenhuma responde "o Veltrix esta saudavel".

O que esta camada acrescenta
----------------------------

Indicadores agregados com ESTADO explicito e a amostra que o sustenta.

A regra que evita o pior erro desta camada
------------------------------------------

    Nao se inventa disponibilidade historica.

Um indicador sem medicao sai `UNKNOWN`, e nunca `HEALTHY`. Isto e o oposto do
default confortavel: um painel que mostra verde por falta de dado e pior que
um painel vazio, porque produz confianca sem base.

Cardinalidade
-------------

Os indicadores sao por NOME, e nao por requisicao, usuario ou prompt. A serie
e limitada ao conjunto declarado de SLIs — o suficiente para operar, longe do
bastante para explodir.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SLO_VERSION = "slo-v1"

# Amostra minima para afirmar saude. Abaixo disso o indicador e UNKNOWN: tres
# sucessos nao provam disponibilidade, e fingir que provam e como o painel
# verde nasce.
MIN_SAMPLE = 5


class HealthState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class SLIKind(str, Enum):
    """Indicadores medidos. Cada um corresponde a um fluxo que existe."""

    AVAILABILITY = "availability"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    PROVIDER_FAILURE = "provider_failure"
    ROUTING_FAILURE = "routing_failure"
    RISK_ANALYSIS_FAILURE = "risk_analysis_failure"
    OUTBOX_BACKLOG = "outbox_backlog"
    EVALUATION_LATENCY = "evaluation_latency"
    DATABASE_HEALTH = "database_health"


class SLOTarget(BaseModel):
    """Alvo declarado de um indicador.

    `degraded_at` e `unavailable_at` sao dois limiares, e nao um: um sistema
    que so soubesse "bom" e "morto" nao daria tempo de reagir.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: SLIKind
    unit: str = Field(..., min_length=1, max_length=32)
    degraded_at: float
    unavailable_at: float
    higher_is_worse: bool = True


_TARGETS: dict[SLIKind, SLOTarget] = {
    SLIKind.AVAILABILITY: SLOTarget(
        kind=SLIKind.AVAILABILITY,
        unit="ratio",
        degraded_at=0.99,
        unavailable_at=0.90,
        higher_is_worse=False,
    ),
    SLIKind.LATENCY: SLOTarget(
        kind=SLIKind.LATENCY, unit="seconds", degraded_at=2.0, unavailable_at=10.0
    ),
    SLIKind.ERROR_RATE: SLOTarget(
        kind=SLIKind.ERROR_RATE, unit="ratio", degraded_at=0.01, unavailable_at=0.10
    ),
    SLIKind.PROVIDER_FAILURE: SLOTarget(
        kind=SLIKind.PROVIDER_FAILURE, unit="ratio", degraded_at=0.05, unavailable_at=0.30
    ),
    SLIKind.ROUTING_FAILURE: SLOTarget(
        kind=SLIKind.ROUTING_FAILURE, unit="ratio", degraded_at=0.05, unavailable_at=0.25
    ),
    SLIKind.RISK_ANALYSIS_FAILURE: SLOTarget(
        kind=SLIKind.RISK_ANALYSIS_FAILURE,
        unit="ratio",
        degraded_at=0.02,
        unavailable_at=0.20,
    ),
    SLIKind.OUTBOX_BACKLOG: SLOTarget(
        kind=SLIKind.OUTBOX_BACKLOG, unit="entries", degraded_at=50, unavailable_at=500
    ),
    SLIKind.EVALUATION_LATENCY: SLOTarget(
        kind=SLIKind.EVALUATION_LATENCY, unit="seconds", degraded_at=30.0, unavailable_at=300.0
    ),
    SLIKind.DATABASE_HEALTH: SLOTarget(
        kind=SLIKind.DATABASE_HEALTH, unit="ratio", degraded_at=0.99, unavailable_at=0.95,
        higher_is_worse=False,
    ),
}


class SLIReading(BaseModel):
    """O estado de um indicador, com a amostra que o sustenta."""

    model_config = ConfigDict(extra="forbid")

    kind: SLIKind
    state: HealthState
    value: float | None = None
    unit: str
    sample_size: int = Field(..., ge=0)
    target_degraded_at: float
    target_unavailable_at: float
    reason_code: str


class HealthSnapshot(BaseModel):
    """Saude agregada. O pior indicador manda."""

    model_config = ConfigDict(extra="forbid")

    slo_version: Literal["slo-v1"] = SLO_VERSION
    state: HealthState
    readings: list[SLIReading] = Field(default_factory=list)
    degraded: list[str] = Field(default_factory=list)
    unavailable: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    observed_at: datetime


_STATE_SEVERITY = {
    HealthState.HEALTHY: 0,
    HealthState.DEGRADED: 1,
    HealthState.UNKNOWN: 2,
    HealthState.UNAVAILABLE: 3,
}

INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
WITHIN_TARGET = "WITHIN_TARGET"
BREACHED_DEGRADED = "BREACHED_DEGRADED_THRESHOLD"
BREACHED_UNAVAILABLE = "BREACHED_UNAVAILABLE_THRESHOLD"


class SLOService:
    """Coleta observacoes e agrega saude. Nao inventa numero ausente."""

    def __init__(self, window: int = 200) -> None:
        self._window = window
        self._samples: dict[SLIKind, deque[float]] = {}

    def observe(self, kind: SLIKind, value: float) -> None:
        serie = self._samples.setdefault(kind, deque(maxlen=self._window))
        serie.append(float(value))

    def reading(self, kind: SLIKind) -> SLIReading:
        alvo = _TARGETS[kind]
        serie = self._samples.get(kind) or ()
        amostra = len(serie)

        if amostra < MIN_SAMPLE:
            # UNKNOWN, e nao HEALTHY. Verde por falta de dado e pior que
            # painel vazio: produz confianca sem base.
            return SLIReading(
                kind=kind,
                state=HealthState.UNKNOWN,
                value=None,
                unit=alvo.unit,
                sample_size=amostra,
                target_degraded_at=alvo.degraded_at,
                target_unavailable_at=alvo.unavailable_at,
                reason_code=INSUFFICIENT_SAMPLE,
            )

        valor = sum(serie) / len(serie)
        if alvo.higher_is_worse:
            indisponivel = valor >= alvo.unavailable_at
            degradado = valor >= alvo.degraded_at
        else:
            indisponivel = valor <= alvo.unavailable_at
            degradado = valor <= alvo.degraded_at

        if indisponivel:
            estado, motivo = HealthState.UNAVAILABLE, BREACHED_UNAVAILABLE
        elif degradado:
            estado, motivo = HealthState.DEGRADED, BREACHED_DEGRADED
        else:
            estado, motivo = HealthState.HEALTHY, WITHIN_TARGET

        return SLIReading(
            kind=kind,
            state=estado,
            value=round(valor, 6),
            unit=alvo.unit,
            sample_size=amostra,
            target_degraded_at=alvo.degraded_at,
            target_unavailable_at=alvo.unavailable_at,
            reason_code=motivo,
        )

    def snapshot(self, now: datetime | None = None) -> HealthSnapshot:
        leituras = [self.reading(kind) for kind in SLIKind]
        pior = max(
            (item.state for item in leituras),
            key=lambda estado: _STATE_SEVERITY[estado],
            default=HealthState.UNKNOWN,
        )
        return HealthSnapshot(
            state=pior,
            readings=leituras,
            degraded=[i.kind.value for i in leituras if i.state is HealthState.DEGRADED],
            unavailable=[
                i.kind.value for i in leituras if i.state is HealthState.UNAVAILABLE
            ],
            unknown=[i.kind.value for i in leituras if i.state is HealthState.UNKNOWN],
            observed_at=now or datetime.now(timezone.utc),
        )

    def targets(self) -> list[SLOTarget]:
        return [_TARGETS[kind] for kind in SLIKind]

    def reset(self) -> None:
        self._samples.clear()


slo_service = SLOService()

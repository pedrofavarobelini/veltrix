"""E7 — Roteamento por qualidade, custo e latencia, com decisao explicavel.

O que ja existia, e continua
----------------------------

`task_router` escolhe estrategia por tarefa. `provider_health` abre e fecha
circuito. `provider_catalog` sabe quem esta homologado. `provider_binding` e
`provider_authorization` dizem quem pode usar o que.

Nada disso foi substituido. Esta camada ORDENA candidatos que ja passaram por
essas portas — e nao abre nenhuma porta nova.

Como a decisao e tomada
-----------------------

Eliminacao primeiro, ordenacao depois.

Politica, capability e disponibilidade ELIMINAM. Um candidato reprovado por
qualquer uma das tres nao entra no ranking, por melhor que fosse a nota: nota
alta nao compra permissao. Qualidade, custo e latencia so ordenam quem
sobreviveu.

Sobre os pesos
--------------

Os pesos sao POR ESTRATEGIA e estao declarados, com a soma sempre igual a 1.
Nao ha peso magico no meio do codigo: `quality_first` privilegia qualidade,
`cost_aware` privilegia custo, e quem discordar troca a estrategia — nao o
algoritmo.

Os sinais sao normalizados para 0..1 e o sentido e explicito: custo e latencia
sao invertidos, porque menor e melhor, e somar "menor e melhor" com "maior e
melhor" sem inverter produz um numero que nao significa nada.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ROUTING_INTELLIGENCE_VERSION = "routing-intelligence-v1"


class RoutingStrategy(str, Enum):
    QUALITY_FIRST = "quality_first"
    COST_AWARE = "cost_aware"
    LATENCY_AWARE = "latency_aware"
    BALANCED = "balanced"


# Pesos declarados por estrategia. Somam 1 e sao verificados por teste: um
# conjunto que nao somasse 1 produziria notas incomparaveis entre estrategias.
_WEIGHTS: dict[RoutingStrategy, dict[str, float]] = {
    RoutingStrategy.QUALITY_FIRST: {"quality": 0.70, "latency": 0.20, "cost": 0.10},
    RoutingStrategy.COST_AWARE: {"quality": 0.25, "latency": 0.15, "cost": 0.60},
    RoutingStrategy.LATENCY_AWARE: {"quality": 0.25, "latency": 0.60, "cost": 0.15},
    RoutingStrategy.BALANCED: {"quality": 0.40, "latency": 0.30, "cost": 0.30},
}


class EliminationReason(str, Enum):
    """Por que um candidato saiu antes do ranking."""

    POLICY_DENIED = "POLICY_DENIED"
    CAPABILITY_MISSING = "CAPABILITY_MISSING"
    UNAVAILABLE = "UNAVAILABLE"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    NOT_HOMOLOGATED = "NOT_HOMOLOGATED"


class RoutingSignals(BaseModel):
    """Sinais medidos de um candidato. Normalizados, com sentido declarado."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # 0..1, maior e melhor.
    quality: float = Field(..., ge=0.0, le=1.0)
    # 0..1, maior significa MAIS caro. Invertido na pontuacao.
    cost: float = Field(..., ge=0.0, le=1.0)
    # 0..1, maior significa MAIS lento. Invertido na pontuacao.
    latency: float = Field(..., ge=0.0, le=1.0)
    # Amostra que sustenta os numeros acima. Zero significa "sem medicao".
    sample_size: int = Field(default=0, ge=0)


class RoutingCandidate(BaseModel):
    """Um candidato ja autorizado pelas camadas que decidem autorizacao."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(..., min_length=1, max_length=128)
    provider: str = Field(..., min_length=1, max_length=64)
    model: str = Field(..., min_length=1, max_length=96)
    signals: RoutingSignals

    policy_allowed: bool = True
    capability_satisfied: bool = True
    available: bool = True
    circuit_closed: bool = True
    homologated: bool = True

    def elimination(self) -> EliminationReason | None:
        """A primeira porta fechada. Ordem e do mais grave para o menos."""
        if not self.policy_allowed:
            return EliminationReason.POLICY_DENIED
        if not self.capability_satisfied:
            return EliminationReason.CAPABILITY_MISSING
        if not self.homologated:
            return EliminationReason.NOT_HOMOLOGATED
        if not self.circuit_closed:
            return EliminationReason.CIRCUIT_OPEN
        if not self.available:
            return EliminationReason.UNAVAILABLE
        return None


class ScoredCandidate(BaseModel):
    """Candidato pontuado, com a conta aberta."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    provider: str
    model: str
    score: float = Field(..., ge=0.0, le=1.0)
    contributions: dict[str, float] = Field(default_factory=dict)
    measured: bool = True


class EliminatedCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    reason: EliminationReason


class RoutingDecision(BaseModel):
    """A decisao, explicavel candidato a candidato."""

    model_config = ConfigDict(extra="forbid")

    routing_version: Literal["routing-intelligence-v1"] = ROUTING_INTELLIGENCE_VERSION
    strategy: RoutingStrategy
    selected_provider: str | None = None
    selected_model: str | None = None
    selected_candidate_id: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    ranked: list[ScoredCandidate] = Field(default_factory=list)
    eliminated: list[EliminatedCandidate] = Field(default_factory=list)
    weights: dict[str, float] = Field(default_factory=dict)

    # Roteamento ordena; ele nunca autoriza. Declarado no proprio resultado.
    bypassed_policy: Literal[False] = False

    @model_validator(mode="after")
    def _a_selection_must_come_from_the_ranking(self) -> RoutingDecision:
        """Nao existe selecionado que nao esteja no ranking.

        Sem isto, uma escolha poderia aparecer sem ter passado pela
        eliminacao — que e exatamente o bypass que esta camada nao pode ter.
        """
        if self.selected_candidate_id is None:
            return self
        if not any(
            item.candidate_id == self.selected_candidate_id for item in self.ranked
        ):
            raise ValueError(
                "candidato selecionado não está no ranking: seleção fora da "
                "eliminação seria bypass de política"
            )
        return self


NO_CANDIDATE_SURVIVED = "NO_CANDIDATE_SURVIVED"
SELECTED_BY_STRATEGY = "SELECTED_BY_STRATEGY"
SELECTED_WITHOUT_MEASUREMENT = "SELECTED_WITHOUT_MEASUREMENT"


class RoutingIntelligenceService:
    """Ordena candidatos autorizados. Nao autoriza nenhum."""

    def decide(
        self,
        candidates: list[RoutingCandidate],
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
    ) -> RoutingDecision:
        pesos = _WEIGHTS[strategy]
        eliminados: list[EliminatedCandidate] = []
        sobreviventes: list[RoutingCandidate] = []

        for candidato in candidates:
            motivo = candidato.elimination()
            if motivo is not None:
                eliminados.append(
                    EliminatedCandidate(
                        candidate_id=candidato.candidate_id, reason=motivo
                    )
                )
            else:
                sobreviventes.append(candidato)

        ranking = sorted(
            (self._score(item, pesos) for item in sobreviventes),
            key=lambda item: (item.score, item.candidate_id),
            reverse=True,
        )

        if not ranking:
            return RoutingDecision(
                strategy=strategy,
                reason_codes=[NO_CANDIDATE_SURVIVED],
                eliminated=eliminados,
                weights=dict(pesos),
            )

        escolhido = ranking[0]
        motivos = [SELECTED_BY_STRATEGY]
        if not escolhido.measured:
            # Escolher sem medicao e legitimo — as vezes e o unico candidato —
            # mas quem le a decisao precisa saber que a nota veio de default.
            motivos.append(SELECTED_WITHOUT_MEASUREMENT)

        return RoutingDecision(
            strategy=strategy,
            selected_provider=escolhido.provider,
            selected_model=escolhido.model,
            selected_candidate_id=escolhido.candidate_id,
            reason_codes=motivos,
            ranked=ranking,
            eliminated=eliminados,
            weights=dict(pesos),
        )

    @staticmethod
    def _score(candidate: RoutingCandidate, weights: dict[str, float]) -> ScoredCandidate:
        sinais = candidate.signals
        # Custo e latencia sao invertidos: menor e melhor, e somar sem
        # inverter produziria um numero sem significado.
        contribuicoes = {
            "quality": weights["quality"] * sinais.quality,
            "cost": weights["cost"] * (1.0 - sinais.cost),
            "latency": weights["latency"] * (1.0 - sinais.latency),
        }
        return ScoredCandidate(
            candidate_id=candidate.candidate_id,
            provider=candidate.provider,
            model=candidate.model,
            score=round(sum(contribuicoes.values()), 6),
            contributions={k: round(v, 6) for k, v in contribuicoes.items()},
            measured=sinais.sample_size > 0,
        )


routing_intelligence_service = RoutingIntelligenceService()

"""Evaluation & Training Foundation — contratos (Era 8).

O que esta Era entrega, e o que deliberadamente NAO entrega
------------------------------------------------------------

Entrega: as interfaces, as transicoes de estado e as politicas de promocao e
rollback. Nao entrega treinamento — nem um LoRA de brinquedo para "provar que
funciona". Um treino executado sem readiness produziria um modelo a partir de
populacao que a governanca recusou, e o Gate teria sido comprado com
exatamente o que ele existe para impedir.

Veltrix como orquestrador
---------------------------

O Veltrix decide O QUE treinar, com QUAL dataset, sob QUAL politica, e o que
fazer com o resultado. Ele nao precisa ser quem roda a GPU. Por isso o backend
e um `Protocol`: local, Hugging Face, nuvem com GPU ou qualquer outro entram
implementando a interface, e nenhum deles aparece no dominio.

Se um nome de provider aparecesse aqui, trocar de backend viraria refatoracao
do dominio — que e o mesmo erro de acoplamento que a Era 3 removeu do runtime,
so que com outra roupa.

Promocao e rollback
-------------------

Promover um modelo e a decisao mais perigosa do ciclo, porque o dano nao
aparece na hora: um modelo pior entra em producao e a degradacao chega diluida.
Por isso a promocao aqui exige comparacao contra baseline com margem explicita,
e nao "a metrica subiu".

E por isso todo modelo promovido carrega de qual versao ele veio: sem isso, o
rollback vira arqueologia no meio de um incidente.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

TRAINING_FOUNDATION_POLICY_VERSION = "training-foundation-v1"

ShortText = Annotated[str, Field(min_length=1, max_length=128)]
Signature = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class EvaluationMetric(str, Enum):
    """Metricas suportadas.

    Um enum fechado, e nao texto livre: metrica com nome livre torna duas
    execucoes incomparaveis assim que alguem escreve `accuracy` num lugar e
    `acc` em outro.
    """

    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"
    EXACT_MATCH = "exact_match"
    PASS_RATE = "pass_rate"
    REGRESSION_COUNT = "regression_count"


# Metricas em que MENOR e melhor. Sem esta distincao, uma comparacao ingenua
# promoveria o modelo que mais regride.
_LOWER_IS_BETTER: frozenset[EvaluationMetric] = frozenset(
    {EvaluationMetric.REGRESSION_COUNT}
)


class MetricValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: EvaluationMetric
    value: float
    sample_size: int = Field(..., ge=1)

    @model_validator(mode="after")
    def _bounded_metrics_stay_in_range(self) -> MetricValue:
        bounded = {
            EvaluationMetric.ACCURACY,
            EvaluationMetric.PRECISION,
            EvaluationMetric.RECALL,
            EvaluationMetric.F1,
            EvaluationMetric.EXACT_MATCH,
            EvaluationMetric.PASS_RATE,
        }
        if self.metric in bounded and not 0.0 <= self.value <= 1.0:
            raise ValueError(f"{self.metric.value} deve estar entre 0.0 e 1.0")
        if self.metric is EvaluationMetric.REGRESSION_COUNT and self.value < 0:
            raise ValueError("regression_count não pode ser negativo")
        return self

    @property
    def higher_is_better(self) -> bool:
        return self.metric not in _LOWER_IS_BETTER


class EvaluationRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationRun(BaseModel):
    """Uma avaliacao contra uma VERSAO de dataset, nunca contra "o dataset".

    Sem a versao, comparar duas execucoes seria comparar contra alvos
    diferentes sem saber.
    """

    model_config = ConfigDict(extra="forbid")

    policy_version: Literal["training-foundation-v1"] = TRAINING_FOUNDATION_POLICY_VERSION
    evaluation_id: ShortText
    dataset_id: ShortText
    dataset_version: int = Field(..., ge=1)
    dataset_fingerprint: Signature
    model_ref: ShortText
    status: EvaluationRunStatus = EvaluationRunStatus.PENDING
    metrics: tuple[MetricValue, ...] = Field(default_factory=tuple)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @model_validator(mode="after")
    def _completed_runs_must_report_metrics(self) -> EvaluationRun:
        """Avaliacao concluida sem metrica nao avaliou nada."""
        if self.status is EvaluationRunStatus.COMPLETED and not self.metrics:
            raise ValueError("avaliação concluída precisa reportar ao menos uma métrica")
        return self

    def metric(self, metric: EvaluationMetric) -> MetricValue | None:
        return next((item for item in self.metrics if item.metric is metric), None)


class PromotionDecision(str, Enum):
    PROMOTE = "promote"
    REJECT = "reject"
    REQUIRES_REVIEW = "requires_review"


class PromotionPolicy(BaseModel):
    """Quando um candidato pode substituir o modelo em producao.

    `minimum_improvement` existe porque "a metrica subiu" nao e motivo: uma
    melhora de 0,001 em 50 exemplos e ruido, e promover com base nela troca o
    modelo de producao por sorte.

    `minimum_sample_size` existe pelo mesmo motivo, do outro lado: uma melhora
    grande em amostra minuscula tambem e ruido.
    """

    model_config = ConfigDict(extra="forbid")

    policy_version: Literal["training-foundation-v1"] = TRAINING_FOUNDATION_POLICY_VERSION
    primary_metric: EvaluationMetric = EvaluationMetric.ACCURACY
    minimum_improvement: float = Field(default=0.01, ge=0.0, le=1.0)
    minimum_sample_size: int = Field(default=100, ge=1)
    # Nenhuma metrica pode piorar mais que isto, mesmo que a principal melhore.
    # Sem este teto, um modelo poderia ganhar accuracy destruindo recall.
    maximum_regression: float = Field(default=0.02, ge=0.0, le=1.0)
    requires_human_review: bool = True


class BaselineComparison(BaseModel):
    """O resultado da comparacao, com o porque explicito."""

    model_config = ConfigDict(extra="forbid")

    decision: PromotionDecision
    primary_metric: EvaluationMetric
    baseline_value: float
    candidate_value: float
    improvement: float
    reason_codes: list[str] = Field(default_factory=list)
    # Reafirmado: comparar nunca promove por conta propria.
    promoted: Literal[False] = False


class TrainingRunStatus(str, Enum):
    """Estados de um treino.

    `BLOCKED` e distinto de `FAILED`: bloqueado significa que a governanca
    recusou iniciar, e falhado significa que iniciou e quebrou. Colapsar os
    dois esconderia justamente o caso em que o sistema funcionou como devia.
    """

    REQUESTED = "requested"
    BLOCKED = "blocked"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingRun(BaseModel):
    """Um pedido de treino, com toda a proveniencia necessaria para auditar."""

    model_config = ConfigDict(extra="forbid")

    policy_version: Literal["training-foundation-v1"] = TRAINING_FOUNDATION_POLICY_VERSION
    run_id: ShortText
    dataset_id: ShortText
    dataset_version: int = Field(..., ge=1)
    dataset_fingerprint: Signature
    backend_id: ShortText
    base_model_ref: ShortText
    requested_by: ShortText
    requested_at: datetime
    status: TrainingRunStatus = TrainingRunStatus.REQUESTED
    blocked_reason_codes: list[str] = Field(default_factory=list)
    # Reafirmado no proprio registro: pedir treino nao inicia treino.
    training_executed: bool = False

    @model_validator(mode="after")
    def _blocked_runs_must_explain_themselves(self) -> TrainingRun:
        if self.status is TrainingRunStatus.BLOCKED and not self.blocked_reason_codes:
            raise ValueError("run bloqueado precisa declarar o motivo")
        if self.status is not TrainingRunStatus.BLOCKED and self.blocked_reason_codes:
            raise ValueError("apenas run bloqueado carrega blocked_reason_codes")
        return self


@runtime_checkable
class TrainingBackend(Protocol):
    """Executor de treino — local, Hugging Face, nuvem, o que for.

    O dominio conhece esta interface e nada alem dela. Nenhum nome de provider
    aparece no Veltrix: trocar de backend nao pode virar refatoracao de
    dominio, que e o mesmo erro de acoplamento que a Era 3 removeu do runtime.
    """

    backend_id: str

    def available(self) -> bool:
        """O backend pode receber trabalho agora?"""
        ...

    def estimate(self, run: TrainingRun) -> dict:
        """Estimativa (custo, duracao) sem iniciar nada."""
        ...

    def start(self, run: TrainingRun) -> str:
        """Inicia o treino e devolve o identificador externo."""
        ...


class ModelStage(str, Enum):
    """Onde um modelo esta no ciclo.

    `ARCHIVED` e separado de `REJECTED`: arquivado ja serviu e saiu, rejeitado
    nunca entrou. A distincao importa no rollback — so faz sentido voltar para
    algo que ja esteve em producao.
    """

    CANDIDATE = "candidate"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class ModelRegistryEntry(BaseModel):
    """Um modelo registrado, com a linhagem que torna rollback possivel."""

    model_config = ConfigDict(extra="forbid")

    policy_version: Literal["training-foundation-v1"] = TRAINING_FOUNDATION_POLICY_VERSION
    model_ref: ShortText
    stage: ModelStage = ModelStage.CANDIDATE
    dataset_id: ShortText
    dataset_version: int = Field(..., ge=1)
    training_run_id: str | None = Field(default=None, max_length=128)
    evaluation_id: str | None = Field(default=None, max_length=128)
    registered_at: datetime
    # De qual modelo de producao este veio. Sem isto o rollback vira
    # arqueologia no meio de um incidente.
    supersedes: str | None = Field(default=None, max_length=128)


class RollbackPolicy(BaseModel):
    """Como voltar atras.

    `require_previous_production` e `Literal[True]` de proposito: um rollback
    sem alvo conhecido nao e rollback, e desligar o modelo e torcer.
    """

    model_config = ConfigDict(extra="forbid")

    policy_version: Literal["training-foundation-v1"] = TRAINING_FOUNDATION_POLICY_VERSION
    require_previous_production: Literal[True] = True
    keep_rejected_for_audit: bool = True

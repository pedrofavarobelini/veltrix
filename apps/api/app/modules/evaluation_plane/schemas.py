"""E4 — Evaluation Plane V2: avaliacao governada e reproduzivel.

O que ja existia
----------------

`evaluation` checava respostas contra criterios. `eval_harness` rodava casos.
As duas funcionavam e nenhuma registrava a avaliacao como EVIDENCIA
reproduzivel: nao dava para dizer, meses depois, "isto foi medido sobre qual
sujeito, com qual suite, em qual ambiente, sob qual versao".

O que esta camada acrescenta
----------------------------

Um registro de avaliacao com sujeito, suite, metricas, ambiente, versao e
resultado — apontando para a evidencia, nunca copiando conteudo.

A separacao que sustenta o resto
--------------------------------

    Evaluation produz evidencia.  Outra camada decide promocao.

Aqui nao existe nenhum caminho que promova nada. O Model Registry consulta a
evidencia e decide; se a avaliacao pudesse promover, quem mede passaria a
depender do resultado que precisa.

Dataset nao e fabricado
-----------------------

Se nao ha dataset pronto, a avaliacao sai com `DATASET_NOT_READY` e sem
metricas. Inventar amostra para produzir um numero seria produzir um numero
sobre nada — e alguem confiaria nele.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EVALUATION_PLANE_VERSION = "evaluation-plane-v2"


class EvaluationSubjectKind(str, Enum):
    """O que esta sendo avaliado."""

    PROVIDER = "provider"
    MODEL = "model"
    PROMPT = "prompt"
    ROUTING_CANDIDATE = "routing_candidate"
    TRAINING_CANDIDATE = "training_candidate"
    MODEL_CANDIDATE = "model_candidate"


class EvaluationStatus(str, Enum):
    COMPLETED = "COMPLETED"
    DATASET_NOT_READY = "DATASET_NOT_READY"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class EvaluationSubject(BaseModel):
    """Quem foi avaliado, identificado sem ambiguidade."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: EvaluationSubjectKind
    subject_id: str = Field(..., min_length=1, max_length=160)
    subject_version: str | None = Field(default=None, max_length=64)


class EvaluationMetric(BaseModel):
    """Uma metrica medida, com a unidade declarada.

    `sample_size` viaja junto de proposito: uma media sobre tres casos e uma
    media sobre trezentos nao valem a mesma coisa, e separar o numero do seu
    tamanho de amostra e como se perde essa diferenca.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(..., min_length=1, max_length=64)
    value: float
    unit: str = Field(..., min_length=1, max_length=32)
    sample_size: int = Field(..., ge=0)
    higher_is_better: bool = True


class EvaluationRecord(BaseModel):
    """Registro auditavel de uma avaliacao."""

    model_config = ConfigDict(extra="forbid")

    evaluation_id: str = Field(..., min_length=8, max_length=128)
    plane_version: Literal["evaluation-plane-v2"] = EVALUATION_PLANE_VERSION

    subject: EvaluationSubject
    suite: str = Field(..., min_length=1, max_length=96)
    suite_version: str = Field(..., min_length=1, max_length=32)
    dataset_id: str | None = Field(default=None, max_length=128)
    dataset_slice: str | None = Field(default=None, max_length=128)

    environment: str = Field(..., min_length=1, max_length=32)
    project_id: str = Field(..., min_length=1, max_length=128)
    producer: str = Field(..., min_length=1, max_length=64)

    status: EvaluationStatus
    metrics: tuple[EvaluationMetric, ...] = Field(default_factory=tuple, max_length=50)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple, max_length=20)

    evidence_ids: tuple[str, ...] = Field(default_factory=tuple, max_length=50)
    correlation_id: str | None = Field(default=None, max_length=128)
    evaluated_at: datetime

    # Declarado no registro: esta camada nao promove nada, e quem ler o
    # registro sozinho precisa saber disso sem consultar a documentacao.
    promotes_subject: Literal[False] = False

    @model_validator(mode="after")
    def _status_and_metrics_agree(self) -> EvaluationRecord:
        """Um resultado sem dataset nao pode trazer metrica.

        Se trouxesse, a metrica seria sobre nada — e alguem a usaria como se
        fosse sobre alguma coisa.
        """
        if self.status is EvaluationStatus.DATASET_NOT_READY and self.metrics:
            raise ValueError(
                "DATASET_NOT_READY não pode trazer métricas: "
                "não se mede o que não existe"
            )
        if self.status is EvaluationStatus.COMPLETED and not self.metrics:
            raise ValueError(
                "avaliação COMPLETED sem métrica não é avaliação concluída"
            )
        return self

    @property
    def usable_as_promotion_evidence(self) -> bool:
        """Só uma avaliação concluída serve de evidência para promoção."""
        return self.status is EvaluationStatus.COMPLETED and bool(self.metrics)

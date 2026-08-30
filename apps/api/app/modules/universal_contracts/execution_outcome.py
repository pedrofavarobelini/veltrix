"""Execution Outcome Contract V1.

Por que existe separado do Execution Contract do Risk Engine
------------------------------------------------------------

O `risk_engine` ja tem `PostExecutionOutcome`, e ele e otimo — para o que faz.
Ele e amarrado a um `ExecutionContract` ASSINADO, emitido pelo proprio
PedroCore, com chave de assinatura e revisores declarados. Um consumidor
externo nao tem esse contrato e nao deve ter: exigi-lo obrigaria a distribuir
capacidade de assinatura para fora.

Este contrato e o degrau anterior: registra o que um produtor externo executou,
sem prometer que aquilo estava sob contrato assinado. Os dois coexistem, e o
mais forte nao foi enfraquecido para acomodar o mais fraco.

O que este contrato deliberadamente NAO permite
-----------------------------------------------

Transformar-se em Training Candidate. Um resultado de execucao e fonte
operacional; virar exemplo de treino exige passar por elegibilidade,
privacidade, proveniencia e autorizacao no Learning Plane. O caminho curto nao
existe porque ele e exatamente o risco.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.universal_contracts.quality_evidence import EvidenceReference
from app.modules.universal_contracts.versioning import EXECUTION_OUTCOME_V1

ShortText = Annotated[str, Field(min_length=1, max_length=128)]


class ExecutionResult(str, Enum):
    """Como a execucao terminou, do ponto de vista do produtor."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class ExecutionState(str, Enum):
    """Estado final do sistema apos a execucao.

    Separado de `ExecutionResult` porque as duas perguntas sao diferentes: uma
    execucao pode FALHAR e ainda assim deixar o sistema estavel, e pode ter
    sucesso parcial deixando estado inconsistente. Colapsar as duas em um campo
    perderia justamente o caso que importa para risco.
    """

    STABLE = "stable"
    DEGRADED = "degraded"
    INCONSISTENT = "inconsistent"
    UNKNOWN = "unknown"


class ExecutionDiagnostic(BaseModel):
    """Erro ou aviso observado, sem stack trace nem payload sensivel."""

    model_config = ConfigDict(extra="forbid")

    level: Literal["warning", "error"]
    code: ShortText
    message: str = Field(..., min_length=1, max_length=1024)


class ExecutionOutcomeV1(BaseModel):
    """Resultado universal de execucao, independente de projeto."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["pedrocore-execution-outcome/v1"] = EXECUTION_OUTCOME_V1
    outcome_id: ShortText
    operation: ShortText
    result: ExecutionResult
    final_state: ExecutionState = ExecutionState.UNKNOWN
    started_at: datetime
    finished_at: datetime
    references: tuple[EvidenceReference, ...] = Field(default_factory=tuple, max_length=50)
    diagnostics: tuple[ExecutionDiagnostic, ...] = Field(
        default_factory=tuple, max_length=100
    )
    summary: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def _timestamps_must_include_timezone(self) -> ExecutionOutcomeV1:
        if self.started_at.tzinfo is None or self.finished_at.tzinfo is None:
            raise ValueError("started_at e finished_at devem incluir timezone")
        return self

    @model_validator(mode="after")
    def _execution_cannot_finish_before_it_starts(self) -> ExecutionOutcomeV1:
        """Tempo impossivel e sinal de dado fabricado ou relogio quebrado.

        Nos dois casos, aceitar contaminaria qualquer analise temporal
        posterior — inclusive comparacao entre risco previsto e resultado real.
        """
        if self.finished_at < self.started_at:
            raise ValueError("finished_at nao pode ser anterior a started_at")
        return self

    @model_validator(mode="after")
    def _failure_requires_diagnostic(self) -> ExecutionOutcomeV1:
        """Falha sem diagnostico e um resultado que ninguem pode investigar."""
        if self.result is ExecutionResult.FAILED and not self.diagnostics:
            raise ValueError(
                "resultado 'failed' exige ao menos um diagnostico observado"
            )
        return self

    def duration_ms(self) -> float:
        """Duracao derivada pelo PedroCore, nunca aceita do produtor."""
        return (self.finished_at - self.started_at).total_seconds() * 1000.0

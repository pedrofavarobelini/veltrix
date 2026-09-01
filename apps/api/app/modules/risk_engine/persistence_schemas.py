"""Modelo de dados da persistência própria do Risk Engine (Stage R2).

Por que uma projeção, e não o objeto de domínio inteiro
-------------------------------------------------------

`PreExecutionRiskAnalysis` e `PostExecutionOutcome` são objetos ricos: carregam
avaliação fundacional, análise semântica, simulações, o relatório de execução
inteiro e a projeção de memória operacional. Guardar isso tal como está
transformaria o histórico de risco em um arquivo de tudo que já passou pelo
motor — incluindo texto livre que veio do consumidor.

O que o domínio Risk precisa para ter história própria é menor e mais duro:
**identificadores, versão de política, veredito, códigos de motivo, dimensões
numéricas, desvios observados e tempo**. Com isso já se responde à pergunta que
justifica a persistência — *o que foi previsto e o que de fato aconteceu* — sem
guardar o pedido original.

Privacidade por ausência de campo
---------------------------------

Não existe aqui `request_text`, `prompt`, `command`, `diff` ou payload bruto. A
proteção não é um sanitizador que roda depois: é o schema não ter onde colocar.
Um campo que não existe não vaza, não precisa ser limpo e não é esquecido na
revisão.

As dimensões de risco são números; os desvios são listas de códigos e de alvos
que o próprio motor já classificou. Nada disso é conteúdo do usuário.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RISK_PERSISTENCE_POLICY_VERSION = "risk-persistence-v1"

ShortText = Annotated[str, Field(min_length=1, max_length=128)]
Signature = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]

# Um registro de risco e feito de codigos e numeros. O teto existe para que
# nenhuma lista de `reason_codes` vire, na pratica, um campo de texto livre.
MAX_CODES = 64
MAX_CODE_LENGTH = 128


class RiskRecordKind(str, Enum):
    """O que o registro representa no ciclo do risco.

    A separacao entre previsto e observado e o motivo de existir persistencia
    propria: sao dois fatos distintos, produzidos em momentos distintos, e
    compara-los e o unico jeito de o motor aprender se acertou.
    """

    ANALYSIS = "analysis"
    OUTCOME = "outcome"


class PersistedRiskDimension(BaseModel):
    """Dimensao de risco reduzida ao que e comparavel entre execucoes."""

    model_config = ConfigDict(extra="forbid")

    dimension: ShortText
    score: float = Field(..., ge=0.0, le=1.0)
    severity: ShortText


def _validate_codes(values: list[str], field: str) -> list[str]:
    if len(values) > MAX_CODES:
        raise ValueError(f"{field} excede {MAX_CODES} entradas")
    for item in values:
        if len(item) > MAX_CODE_LENGTH:
            raise ValueError(f"{field} contém entrada longa demais; use códigos, não texto")
    return values


class RiskAnalysisRecord(BaseModel):
    """O que o motor PREVIU, antes de qualquer execução."""

    model_config = ConfigDict(extra="forbid")

    policy_version: Literal["risk-persistence-v1"] = RISK_PERSISTENCE_POLICY_VERSION
    kind: Literal[RiskRecordKind.ANALYSIS] = RiskRecordKind.ANALYSIS

    analysis_id: ShortText
    project_id: ShortText
    request_id: ShortText
    # Versao da politica que PRODUZIU a analise. Sem ela, comparar duas
    # analises de epocas diferentes seria comparar reguas diferentes.
    analysis_policy_version: ShortText

    severity: ShortText
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertainty: float = Field(..., ge=0.0, le=1.0)
    dimensions: tuple[PersistedRiskDimension, ...] = Field(default_factory=tuple)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    blast_radius_level: ShortText | None = None

    # Stage R3 — metrica de ALCANCE, opcional. `None` em registro gravado antes
    # do R3: forcar um numero neles inventaria um alcance que ninguem mediu.
    blast_metric_version: ShortText | None = None
    blast_boundary_breadth: int | None = Field(default=None, ge=0, le=8)
    blast_item_extent: int | None = Field(default=None, ge=0)
    blast_boundary_counts: dict[str, int] | None = None

    # Fingerprint do conteudo persistido. E o que permite reconhecer um replay
    # identico sem comparar objeto a objeto, e detectar conflito quando o mesmo
    # id chega com conteudo diferente.
    fingerprint: Signature
    created_at: datetime

    # Reafirmado no registro: guardar analise nao executa nada.
    target_operation_executed: Literal[False] = False

    @model_validator(mode="after")
    def _blast_metric_is_all_or_nothing(self) -> RiskAnalysisRecord:
        """Metrica presente ou ausente por inteiro.

        Amplitude preenchida com extensao nula descreveria um alcance
        impossivel — fronteiras tocadas sem nenhum item dentro delas.
        """
        present = [
            self.blast_metric_version,
            self.blast_boundary_breadth,
            self.blast_item_extent,
        ]
        if any(item is not None for item in present) and any(
            item is None for item in present
        ):
            raise ValueError("métrica de blast radius incompleta")
        if (
            self.blast_item_extent is not None
            and self.blast_boundary_breadth is not None
            and self.blast_item_extent < self.blast_boundary_breadth
        ):
            raise ValueError("item_extent não pode ser menor que boundary_breadth")
        return self

    @model_validator(mode="after")
    def _codes_are_codes(self) -> RiskAnalysisRecord:
        _validate_codes(list(self.reason_codes), "reason_codes")
        return self

    @model_validator(mode="after")
    def _created_at_requires_timezone(self) -> RiskAnalysisRecord:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at deve incluir timezone")
        return self


class RiskOutcomeRecord(BaseModel):
    """O que de fato ACONTECEU, depois da execução.

    `risk_analysis_id` e a correlacao que fecha o par previsto/observado. Sem
    ela o registro seria um fato solto, e o motor nunca saberia a qual previsao
    ele corresponde.
    """

    model_config = ConfigDict(extra="forbid")

    policy_version: Literal["risk-persistence-v1"] = RISK_PERSISTENCE_POLICY_VERSION
    kind: Literal[RiskRecordKind.OUTCOME] = RiskRecordKind.OUTCOME

    outcome_id: ShortText
    project_id: ShortText
    risk_analysis_id: ShortText
    contract_id: ShortText
    evidence_id: ShortText
    outcome_policy_version: ShortText

    effective_gate: ShortText
    status: Literal["passed", "failed", "blocked"]
    contract_valid: bool

    predicted_dimensions: dict[str, float] = Field(default_factory=dict)
    actual_issue_codes: tuple[str, ...] = Field(default_factory=tuple)
    predicted_risk_materialized: bool = False
    unpredicted_issue_detected: bool = False
    scope_deviation: tuple[str, ...] = Field(default_factory=tuple)

    fingerprint: Signature
    created_at: datetime

    target_operation_executed_by_risk_engine: Literal[False] = False

    @model_validator(mode="after")
    def _codes_are_codes(self) -> RiskOutcomeRecord:
        _validate_codes(list(self.actual_issue_codes), "actual_issue_codes")
        _validate_codes(list(self.scope_deviation), "scope_deviation")
        return self

    @model_validator(mode="after")
    def _created_at_requires_timezone(self) -> RiskOutcomeRecord:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at deve incluir timezone")
        return self


class RiskHistorySlice(BaseModel):
    """Recorte do historico proprio de um projeto.

    Existe para que o Historical Risk possa perguntar ao dominio Risk em vez de
    reconstruir tudo a partir de Report Memory — que era o acoplamento que o
    Stage R2 veio desfazer.
    """

    model_config = ConfigDict(extra="forbid")

    project_id: ShortText
    analyses: tuple[RiskAnalysisRecord, ...] = Field(default_factory=tuple)
    outcomes: tuple[RiskOutcomeRecord, ...] = Field(default_factory=tuple)

    @property
    def sample_size(self) -> int:
        return len(self.outcomes)

    def materialized_ratio(self) -> float | None:
        """Fracao de previsoes que se confirmaram.

        `None` quando nao ha outcome: zero seria uma afirmacao — "nenhum risco
        se materializou" — e a verdade e "ainda nao ha o que comparar".
        """
        if not self.outcomes:
            return None
        hits = sum(1 for item in self.outcomes if item.predicted_risk_materialized)
        return hits / len(self.outcomes)

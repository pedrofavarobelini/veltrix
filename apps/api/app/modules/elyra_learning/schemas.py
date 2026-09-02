"""Contrato `elyra-learning/v1` — submissao governada de candidato de treino.

Capability **estreita**: existe para duas operacoes e nada mais.

  - `submit_governed_candidate`
  - `revoke_governed_candidate`

O que esta capability NAO faz, por construcao: nao treina, nao inicia fine-tuning,
nao escreve em dataset generico, nao cria um segundo Candidate Store e nao aceita
conteudo bruto. Ela alimenta o **Dataset Foundation ja existente**.

Fail-closed absoluto: falta qualquer requisito — elegibilidade, consentimento de
treino, proveniencia, fingerprint, resultado de qualidade, versao de politica ou
versao de schema — e a submissao e **negada**, nao ajustada.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ELYRA_LEARNING_CONTRACT_VERSION = "elyra-learning/v1"
ELYRA_LEARNING_INPUT_SCHEMA_VERSION = "elyra-learning-input/v1"
ELYRA_LEARNING_OUTPUT_SCHEMA_VERSION = "elyra-learning-output/v1"
ELYRA_LEARNING_TASK_TYPE = "governed_learning_candidate_submission"
ELYRA_LEARNING_MESSAGE = "submeter_candidato_de_learning_governado"

ELYRA_LEARNING_POLICY_VERSION = "elyra-learning-policy/v1"
ELYRA_LEARNING_EXPORT_SCHEMA_VERSION = "elyra-learning-export/v1"

SUBMIT_OPERATION = "submit_governed_candidate"
REVOKE_OPERATION = "revoke_governed_candidate"


class StrictContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class EligibilityDeclarationV1(StrictContractModel):
    """A Elyra decide elegibilidade; o Veltrix exige a decisao explicita.

    `eligible` e `Literal[True]`: uma submissao inelegivel nao chega com
    `false` — ela simplesmente nao e submetida. Se chegar, e recusada.
    """

    eligible: Literal[True]
    policy_version: Literal["elyra-learning-policy/v1"] = Field(alias="policyVersion")
    evaluated_at: datetime = Field(alias="evaluatedAt")

    @model_validator(mode="after")
    def validate_timezone(self) -> "EligibilityDeclarationV1":
        if self.evaluated_at.tzinfo is None:
            raise ValueError("evaluatedAt precisa incluir timezone")
        return self


class TrainingConsentV1(StrictContractModel):
    """Consentimento de TREINO — proprio, separado de inferencia e de captura."""

    training_consent_granted: Literal[True] = Field(alias="trainingConsentGranted")
    consent_version: Literal["v1"] = Field(alias="consentVersion")
    granted_at: datetime = Field(alias="grantedAt")

    @model_validator(mode="after")
    def validate_timezone(self) -> "TrainingConsentV1":
        if self.granted_at.tzinfo is None:
            raise ValueError("grantedAt precisa incluir timezone")
        return self


class ProvenanceV1(StrictContractModel):
    """De onde o candidato veio, sem dizer de QUEM veio.

    Nao ha `user_id`, `session_id` nem `snapshot_id` legivel: a rastreabilidade
    ate a pessoa fica na Elyra, do lado que tem a base legal para mante-la.
    """

    source_kind: Literal["report_snapshot"] = Field(alias="sourceKind")
    source_schema_version: Literal["report_snapshot/v1"] = Field(
        alias="sourceSchemaVersion"
    )
    analytics_version: Literal["elyra-analytics/v1"] = Field(alias="analyticsVersion")
    export_schema_version: Literal["elyra-learning-export/v1"] = Field(
        alias="exportSchemaVersion"
    )
    produced_at: datetime = Field(alias="producedAt")

    @model_validator(mode="after")
    def validate_timezone(self) -> "ProvenanceV1":
        if self.produced_at.tzinfo is None:
            raise ValueError("producedAt precisa incluir timezone")
        return self


class QualityCheckV1(StrictContractModel):
    name: Literal[
        "minimum_days_with_data",
        "window_completeness",
        "no_free_text",
        "no_direct_identifier",
        "value_domains",
    ]
    passed: Literal[True]


class QualityResultV1(StrictContractModel):
    """Todos os gates de qualidade precisam ter passado, nominalmente."""

    passed: Literal[True]
    checks: list[QualityCheckV1] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_checks(self) -> "QualityResultV1":
        names = [check.name for check in self.checks]
        if len(set(names)) != len(names):
            raise ValueError("gate de qualidade duplicado")
        return self


class LearningMetricAggregateV1(StrictContractModel):
    """Agregado numerico. Sem texto livre, sem data, sem identificador."""

    mean: float | None
    delta: float | None
    trend: Literal["up", "down", "stable", "insufficient_data"]
    samples: int = Field(ge=0, le=90)

    @model_validator(mode="after")
    def validate_domain(self) -> "LearningMetricAggregateV1":
        # Sem amostra nao existe media nem tendencia: NULL nao e zero.
        if self.samples == 0:
            if self.mean is not None or self.delta is not None:
                raise ValueError("agregado sem amostra nao pode transportar valor")
            if self.trend != "insufficient_data":
                raise ValueError("agregado sem amostra exige insufficient_data")
        elif self.mean is None:
            raise ValueError("agregado com amostra precisa de media")
        return self


class SanitizedLearningPayloadV1(StrictContractModel):
    """O candidato em si. **Somente numeros e enums fechados.**

    Nao existe campo de texto neste modelo. Diario, transcricao, nome, conversa e
    saida do Veltrix nao tem onde caber — nao por politica, por **tipo**.
    """

    days_in_window: Literal[28, 56, 90] = Field(alias="daysInWindow")
    mood: LearningMetricAggregateV1
    anxiety: LearningMetricAggregateV1
    energy: LearningMetricAggregateV1
    sleep_duration_minutes: LearningMetricAggregateV1 = Field(
        alias="sleepDurationMinutes"
    )
    days_with_mood: int = Field(alias="daysWithMood", ge=0, le=90)
    days_with_anxiety: int = Field(alias="daysWithAnxiety", ge=0, le=90)
    days_with_energy: int = Field(alias="daysWithEnergy", ge=0, le=90)
    days_with_sleep: int = Field(alias="daysWithSleep", ge=0, le=90)
    cycle_enabled: bool = Field(alias="cycleEnabled")

    @model_validator(mode="after")
    def validate_counts(self) -> "SanitizedLearningPayloadV1":
        counts = (
            self.days_with_mood,
            self.days_with_anxiety,
            self.days_with_energy,
            self.days_with_sleep,
        )
        if any(count > self.days_in_window for count in counts):
            raise ValueError("contagem excede a janela declarada")

        pairs = (
            (self.mood, self.days_with_mood),
            (self.anxiety, self.days_with_anxiety),
            (self.energy, self.days_with_energy),
            (self.sleep_duration_minutes, self.days_with_sleep),
        )
        for aggregate, count in pairs:
            if aggregate.samples > count:
                raise ValueError("amostras do agregado excedem os dias com dado")

        # Dominios: emocionais 0-10, sono em minutos.
        for aggregate in (self.mood, self.anxiety, self.energy):
            if aggregate.mean is not None and not 0 <= aggregate.mean <= 10:
                raise ValueError("metrica emocional fora do dominio 0..10")
            if aggregate.delta is not None and not -10 <= aggregate.delta <= 10:
                raise ValueError("delta emocional fora do dominio")
        sleep = self.sleep_duration_minutes
        if sleep.mean is not None and not 0 <= sleep.mean <= 1440:
            raise ValueError("duracao de sono fora do dominio 0..1440")
        if sleep.delta is not None and not -1440 <= sleep.delta <= 1440:
            raise ValueError("delta de sono fora do dominio")
        return self


class ElyraLearningSubmissionV1(StrictContractModel):
    contract_version: Literal["elyra-learning/v1"] = Field(alias="contractVersion")
    input_schema_version: Literal["elyra-learning-input/v1"] = Field(
        alias="inputSchemaVersion"
    )
    operation: Literal["submit_governed_candidate"]
    eligibility: EligibilityDeclarationV1
    consent: TrainingConsentV1
    provenance: ProvenanceV1
    quality: QualityResultV1
    # Fingerprint do payload canonico sanitizado, calculado pela Elyra.
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload: SanitizedLearningPayloadV1

    @model_validator(mode="after")
    def validate_chronology(self) -> "ElyraLearningSubmissionV1":
        # O consentimento de treino precisa existir ANTES de o dado ser exportado.
        if self.consent.granted_at > self.provenance.produced_at:
            raise ValueError("consentimento de treino posterior ao dado exportado")
        return self


class ElyraLearningRevocationV1(StrictContractModel):
    contract_version: Literal["elyra-learning/v1"] = Field(alias="contractVersion")
    input_schema_version: Literal["elyra-learning-input/v1"] = Field(
        alias="inputSchemaVersion"
    )
    operation: Literal["revoke_governed_candidate"]
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason_code: Literal[
        "training_consent_revoked",
        "user_data_deleted",
        "eligibility_lost",
    ] = Field(alias="reasonCode")
    revoked_at: datetime = Field(alias="revokedAt")

    @model_validator(mode="after")
    def validate_timezone(self) -> "ElyraLearningRevocationV1":
        if self.revoked_at.tzinfo is None:
            raise ValueError("revokedAt precisa incluir timezone")
        return self


class ElyraLearningOutputV1(StrictContractModel):
    """Recibo da operacao. Nunca devolve o payload submetido."""

    contract_version: Literal["elyra-learning/v1"] = Field(alias="contractVersion")
    output_schema_version: Literal["elyra-learning-output/v1"] = Field(
        alias="outputSchemaVersion"
    )
    operation: Literal["submit_governed_candidate", "revoke_governed_candidate"]
    correlation_id: str = Field(alias="correlationId", min_length=3, max_length=128)
    candidate_id: str = Field(
        alias="candidateId", pattern=r"^training-candidate-[0-9a-f]{24}$"
    )
    lifecycle: Literal[
        "proposed", "authorized", "review_required", "excluded", "revoked", "consumed"
    ]
    duplicate: bool
    policy_version: Literal["elyra-learning-policy/v1"] = Field(alias="policyVersion")
    # Declaracao explicita: esta capability nao treina nada.
    training_started: Literal[False] = Field(alias="trainingStarted")
    model_weights_updated: Literal[False] = Field(alias="modelWeightsUpdated")

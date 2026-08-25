from __future__ import annotations

from datetime import date
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ELYRA_CONTRACT_VERSION = "elyra-textual/v1"
ELYRA_INPUT_SCHEMA_VERSION = "elyra-textual-input/v1"
ELYRA_OUTPUT_SCHEMA_VERSION = "elyra-textual-output/v1"
ELYRA_OPERATION = "interpret_deterministic_report"
ELYRA_TASK_TYPE = "wellbeing_report_interpretation"
ELYRA_CANONICAL_MESSAGE = "interpretar_relatorio_deterministico"

REPORT_SCHEMA_VERSION = "report_snapshot/v1"
ANALYTICS_VERSION = "elyra-analytics/v1"
CYCLE_HEURISTIC_VERSION = "elyra-cycle/v1"

ELYRA_DISCLAIMER = (
    "Conteúdo informativo e não clínico. Não constitui diagnóstico, prescrição "
    "ou afirmação causal e deve ser interpretado pela pessoa usuária."
)


class StrictContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class AnalyticsWindowV1(StrictContractModel):
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")

    @model_validator(mode="after")
    def validate_order(self) -> "AnalyticsWindowV1":
        if self.from_date > self.to_date:
            raise ValueError("janela analítica invertida")
        return self


class ComparisonV1(StrictContractModel):
    current: float | None
    previous: float | None
    delta: float | None
    trend: Literal["up", "down", "stable", "insufficient_data"]
    current_samples: int = Field(alias="currentSamples", ge=0, le=90)
    previous_samples: int = Field(alias="previousSamples", ge=0, le=90)


class DailyAnalyticsPointV1(StrictContractModel):
    date: date
    mood: float | None = Field(default=None, ge=0, le=10)
    anxiety: float | None = Field(default=None, ge=0, le=10)
    energy: float | None = Field(default=None, ge=0, le=10)
    sleep_hours: float | None = Field(default=None, alias="sleepHours", ge=0, le=24)
    mood_heatmap_bucket: int | None = Field(
        default=None,
        alias="moodHeatmapBucket",
        ge=0,
        le=4,
    )


class AnalyticsMetricsV1(StrictContractModel):
    mood: ComparisonV1
    anxiety: ComparisonV1
    energy: ComparisonV1
    sleep_duration_minutes: ComparisonV1 = Field(alias="sleepDurationMinutes")

    @model_validator(mode="after")
    def validate_metric_domains(self) -> "AnalyticsMetricsV1":
        for metric in (self.mood, self.anxiety, self.energy):
            values = (metric.current, metric.previous)
            if any(value is not None and not 0 <= value <= 10 for value in values):
                raise ValueError("métrica emocional fora do domínio 0..10")
            if metric.delta is not None and not -10 <= metric.delta <= 10:
                raise ValueError("delta emocional fora do domínio -10..10")

        sleep = self.sleep_duration_minutes
        if any(
            value is not None and not 0 <= value <= 1440
            for value in (sleep.current, sleep.previous)
        ):
            raise ValueError("duração de sono fora do domínio 0..1440 minutos")
        if sleep.delta is not None and not -1440 <= sleep.delta <= 1440:
            raise ValueError("delta de sono fora do domínio permitido")
        return self


class RegisteredBandV1(StrictContractModel):
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")

    @model_validator(mode="after")
    def validate_order(self) -> "RegisteredBandV1":
        if self.from_date > self.to_date:
            raise ValueError("faixa menstrual registrada invertida")
        return self


class CycleSummaryV1(StrictContractModel):
    enabled: bool
    registered_menstruation_days: int | None = Field(
        alias="registeredMenstruationDays",
        ge=0,
        le=90,
    )
    registered_bands: list[RegisteredBandV1] = Field(
        alias="registeredBands",
        max_length=20,
    )

    @model_validator(mode="after")
    def validate_opt_in_boundary(self) -> "CycleSummaryV1":
        if not self.enabled and (
            self.registered_menstruation_days is not None or self.registered_bands
        ):
            raise ValueError("ciclo desligado não pode enviar dados de ciclo")
        return self


class TemporalAssociationV1(StrictContractModel):
    status: Literal["available", "insufficient_data"]
    metric: Literal["energy"]
    before_period_mean: float | None = Field(
        alias="beforePeriodMean",
        ge=0,
        le=10,
    )
    other_days_mean: float | None = Field(alias="otherDaysMean", ge=0, le=10)
    delta: float | None = Field(default=None, ge=-10, le=10)
    before_period_samples: int = Field(alias="beforePeriodSamples", ge=0, le=90)
    other_days_samples: int = Field(alias="otherDaysSamples", ge=0, le=90)


class AssociationsV1(StrictContractModel):
    pre_period_energy: TemporalAssociationV1 = Field(alias="prePeriodEnergy")


class DataQualityV1(StrictContractModel):
    days_in_window: Literal[28, 56, 90] = Field(alias="daysInWindow")
    days_with_mood: int = Field(alias="daysWithMood", ge=0, le=90)
    days_with_anxiety: int = Field(alias="daysWithAnxiety", ge=0, le=90)
    days_with_energy: int = Field(alias="daysWithEnergy", ge=0, le=90)
    days_with_sleep: int = Field(alias="daysWithSleep", ge=0, le=90)

    @model_validator(mode="after")
    def validate_counts(self) -> "DataQualityV1":
        counts = (
            self.days_with_mood,
            self.days_with_anxiety,
            self.days_with_energy,
            self.days_with_sleep,
        )
        if any(value > self.days_in_window for value in counts):
            raise ValueError("contagem de qualidade excede a janela")
        return self


class AnalyticsReportV1(StrictContractModel):
    schema_version: Literal["report_snapshot/v1"] = Field(alias="schemaVersion")
    analytics_version: Literal["elyra-analytics/v1"] = Field(alias="analyticsVersion")
    cycle_heuristic_version: Literal["elyra-cycle/v1"] = Field(
        alias="cycleHeuristicVersion"
    )
    time_zone: str = Field(alias="timeZone", min_length=1, max_length=64)
    window: AnalyticsWindowV1
    previous_window: AnalyticsWindowV1 = Field(alias="previousWindow")
    series: list[DailyAnalyticsPointV1] = Field(max_length=90)
    metrics: AnalyticsMetricsV1
    cycle: CycleSummaryV1
    associations: AssociationsV1
    data_quality: DataQualityV1 = Field(alias="dataQuality")

    @field_validator("time_zone")
    @classmethod
    def validate_time_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("fuso IANA inválido") from exc
        return value

    @model_validator(mode="after")
    def validate_series_boundary(self) -> "AnalyticsReportV1":
        window_days = (self.window.to_date - self.window.from_date).days + 1
        previous_window_days = (
            self.previous_window.to_date - self.previous_window.from_date
        ).days + 1
        if window_days != self.data_quality.days_in_window:
            raise ValueError("janela atual incompatível com daysInWindow")
        if previous_window_days != self.data_quality.days_in_window:
            raise ValueError("janela anterior incompatível com daysInWindow")
        if self.previous_window.to_date >= self.window.from_date:
            raise ValueError("janela anterior deve terminar antes da janela atual")
        if len(self.series) != self.data_quality.days_in_window:
            raise ValueError("série precisa representar cada dia da janela")
        dates = [item.date for item in self.series]
        if dates != sorted(set(dates)):
            raise ValueError("datas da série precisam ser únicas e ordenadas")
        if any(item < self.window.from_date or item > self.window.to_date for item in dates):
            raise ValueError("série fora da janela declarada")
        return self


class ElyraTextualInputV1(StrictContractModel):
    contract_version: Literal["elyra-textual/v1"] = Field(alias="contractVersion")
    input_schema_version: Literal["elyra-textual-input/v1"] = Field(
        alias="inputSchemaVersion"
    )
    operation: Literal["interpret_deterministic_report"]
    ai_inference_consent: bool = Field(alias="aiInferenceConsent")
    report: AnalyticsReportV1


class ElyraObservationV1(StrictContractModel):
    category: Literal["metric", "data_quality", "temporal_association"]
    evidence_path: Literal[
        "metrics.mood",
        "metrics.anxiety",
        "metrics.energy",
        "metrics.sleepDurationMinutes",
        "dataQuality",
        "associations.prePeriodEnergy",
    ] = Field(alias="evidencePath")
    text: str = Field(min_length=1, max_length=320)


class ElyraSafetyDeclarationV1(StrictContractModel):
    diagnostic_claim: Literal[False] = Field(alias="diagnosticClaim")
    prescription: Literal[False]
    causal_claim: Literal[False] = Field(alias="causalClaim")
    facial_emotion_as_fact: Literal[False] = Field(alias="facialEmotionAsFact")
    fictitious_emotion_percentage: Literal[False] = Field(
        alias="fictitiousEmotionPercentage"
    )


class ElyraTextualOutputV1(StrictContractModel):
    contract_version: Literal["elyra-textual/v1"] = Field(alias="contractVersion")
    output_schema_version: Literal["elyra-textual-output/v1"] = Field(
        alias="outputSchemaVersion"
    )
    operation: Literal["interpret_deterministic_report"]
    correlation_id: str = Field(alias="correlationId", min_length=3, max_length=128)
    source_report_schema_version: Literal["report_snapshot/v1"] = Field(
        alias="sourceReportSchemaVersion"
    )
    source_analytics_version: Literal["elyra-analytics/v1"] = Field(
        alias="sourceAnalyticsVersion"
    )
    language: Literal["pt-BR"]
    summary: str = Field(min_length=1, max_length=1000)
    observations: list[ElyraObservationV1] = Field(min_length=1, max_length=5)
    limitations: list[str] = Field(min_length=2, max_length=5)
    disclaimer: Literal[
        "Conteúdo informativo e não clínico. Não constitui diagnóstico, prescrição "
        "ou afirmação causal e deve ser interpretado pela pessoa usuária."
    ]
    safety: ElyraSafetyDeclarationV1

    @field_validator("limitations")
    @classmethod
    def validate_limitations(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or len(value) > 320 for value in values):
            raise ValueError("limitação vazia ou extensa demais")
        return values

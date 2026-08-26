"""Contrato `elyra-multimodal/v1`.

Capability PROPRIA do consumer Elyra, separada de `elyra-textual/v1`. O PedroCore
nunca recebe midia bruta, caminho de Storage, credencial ou identificador de
pessoa usuaria: a fronteira aceita apenas transcricao consentida, sinais
observaveis ja calculados pela Elyra e metadados minimizados.

Regra inviolavel: sinal observavel NAO e emocao. O vocabulario e um `Literal`
fechado justamente para que nenhum campo de emocao, diagnostico ou percentual
afetivo atravesse a fronteira, nem por extensao futura acidental.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ELYRA_MULTIMODAL_CONTRACT_VERSION = "elyra-multimodal/v1"
ELYRA_MULTIMODAL_INPUT_SCHEMA_VERSION = "elyra-multimodal-input/v1"
ELYRA_MULTIMODAL_OUTPUT_SCHEMA_VERSION = "elyra-multimodal-output/v1"
ELYRA_MULTIMODAL_OPERATION = "interpret_observable_session_signals"
ELYRA_MULTIMODAL_TASK_TYPE = "multimodal_session_signal_interpretation"
ELYRA_MULTIMODAL_CANONICAL_MESSAGE = "interpretar_sinais_observaveis_de_sessao"

SIGNALS_SCHEMA_VERSION = "multimodal_signals/v1"
FEATURE_EXTRACTOR_VERSION = "elyra-signals/v1"

ELYRA_MULTIMODAL_DISCLAIMER = (
    "Conteúdo informativo e não clínico. Sinais observáveis descrevem como a "
    "sessão foi registrada, não determinam emoção, não constituem diagnóstico "
    "ou prescrição e devem ser interpretados pela pessoa usuária."
)

# Vocabulario fechado de sinais observaveis. Cada nome corresponde a uma medida
# deterministica extraida on-device pela Elyra (ADR-0005), sem modelo de ML,
# sem inferencia afetiva e sem norma populacional.
ObservableSignalName = Literal[
    "speech_rate",
    "pause_count",
    "pause_total_duration",
    "pause_mean_duration",
    "vocal_variation",
    "movement_frequency",
]

SIGNAL_UNITS: dict[str, str] = {
    "speech_rate": "words_per_minute",
    "pause_count": "count",
    "pause_total_duration": "milliseconds",
    "pause_mean_duration": "milliseconds",
    "vocal_variation": "index",
    "movement_frequency": "index",
}

# Limite superior por sinal. Valor fora do dominio e recusado antes de qualquer
# dispatch: um `speech_rate` de 10.000 wpm nao e interpretado, e rejeitado.
SIGNAL_MAXIMUM: dict[str, float] = {
    "speech_rate": 400.0,
    "pause_count": 1000.0,
    "pause_total_duration": 3_600_000.0,
    "pause_mean_duration": 600_000.0,
    "vocal_variation": 1.0,
    "movement_frequency": 1.0,
}

AUDIO_SIGNAL_NAMES = frozenset(
    {
        "speech_rate",
        "pause_count",
        "pause_total_duration",
        "pause_mean_duration",
        "vocal_variation",
    }
)


class StrictContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ObservableSignalV1(StrictContractModel):
    """Um sinal observavel comparado somente a baseline pessoal do usuario."""

    name: ObservableSignalName
    value: float | None = Field(default=None, ge=0)
    unit: Literal["words_per_minute", "count", "milliseconds", "index"]
    personal_baseline_mean: float | None = Field(
        default=None, alias="personalBaselineMean", ge=0
    )
    personal_baseline_samples: int = Field(
        alias="personalBaselineSamples", ge=0, le=90
    )
    delta_vs_personal_baseline: float | None = Field(
        default=None, alias="deltaVsPersonalBaseline"
    )
    status: Literal["available", "insufficient_baseline", "not_captured"]

    @model_validator(mode="after")
    def validate_signal(self) -> "ObservableSignalV1":
        if self.unit != SIGNAL_UNITS[self.name]:
            raise ValueError("unidade incompatível com o sinal declarado")

        maximum = SIGNAL_MAXIMUM[self.name]
        if self.value is not None and self.value > maximum:
            raise ValueError("valor do sinal fora do domínio permitido")
        if (
            self.personal_baseline_mean is not None
            and self.personal_baseline_mean > maximum
        ):
            raise ValueError("baseline pessoal fora do domínio permitido")
        if self.delta_vs_personal_baseline is not None and not (
            -maximum <= self.delta_vs_personal_baseline <= maximum
        ):
            raise ValueError("delta vs baseline fora do domínio permitido")

        # `not_captured` significa ausencia de captura: NULL nao e zero.
        if self.status == "not_captured":
            if self.value is not None:
                raise ValueError("sinal não capturado não pode transportar valor")
        elif self.value is None:
            raise ValueError("sinal capturado precisa de valor")

        # Sem baseline nao existe comparacao: delta so acompanha `available`.
        if self.status == "available":
            if self.personal_baseline_mean is None or self.personal_baseline_samples < 1:
                raise ValueError("sinal disponível exige baseline pessoal real")
        elif self.delta_vs_personal_baseline is not None:
            raise ValueError("delta exige baseline pessoal disponível")
        return self


class TranscriptDigestV1(StrictContractModel):
    """Transcricao consentida. So atravessa quando ha consentimento proprio."""

    language: Literal["pt-BR"]
    text: str = Field(min_length=1, max_length=20_000)
    word_count: int = Field(alias="wordCount", ge=0, le=20_000)
    voiced_duration_ms: int = Field(alias="voicedDurationMs", ge=0, le=3_600_000)
    truncated: bool


class MultimodalSessionSignalsV1(StrictContractModel):
    """Projecao minimizada da sessao. Sem id de usuario, sem caminho de midia."""

    signals_schema_version: Literal["multimodal_signals/v1"] = Field(
        alias="signalsSchemaVersion"
    )
    feature_extractor_version: Literal["elyra-signals/v1"] = Field(
        alias="featureExtractorVersion"
    )
    session_kind: Literal["guided", "free", "deep_checkin"] = Field(alias="sessionKind")
    captured_resources: list[Literal["screen", "camera", "microphone"]] = Field(
        alias="capturedResources", min_length=1, max_length=3
    )
    duration_ms: int = Field(alias="durationMs", ge=0, le=3_600_000)
    transcript: TranscriptDigestV1 | None = None
    signals: list[ObservableSignalV1] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def validate_session(self) -> "MultimodalSessionSignalsV1":
        if len(set(self.captured_resources)) != len(self.captured_resources):
            raise ValueError("recurso de captura duplicado")

        names = [signal.name for signal in self.signals]
        if len(set(names)) != len(names):
            raise ValueError("sinal observável duplicado")

        # Sinal calculado sem a captura correspondente seria dado fabricado.
        has_microphone = "microphone" in self.captured_resources
        has_camera = "camera" in self.captured_resources
        for signal in self.signals:
            if signal.status == "not_captured":
                continue
            if signal.name in AUDIO_SIGNAL_NAMES and not has_microphone:
                raise ValueError("sinal de áudio sem captura de microfone")
            if signal.name == "movement_frequency" and not has_camera:
                raise ValueError("sinal de movimento sem captura de câmera")

        if self.transcript is not None:
            if not has_microphone:
                raise ValueError("transcrição sem captura de microfone")
            if self.transcript.voiced_duration_ms > self.duration_ms:
                raise ValueError("duração falada excede a duração da sessão")
        return self


class ElyraMultimodalInputV1(StrictContractModel):
    contract_version: Literal["elyra-multimodal/v1"] = Field(alias="contractVersion")
    input_schema_version: Literal["elyra-multimodal-input/v1"] = Field(
        alias="inputSchemaVersion"
    )
    operation: Literal["interpret_observable_session_signals"]
    ai_inference_consent: bool = Field(alias="aiInferenceConsent")
    multimodal_analysis_consent: bool = Field(alias="multimodalAnalysisConsent")
    transcript_analysis_consent: bool = Field(alias="transcriptAnalysisConsent")
    session: MultimodalSessionSignalsV1

    @model_validator(mode="after")
    def validate_consent_boundary(self) -> "ElyraMultimodalInputV1":
        # Fail-closed: transcricao sem consentimento proprio nunca atravessa,
        # mesmo que a inferencia de IA esteja consentida.
        if self.session.transcript is not None and not self.transcript_analysis_consent:
            raise ValueError("transcrição enviada sem consentimento de transcrição")
        return self


class ElyraMultimodalObservationV1(StrictContractModel):
    category: Literal["observable_signal", "transcript", "capture_quality"]
    evidence_path: Literal[
        "signals.speech_rate",
        "signals.pause_count",
        "signals.pause_total_duration",
        "signals.pause_mean_duration",
        "signals.vocal_variation",
        "signals.movement_frequency",
        "transcript",
        "captureQuality",
    ] = Field(alias="evidencePath")
    text: str = Field(min_length=1, max_length=320)


class ElyraMultimodalSafetyV1(StrictContractModel):
    diagnostic_claim: Literal[False] = Field(alias="diagnosticClaim")
    prescription: Literal[False]
    causal_claim: Literal[False] = Field(alias="causalClaim")
    facial_emotion_as_fact: Literal[False] = Field(alias="facialEmotionAsFact")
    fictitious_emotion_percentage: Literal[False] = Field(
        alias="fictitiousEmotionPercentage"
    )
    # Especificos da fronteira multimodal.
    emotion_inferred_from_signal: Literal[False] = Field(
        alias="emotionInferredFromSignal"
    )
    raw_media_accessed: Literal[False] = Field(alias="rawMediaAccessed")
    population_norm_comparison: Literal[False] = Field(alias="populationNormComparison")


class ElyraMultimodalOutputV1(StrictContractModel):
    contract_version: Literal["elyra-multimodal/v1"] = Field(alias="contractVersion")
    output_schema_version: Literal["elyra-multimodal-output/v1"] = Field(
        alias="outputSchemaVersion"
    )
    operation: Literal["interpret_observable_session_signals"]
    correlation_id: str = Field(alias="correlationId", min_length=3, max_length=128)
    source_signals_schema_version: Literal["multimodal_signals/v1"] = Field(
        alias="sourceSignalsSchemaVersion"
    )
    source_feature_extractor_version: Literal["elyra-signals/v1"] = Field(
        alias="sourceFeatureExtractorVersion"
    )
    language: Literal["pt-BR"]
    summary: str = Field(min_length=1, max_length=1000)
    observations: list[ElyraMultimodalObservationV1] = Field(min_length=1, max_length=6)
    limitations: list[str] = Field(min_length=2, max_length=5)
    disclaimer: Literal[
        "Conteúdo informativo e não clínico. Sinais observáveis descrevem como a "
        "sessão foi registrada, não determinam emoção, não constituem diagnóstico "
        "ou prescrição e devem ser interpretados pela pessoa usuária."
    ]
    safety: ElyraMultimodalSafetyV1

    @model_validator(mode="after")
    def validate_limitations(self) -> "ElyraMultimodalOutputV1":
        if any(not value.strip() or len(value) > 320 for value in self.limitations):
            raise ValueError("limitação vazia ou extensa demais")
        return self

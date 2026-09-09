"""Contrato `elyra-multimodal/v2`.

Arquivo separado do `schemas.py` de proposito: a V1 continua valida, continua
sendo aceita e **nao e tocada aqui**. Sessoes ja interpretadas sob a V1 nao
podem passar a ser recusadas porque a Elyra evoluiu - um consumidor que quebra
o passado ao ganhar um campo nao e um contrato, e uma armadilha.

## O que a V2 acrescenta

A V1 conhecia seis sinais, todos derivados de audio ou de diferenca de pixel.
Entre a Era 4 e a Stage 22-V a Elyra passou a produzir:

- cinco sinais visuais (cabeca, corpo, maos), derivados de geometria;
- cobertura por modalidade - `PARTIAL_CAPTURE != FULL_CAPTURE`;
- autorrelato da propria pessoa, que e outra camada de verdade;
- janelas temporais, para dizer *quando* dentro da sessao;
- consentimento de analise visual, separado do de camera;
- confianca declarada da interpretacao;
- proveniencia da transcricao.

Nenhum desses campos cabia na V1 sem mentir por omissao.

## O que a V2 NAO acrescenta

Nada que aproxime a fronteira de emocao, diagnostico ou midia. O vocabulario
segue fechado, e os sinais visuais descrevem **a medida** - "frequencia de
movimento da cabeca" e uma contagem normalizada de amostras em que a orientacao
mudou acima de um limiar. Nao e agitacao, nao e ansiedade, nao e engajamento, e
por isso nenhuma dessas palavras tem nome nesta lista.

O Veltrix continua sem receber audio, video, frame, imagem, landmark, caminho de
Storage ou identificador de pessoa.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.modules.elyra_multimodal.schemas import (
    ELYRA_MULTIMODAL_DISCLAIMER,
    ELYRA_MULTIMODAL_OPERATION,
    StrictContractModel,
)

ELYRA_MULTIMODAL_CONTRACT_VERSION_V2 = "elyra-multimodal/v2"
ELYRA_MULTIMODAL_INPUT_SCHEMA_VERSION_V2 = "elyra-multimodal-input/v2"
ELYRA_MULTIMODAL_OUTPUT_SCHEMA_VERSION_V2 = "elyra-multimodal-output/v2"

SIGNALS_SCHEMA_VERSION_V2 = "multimodal_signals/v2"
FEATURE_EXTRACTOR_VERSION_V2 = "elyra-signals/v3"

# Sinais visuais: derivados de geometria corporal, e so existem com camera E
# consentimento de analise visual. Os dois, e nao um.
VISUAL_SIGNAL_NAMES = frozenset(
    {
        "head_movement_frequency",
        "head_motion_amplitude",
        "body_movement_frequency",
        "body_motion_amplitude",
        "hand_movement_frequency",
    }
)

ObservableSignalNameV2 = Literal[
    "speech_rate",
    "pause_count",
    "pause_total_duration",
    "pause_mean_duration",
    "vocal_variation",
    # Mede mudanca de pixel na cena inteira. Continua existindo e NAO e
    # substituido pelos visuais: e outra conta, e sessoes antigas dependem dele.
    "movement_frequency",
    "head_movement_frequency",
    "head_motion_amplitude",
    "body_movement_frequency",
    "body_motion_amplitude",
    "hand_movement_frequency",
]

SIGNAL_UNITS_V2: dict[str, str] = {
    "speech_rate": "words_per_minute",
    "pause_count": "count",
    "pause_total_duration": "milliseconds",
    "pause_mean_duration": "milliseconds",
    "vocal_variation": "index",
    "movement_frequency": "index",
    "head_movement_frequency": "index",
    "head_motion_amplitude": "index",
    "body_movement_frequency": "index",
    "body_motion_amplitude": "index",
    "hand_movement_frequency": "index",
}

SIGNAL_MAXIMUM_V2: dict[str, float] = {
    "speech_rate": 400.0,
    "pause_count": 1000.0,
    "pause_total_duration": 3_600_000.0,
    "pause_mean_duration": 600_000.0,
    "vocal_variation": 1.0,
    "movement_frequency": 1.0,
    "head_movement_frequency": 1.0,
    "head_motion_amplitude": 1.0,
    "body_movement_frequency": 1.0,
    "body_motion_amplitude": 1.0,
    "hand_movement_frequency": 1.0,
}

AUDIO_SIGNAL_NAMES_V2 = frozenset(
    {
        "speech_rate",
        "pause_count",
        "pause_total_duration",
        "pause_mean_duration",
        "vocal_variation",
    }
)

# De qual modalidade visual cada sinal visual vem. Um sinal de cabeca precisa da
# cobertura de `visual_face`, e nao da cobertura da camera: sem isso, um sinal
# derivado de 6 minutos de rosto viajaria carregando `camera = full`.
VISUAL_SIGNAL_MODALITY: dict[str, str] = {
    "head_movement_frequency": "visual_face",
    "head_motion_amplitude": "visual_face",
    "body_movement_frequency": "visual_body",
    "body_motion_amplitude": "visual_body",
    "hand_movement_frequency": "visual_hands",
}

VISUAL_MODALITIES = frozenset({"visual_face", "visual_body", "visual_hands"})

ObservationModality = Literal[
    "screen",
    "camera",
    "microphone",
    "visual_face",
    "visual_body",
    "visual_hands",
]

CAPTURE_ABSENCE_REASONS = frozenset(
    {"not_requested", "unsupported", "denied", "cancelled", "error", "not_observed"}
)
CAPTURE_PARTIAL_REASONS = frozenset(
    {"interrupted", "recording_capped", "out_of_frame", "analysis_started_late"}
)

CaptureCoverageReason = Literal[
    "not_requested",
    "unsupported",
    "denied",
    "cancelled",
    "error",
    "not_observed",
    "interrupted",
    "recording_capped",
    "out_of_frame",
    "analysis_started_late",
]

WindowedSignalName = Literal[
    "pause_count",
    "pause_total_duration",
    "pause_mean_duration",
    "vocal_variation",
    "movement_frequency",
    "head_movement_frequency",
    "head_motion_amplitude",
    "body_movement_frequency",
    "body_motion_amplitude",
    "hand_movement_frequency",
]


class CaptureCoverageV2(StrictContractModel):
    """Quanto tempo a modalidade esteve ativa dentro da sessao.

    Nao e qualidade de imagem, de som ou de rede. Chamar de "qualidade"
    convidaria a leitura de que 100% de cobertura significa boa captura.
    """

    modality: ObservationModality
    outcome: Literal["full", "partial", "absent"]
    reason: CaptureCoverageReason | None = None
    coverage_ms: int = Field(alias="coverageMs", ge=0, le=3_600_000)
    session_duration_ms: int = Field(alias="sessionDurationMs", ge=0, le=3_600_000)

    @model_validator(mode="after")
    def validate_coverage(self) -> "CaptureCoverageV2":
        if self.coverage_ms > self.session_duration_ms:
            raise ValueError("cobertura maior que a duracao da sessao")

        if self.outcome == "full":
            if self.reason is not None:
                raise ValueError("cobertura completa nao tem motivo")
            return self

        if self.reason is None:
            raise ValueError("cobertura incompleta exige motivo declarado")

        if self.outcome == "absent":
            if self.reason not in CAPTURE_ABSENCE_REASONS:
                raise ValueError("motivo incompativel com ausencia de captura")
            # Ausencia nao carrega tempo: coverageMs positivo afirmaria captura.
            if self.coverage_ms != 0:
                raise ValueError("modalidade ausente nao pode ter cobertura")
            return self

        if self.reason not in CAPTURE_PARTIAL_REASONS:
            raise ValueError("motivo incompativel com cobertura parcial")
        return self


class ObservableSignalV2(StrictContractModel):
    """Um sinal observavel comparado somente a baseline pessoal do usuario."""

    name: ObservableSignalNameV2
    value: float | None = Field(default=None, ge=0)
    unit: Literal["words_per_minute", "count", "milliseconds", "index"]
    personal_baseline_mean: float | None = Field(
        default=None, alias="personalBaselineMean", ge=0
    )
    personal_baseline_samples: int = Field(alias="personalBaselineSamples", ge=0, le=90)
    delta_vs_personal_baseline: float | None = Field(
        default=None, alias="deltaVsPersonalBaseline"
    )
    status: Literal["available", "insufficient_baseline", "not_captured"]
    # `None` significa linha anterior a Era 4, e NAO "cobertura completa". Ler
    # ausencia como completude reintroduziria exatamente o engano que a coluna
    # existe para desfazer.
    coverage: CaptureCoverageV2 | None = None

    @model_validator(mode="after")
    def validate_signal(self) -> "ObservableSignalV2":
        if self.unit != SIGNAL_UNITS_V2[self.name]:
            raise ValueError("unidade incompativel com o sinal declarado")

        maximum = SIGNAL_MAXIMUM_V2[self.name]
        if self.value is not None and self.value > maximum:
            raise ValueError("valor do sinal fora do dominio permitido")
        if (
            self.personal_baseline_mean is not None
            and self.personal_baseline_mean > maximum
        ):
            raise ValueError("baseline pessoal fora do dominio permitido")
        if self.delta_vs_personal_baseline is not None and not (
            -maximum <= self.delta_vs_personal_baseline <= maximum
        ):
            raise ValueError("delta vs baseline fora do dominio permitido")

        # `not_captured` significa ausencia de captura: NULL nao e zero.
        if self.status == "not_captured":
            if self.value is not None:
                raise ValueError("sinal nao capturado nao pode transportar valor")
        elif self.value is None:
            raise ValueError("sinal capturado precisa de valor")

        if self.status == "available":
            if (
                self.personal_baseline_mean is None
                or self.personal_baseline_samples < 1
            ):
                raise ValueError("sinal disponivel exige baseline pessoal real")
        elif self.delta_vs_personal_baseline is not None:
            raise ValueError("delta exige baseline pessoal disponivel")
        return self


class TranscriptProvenanceV2(StrictContractModel):
    """De onde veio o texto.

    O Veltrix precisa saber a natureza da fonte para nao tratar saida de ASR
    como fala perfeita. Isto e proveniencia, e nao acuracia: saber que o texto
    veio do whisper-base q8 nao torna o texto verdadeiro.

    Nenhum campo aqui e taxa de erro. WER e CER sao medidas de QA privadas da
    Elyra e nao atravessam a fronteira - atravessa-las as transformaria em
    atributo da sessao de alguem.
    """

    engine: Literal[
        "native_speech_recognition", "local_whisper", "on_device_speech_api"
    ]
    model: str | None = Field(default=None, min_length=1, max_length=120)
    quantization: str | None = Field(default=None, min_length=1, max_length=40)
    runtime: str | None = Field(default=None, min_length=1, max_length=60)
    runtime_version: str | None = Field(
        default=None, alias="runtimeVersion", min_length=1, max_length=40
    )
    vad: str | None = Field(default=None, min_length=1, max_length=60)
    # Preenchido a partir do Block 3: transcricao revisada por quem falou nao e
    # a mesma coisa que saida crua de ASR, e o Veltrix nao pode confundi-las.
    human_corrected: bool = Field(default=False, alias="humanCorrected")


class TranscriptDigestV2(StrictContractModel):
    """Transcricao consentida. So atravessa quando ha consentimento proprio."""

    language: Literal["pt-BR"]
    text: str = Field(min_length=1, max_length=20_000)
    word_count: int = Field(alias="wordCount", ge=0, le=20_000)
    voiced_duration_ms: int = Field(alias="voicedDurationMs", ge=0, le=3_600_000)
    truncated: bool
    provenance: TranscriptProvenanceV2 | None = None


class SessionSelfReportV2(StrictContractModel):
    """O que a pessoa relatou sobre a propria sessao.

    SELF_REPORTED, e nunca AI_INFERRED_EMOTION. A distincao e o que permite
    dizer *"nas sessoes em que voce relatou ansiedade elevada..."* sem nunca
    poder dizer *"fala rapida = ansiedade"*.

    Ausencia e `None`, nunca `0` e nunca "neutro".
    """

    mood: int | None = Field(default=None, ge=0, le=10)
    # Autorrelatada. O sistema nao mede ansiedade - ele registra o relato.
    perceived_anxiety: int | None = Field(
        default=None, alias="perceivedAnxiety", ge=0, le=10
    )
    energy: int | None = Field(default=None, ge=0, le=10)

    @model_validator(mode="after")
    def validate_self_report(self) -> "SessionSelfReportV2":
        if self.mood is None and self.perceived_anxiety is None and self.energy is None:
            # Autorrelato vazio nao e autorrelato.
            raise ValueError("autorrelato sem nenhum valor")
        return self


class SignalWindowV2(StrictContractModel):
    """Uma janela temporal derivada, em offset relativo ao inicio da sessao."""

    signal: WindowedSignalName
    start_offset_ms: int = Field(alias="startOffsetMs", ge=0, le=3_600_000)
    end_offset_ms: int = Field(alias="endOffsetMs", ge=0, le=3_600_000)
    value: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_window(self) -> "SignalWindowV2":
        if self.end_offset_ms < self.start_offset_ms:
            raise ValueError("janela termina antes de comecar")
        return self


class MultimodalSessionSignalsV2(StrictContractModel):
    """Projecao minimizada da sessao. Sem id de usuario, sem caminho de midia."""

    signals_schema_version: Literal["multimodal_signals/v2"] = Field(
        alias="signalsSchemaVersion"
    )
    feature_extractor_version: Literal["elyra-signals/v3"] = Field(
        alias="featureExtractorVersion"
    )
    session_kind: Literal["guided", "free", "deep_checkin"] = Field(alias="sessionKind")
    captured_resources: list[Literal["screen", "camera", "microphone"]] = Field(
        alias="capturedResources", min_length=1, max_length=3
    )
    duration_ms: int = Field(alias="durationMs", ge=0, le=3_600_000)
    # Ate seis linhas: as tres modalidades de captura mais as tres visuais.
    modality_coverage: list[CaptureCoverageV2] = Field(
        alias="modalityCoverage", min_length=1, max_length=6
    )
    self_report: SessionSelfReportV2 | None = Field(default=None, alias="selfReport")
    # Dez sinais janelaveis numa sessao de 60 minutos sao 600 janelas.
    windows: list[SignalWindowV2] = Field(default_factory=list, max_length=1200)
    transcript: TranscriptDigestV2 | None = None
    signals: list[ObservableSignalV2] = Field(min_length=1, max_length=11)

    @model_validator(mode="after")
    def validate_session(self) -> "MultimodalSessionSignalsV2":
        if len(set(self.captured_resources)) != len(self.captured_resources):
            raise ValueError("recurso de captura duplicado")

        names = [signal.name for signal in self.signals]
        if len(set(names)) != len(names):
            raise ValueError("sinal observavel duplicado")

        # Sinal calculado sem a captura correspondente seria dado fabricado.
        has_microphone = "microphone" in self.captured_resources
        has_camera = "camera" in self.captured_resources
        for signal in self.signals:
            if signal.status == "not_captured":
                continue
            if signal.name in AUDIO_SIGNAL_NAMES_V2 and not has_microphone:
                raise ValueError("sinal de audio sem captura de microfone")
            if signal.name == "movement_frequency" and not has_camera:
                raise ValueError("sinal de movimento sem captura de camera")
            if signal.name in VISUAL_SIGNAL_NAMES and not has_camera:
                raise ValueError("sinal visual sem captura de camera")

        # Um sinal visual precisa da cobertura da SUA modalidade, e nao da
        # cobertura da camera.
        declared = {coverage.modality for coverage in self.modality_coverage}
        for signal in self.signals:
            if signal.status == "not_captured":
                continue
            modality = VISUAL_SIGNAL_MODALITY.get(signal.name)
            if modality and modality not in declared:
                raise ValueError(
                    "sinal visual sem cobertura da modalidade que o produziu"
                )

        if self.transcript is not None:
            if not has_microphone:
                raise ValueError("transcricao sem captura de microfone")
            if self.transcript.voiced_duration_ms > self.duration_ms:
                raise ValueError("duracao falada excede a duracao da sessao")

        for window in self.windows:
            if window.end_offset_ms > self.duration_ms:
                raise ValueError("janela ultrapassa a duracao da sessao")
        return self


class ElyraMultimodalInputV2(StrictContractModel):
    contract_version: Literal["elyra-multimodal/v2"] = Field(alias="contractVersion")
    input_schema_version: Literal["elyra-multimodal-input/v2"] = Field(
        alias="inputSchemaVersion"
    )
    operation: Literal["interpret_observable_session_signals"]
    ai_inference_consent: bool = Field(alias="aiInferenceConsent")
    multimodal_analysis_consent: bool = Field(alias="multimodalAnalysisConsent")
    transcript_analysis_consent: bool = Field(alias="transcriptAnalysisConsent")
    # Consentimento ESPECIFICO de analise visual. Nao e derivado de
    # camera_consent nem de multimodalAnalysisConsent: ligar a camera e gravar
    # imagem; analise visual e extrair geometria corporal dela.
    visual_analysis_consent: bool = Field(alias="visualAnalysisConsent")
    session: MultimodalSessionSignalsV2

    @model_validator(mode="after")
    def validate_consent_boundary(self) -> "ElyraMultimodalInputV2":
        if self.session.transcript is not None and not self.transcript_analysis_consent:
            raise ValueError("transcricao enviada sem consentimento de transcricao")

        if self.visual_analysis_consent:
            return self

        # Sem consentimento visual, nada derivado de landmark atravessa: nem
        # sinal, nem janela, nem a linha de cobertura que diria por quanto tempo
        # o corpo da pessoa esteve observavel. A cobertura parece inofensiva e
        # nao e: "rosto observavel por 22 dos 30 minutos" e uma observacao sobre
        # o corpo de alguem que nao autorizou observacao do corpo.
        if any(signal.name in VISUAL_SIGNAL_NAMES for signal in self.session.signals):
            raise ValueError("sinal visual enviado sem consentimento de analise visual")
        if any(window.signal in VISUAL_SIGNAL_NAMES for window in self.session.windows):
            raise ValueError("janela visual enviada sem consentimento de analise visual")
        if any(
            coverage.modality in VISUAL_MODALITIES
            for coverage in self.session.modality_coverage
        ):
            raise ValueError(
                "cobertura visual enviada sem consentimento de analise visual"
            )
        return self


EvidencePathV2 = Literal[
    "signals.speech_rate",
    "signals.pause_count",
    "signals.pause_total_duration",
    "signals.pause_mean_duration",
    "signals.vocal_variation",
    "signals.movement_frequency",
    "signals.head_movement_frequency",
    "signals.head_motion_amplitude",
    "signals.body_movement_frequency",
    "signals.body_motion_amplitude",
    "signals.hand_movement_frequency",
    "transcript",
    "captureQuality",
    "coverage",
    "timeline",
    "selfReport",
]


class ElyraMultimodalObservationV2(StrictContractModel):
    category: Literal["observable_signal", "transcript", "capture_quality"]
    evidence_path: EvidencePathV2 = Field(alias="evidencePath")
    text: str = Field(min_length=1, max_length=320)


class ElyraMultimodalSafetyV2(StrictContractModel):
    diagnostic_claim: Literal[False] = Field(alias="diagnosticClaim")
    prescription: Literal[False]
    causal_claim: Literal[False] = Field(alias="causalClaim")
    facial_emotion_as_fact: Literal[False] = Field(alias="facialEmotionAsFact")
    fictitious_emotion_percentage: Literal[False] = Field(
        alias="fictitiousEmotionPercentage"
    )
    emotion_inferred_from_signal: Literal[False] = Field(
        alias="emotionInferredFromSignal"
    )
    raw_media_accessed: Literal[False] = Field(alias="rawMediaAccessed")
    population_norm_comparison: Literal[False] = Field(alias="populationNormComparison")
    # Autorrelato nunca e apresentado como correcao do sinal, nem o inverso.
    self_report_contradicted_by_signal: Literal[False] = Field(
        alias="selfReportContradictedBySignal"
    )


class ElyraMultimodalOutputV2(StrictContractModel):
    contract_version: Literal["elyra-multimodal/v2"] = Field(alias="contractVersion")
    output_schema_version: Literal["elyra-multimodal-output/v2"] = Field(
        alias="outputSchemaVersion"
    )
    operation: Literal["interpret_observable_session_signals"]
    correlation_id: str = Field(alias="correlationId", min_length=3, max_length=128)
    source_signals_schema_version: Literal["multimodal_signals/v2"] = Field(
        alias="sourceSignalsSchemaVersion"
    )
    source_feature_extractor_version: Literal["elyra-signals/v3"] = Field(
        alias="sourceFeatureExtractorVersion"
    )
    language: Literal["pt-BR"]
    summary: str = Field(min_length=1, max_length=1000)
    # Confianca ALTERA o que se afirma; ela nao acompanha uma frase categorica
    # como ressalva.
    confidence: Literal["low", "moderate", "high"]
    observations: list[ElyraMultimodalObservationV2] = Field(min_length=1, max_length=6)
    limitations: list[str] = Field(min_length=2, max_length=5)
    disclaimer: Literal[ELYRA_MULTIMODAL_DISCLAIMER]  # type: ignore[valid-type]
    safety: ElyraMultimodalSafetyV2

    @model_validator(mode="after")
    def validate_limitations(self) -> "ElyraMultimodalOutputV2":
        if any(not value.strip() or len(value) > 320 for value in self.limitations):
            raise ValueError("limitacao vazia ou extensa demais")
        return self


assert ELYRA_MULTIMODAL_OPERATION == "interpret_observable_session_signals"

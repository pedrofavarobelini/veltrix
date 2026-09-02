"""Boundary tipado e fail-closed da capability multimodal V1 do Elyra.

Espelha a disciplina de `elyra_textual`, mas com contrato, task, consentimento e
declaracao de seguranca proprios. Nenhuma regra textual e reaproveitada por
generalizacao: um payload textual nunca satisfaz este contrato e vice-versa.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import ValidationError

from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.chat.schemas import ChatRequest
from app.modules.contracts import codes
from app.modules.elyra_multimodal.schemas import (
    ELYRA_MULTIMODAL_CANONICAL_MESSAGE,
    ELYRA_MULTIMODAL_CONTRACT_VERSION,
    ELYRA_MULTIMODAL_DISCLAIMER,
    ELYRA_MULTIMODAL_OPERATION,
    ELYRA_MULTIMODAL_OUTPUT_SCHEMA_VERSION,
    FEATURE_EXTRACTOR_VERSION,
    SIGNALS_SCHEMA_VERSION,
    ElyraMultimodalInputV1,
    ElyraMultimodalObservationV1,
    ElyraMultimodalOutputV1,
    ElyraMultimodalSafetyV1,
    ObservableSignalV1,
)

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")

INVALID_INPUT_REASON = (
    "Payload Elyra incompatível com elyra-multimodal-input/v1; nenhuma chamada "
    "de provider foi iniciada."
)
CONSENT_REQUIRED_REASON = (
    "A operação multimodal Elyra exige consentimento explícito de inferência de IA "
    "E de análise multimodal; consentimento de captura, armazenamento, "
    "compartilhamento ou learning não o substitui."
)
PROVIDER_POLICY_REASON = (
    "Elyra multimodal V1 aceita provider=mock para QA determinística ou "
    "provider=auto com allow_real_provider=true e allow_mock_fallback=false."
)
OUTPUT_INVALID_REASON = (
    "Resposta incompatível com elyra-multimodal-output/v1; conteúdo parcial não "
    "foi publicado."
)
PROVIDER_MISMATCH_REASON = (
    "Provider ou modelo respondente divergiu do binding selecionado pelo Veltrix; "
    "resposta multimodal recusada sem fallback."
)
IDEMPOTENCY_CONFLICT_REASON = (
    "Idempotency key multimodal já usada com payload diferente; requisição negada "
    "sem novo dispatch."
)
INTERNAL_FAILURE_REASON = (
    "Falha interna controlada no contrato multimodal Elyra; nenhuma resposta foi "
    "tratada como sucesso."
)
CALLER_NOT_REGISTERED_REASON = (
    "A capability multimodal Elyra exige credencial registrada, vinculada ao "
    "project_id=elyra e ao papel common_consumer; identidade local, compartilhada "
    "ou de outro projeto é negada."
)

_SIGNAL_LABEL: dict[str, str] = {
    "speech_rate": "Ritmo de fala",
    "pause_count": "Quantidade de pausas",
    "pause_total_duration": "Tempo total em pausa",
    "pause_mean_duration": "Duração média das pausas",
    "vocal_variation": "Variação vocal",
    "movement_frequency": "Frequência de movimento",
}

_SIGNAL_UNIT_LABEL: dict[str, str] = {
    "words_per_minute": "palavras por minuto",
    "count": "ocorrências",
    "milliseconds": "ms",
    "index": "índice 0-1",
}


@dataclass(frozen=True)
class ElyraMultimodalInputValidation:
    value: ElyraMultimodalInputV1 | None = None
    error_code: str | None = None
    reason: str | None = None

    @property
    def valid(self) -> bool:
        return self.value is not None


@dataclass(frozen=True)
class ElyraMultimodalOutputValidation:
    value: ElyraMultimodalOutputV1 | None = None
    error_code: str | None = None
    reason: str | None = None

    @property
    def valid(self) -> bool:
        return self.value is not None


class ElyraMultimodalService:
    """Capability multimodal V1: sinais observaveis, nunca emocao objetiva."""

    def validate_input(
        self,
        payload: ChatRequest,
        caller: AuthenticatedCallerContext,
    ) -> ElyraMultimodalInputValidation:
        if not (
            caller.identity_strength is IdentityStrength.REGISTERED
            and caller.project_id == "elyra"
            and caller.caller_role is CallerRole.COMMON_CONSUMER
            and caller.allowed_origins is not None
            and "elyra" in caller.allowed_origins
        ):
            return ElyraMultimodalInputValidation(
                error_code=codes.ELYRA_MULTIMODAL_CALLER_NOT_REGISTERED,
                reason=CALLER_NOT_REGISTERED_REASON,
            )

        correlation = payload.correlation_id or ""
        idempotency = payload.idempotency_key or ""
        if not _IDENTIFIER.fullmatch(correlation) or not _IDENTIFIER.fullmatch(
            idempotency
        ):
            return ElyraMultimodalInputValidation(
                error_code=codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID,
                reason=INVALID_INPUT_REASON,
            )

        if (
            payload.message != ELYRA_MULTIMODAL_CANONICAL_MESSAGE
            or payload.mode != "tecnico"
            or payload.system_prompt is not None
            or payload.metadata is not None
            or payload.artifacts is not None
            or payload.context_from_memory
            or payload.allow_local_model
        ):
            return ElyraMultimodalInputValidation(
                error_code=codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID,
                reason=INVALID_INPUT_REASON,
            )

        requested_provider = (payload.provider or "").strip().lower()
        mock_mode = requested_provider == "mock" and not payload.allow_real_provider
        real_mode = (
            requested_provider == "auto"
            and payload.allow_real_provider
            and not payload.allow_mock_fallback
        )
        if not (mock_mode or real_mode):
            return ElyraMultimodalInputValidation(
                error_code=codes.ELYRA_MULTIMODAL_PROVIDER_POLICY_DENIED,
                reason=PROVIDER_POLICY_REASON,
            )

        try:
            value = ElyraMultimodalInputV1.model_validate(payload.context)
        except ValidationError:
            return ElyraMultimodalInputValidation(
                error_code=codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID,
                reason=INVALID_INPUT_REASON,
            )

        # Dois consentimentos independentes e obrigatorios. Um nao substitui o outro.
        if not (value.ai_inference_consent and value.multimodal_analysis_consent):
            return ElyraMultimodalInputValidation(
                error_code=codes.ELYRA_MULTIMODAL_CONSENT_REQUIRED,
                reason=CONSENT_REQUIRED_REASON,
            )

        return ElyraMultimodalInputValidation(value=value)

    @staticmethod
    def system_prompt() -> str:
        return f"""Você executa exclusivamente o contrato {ELYRA_MULTIMODAL_CONTRACT_VERSION}.
Você recebe SOMENTE sinais observáveis já calculados pela Elyra e, quando houver
consentimento, uma transcrição. Você NUNCA recebe áudio, vídeo, tela ou imagem.
Sinal observável NÃO é emoção. É proibido inferir, nomear, estimar ou
percentualizar emoção, sentimento ou estado afetivo a partir de ritmo de fala,
pausas, variação vocal, movimento ou expressão facial.
Não diagnostique, não prescreva, não afirme condição clínica e não transforme
associação temporal em causalidade. Compare somente com a baseline pessoal
enviada; nunca com norma populacional. Quando `status` for
`insufficient_baseline` ou `not_captured`, diga que não há comparação possível —
ausência de dado não é zero.
Responda SOMENTE com JSON válido, sem Markdown, no schema
{ELYRA_MULTIMODAL_OUTPUT_SCHEMA_VERSION}, com estas chaves exatas:
contractVersion, outputSchemaVersion, operation, correlationId,
sourceSignalsSchemaVersion, sourceFeatureExtractorVersion, language, summary,
observations, limitations, disclaimer e safety.
Cada observation exige category, evidencePath e text. safety deve declarar false
para diagnosticClaim, prescription, causalClaim, facialEmotionAsFact,
fictitiousEmotionPercentage, emotionInferredFromSignal, rawMediaAccessed e
populationNormComparison.
O disclaimer deve ser exatamente: {ELYRA_MULTIMODAL_DISCLAIMER}"""

    def deterministic_mock(
        self,
        request: ElyraMultimodalInputV1,
        correlation_id: str,
    ) -> ElyraMultimodalOutputV1:
        session = request.session
        observations: list[ElyraMultimodalObservationV1] = [
            ElyraMultimodalObservationV1(
                category="capture_quality",
                evidencePath="captureQuality",
                text=(
                    f"A sessão do tipo {session.session_kind} durou "
                    f"{session.duration_ms} ms e registrou "
                    f"{', '.join(session.captured_resources)}."
                ),
            )
        ]

        for signal in session.signals:
            if len(observations) >= 5:
                break
            observations.append(self._signal_observation(signal))

        if session.transcript is not None and len(observations) < 6:
            observations.append(
                ElyraMultimodalObservationV1(
                    category="transcript",
                    evidencePath="transcript",
                    text=(
                        "A transcrição consentida registrou "
                        f"{session.transcript.word_count} palavras em "
                        f"{session.transcript.voiced_duration_ms} ms de fala."
                    ),
                )
            )

        return ElyraMultimodalOutputV1(
            contractVersion=ELYRA_MULTIMODAL_CONTRACT_VERSION,
            outputSchemaVersion=ELYRA_MULTIMODAL_OUTPUT_SCHEMA_VERSION,
            operation=ELYRA_MULTIMODAL_OPERATION,
            correlationId=correlation_id,
            sourceSignalsSchemaVersion=SIGNALS_SCHEMA_VERSION,
            sourceFeatureExtractorVersion=FEATURE_EXTRACTOR_VERSION,
            language="pt-BR",
            summary=(
                "Leitura não clínica dos sinais observáveis registrados nesta "
                "sessão. As observações descrevem apenas como a sessão foi "
                "registrada, comparada ao histórico da própria pessoa usuária, e "
                "não determinam emoção nem estado afetivo."
            ),
            observations=observations[:6],
            limitations=[
                "Sinais observáveis descrevem a forma do registro e não indicam emoção.",
                "Ausência de dado não equivale a zero e limita qualquer comparação.",
                "A comparação é somente com o histórico pessoal, nunca com uma norma.",
                "A resposta não substitui avaliação humana ou acompanhamento profissional.",
            ],
            disclaimer=ELYRA_MULTIMODAL_DISCLAIMER,
            safety=ElyraMultimodalSafetyV1(
                diagnosticClaim=False,
                prescription=False,
                causalClaim=False,
                facialEmotionAsFact=False,
                fictitiousEmotionPercentage=False,
                emotionInferredFromSignal=False,
                rawMediaAccessed=False,
                populationNormComparison=False,
            ),
        )

    @staticmethod
    def _signal_observation(signal: ObservableSignalV1) -> ElyraMultimodalObservationV1:
        label = _SIGNAL_LABEL[signal.name]
        evidence_path = f"signals.{signal.name}"

        if signal.status == "not_captured":
            text = (
                f"{label}: não capturado nesta sessão; ausência de captura não é "
                "valor zero e não permite comparação."
            )
        elif signal.status == "insufficient_baseline":
            unit = _SIGNAL_UNIT_LABEL[signal.unit]
            text = (
                f"{label}: {signal.value:g} {unit} nesta sessão. Ainda não há "
                "histórico pessoal suficiente para comparar."
            )
        else:
            unit = _SIGNAL_UNIT_LABEL[signal.unit]
            delta = signal.delta_vs_personal_baseline
            direction = (
                "acima"
                if delta is not None and delta > 0
                else "abaixo"
                if delta is not None and delta < 0
                else "em linha com"
            )
            text = (
                f"{label}: {signal.value:g} {unit} nesta sessão, {direction} da "
                f"média pessoal de {signal.personal_baseline_mean:g} {unit} em "
                f"{signal.personal_baseline_samples} sessões anteriores."
            )

        return ElyraMultimodalObservationV1(
            category="observable_signal",
            evidencePath=evidence_path,
            text=text[:320],
        )

    @staticmethod
    def serialize_output(value: ElyraMultimodalOutputV1) -> str:
        return value.model_dump_json(by_alias=True)

    @staticmethod
    def validate_output(
        raw: str,
        request: ElyraMultimodalInputV1,
        correlation_id: str,
    ) -> ElyraMultimodalOutputValidation:
        try:
            decoded = json.loads(raw)
            value = ElyraMultimodalOutputV1.model_validate(decoded)
        except (json.JSONDecodeError, ValidationError, TypeError):
            return ElyraMultimodalOutputValidation(
                error_code=codes.ELYRA_MULTIMODAL_OUTPUT_INVALID,
                reason=OUTPUT_INVALID_REASON,
            )

        session = request.session
        if (
            value.correlation_id != correlation_id
            or value.source_signals_schema_version != session.signals_schema_version
            or value.source_feature_extractor_version
            != session.feature_extractor_version
        ):
            return ElyraMultimodalOutputValidation(
                error_code=codes.ELYRA_MULTIMODAL_OUTPUT_INVALID,
                reason=OUTPUT_INVALID_REASON,
            )

        # Sem consentimento de transcricao o modelo nao pode ancorar observacao
        # em transcricao: isso seria interpretar o que nao foi autorizado.
        if not request.transcript_analysis_consent and any(
            observation.evidence_path == "transcript"
            for observation in value.observations
        ):
            return ElyraMultimodalOutputValidation(
                error_code=codes.ELYRA_MULTIMODAL_OUTPUT_INVALID,
                reason=OUTPUT_INVALID_REASON,
            )

        # Observacao so pode citar sinal realmente enviado nesta sessao.
        sent_paths = {f"signals.{signal.name}" for signal in session.signals}
        for observation in value.observations:
            if (
                observation.evidence_path.startswith("signals.")
                and observation.evidence_path not in sent_paths
            ):
                return ElyraMultimodalOutputValidation(
                    error_code=codes.ELYRA_MULTIMODAL_OUTPUT_INVALID,
                    reason=OUTPUT_INVALID_REASON,
                )

        return ElyraMultimodalOutputValidation(value=value)


elyra_multimodal_service = ElyraMultimodalService()

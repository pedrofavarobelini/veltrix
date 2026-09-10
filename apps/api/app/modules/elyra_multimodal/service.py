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
from app.modules.elyra_multimodal.schemas_v2 import (
    EVIDENCE_PATHS_V2,
    ELYRA_MULTIMODAL_CONTRACT_VERSION_V2,
    ELYRA_MULTIMODAL_OUTPUT_SCHEMA_VERSION_V2,
    FEATURE_EXTRACTOR_VERSION_V2,
    SIGNALS_SCHEMA_VERSION_V2,
    ElyraMultimodalInputV2,
    ElyraMultimodalObservationV2,
    ElyraMultimodalOutputV2,
    ElyraMultimodalSafetyV2,
    ObservableSignalV2,
)

# A fronteira aceita as DUAS versoes. A V1 nao e removida nem convertida em
# silencio: converter perderia cobertura, autorrelato, janela e consentimento
# visual - campos que a V1 nao sabe nomear. Cada versao e validada pelo seu
# proprio schema, e a resposta sai na mesma versao em que a pergunta entrou.
ElyraMultimodalInput = ElyraMultimodalInputV1 | ElyraMultimodalInputV2
ElyraMultimodalOutput = ElyraMultimodalOutputV1 | ElyraMultimodalOutputV2

_INPUT_MODEL_BY_CONTRACT: dict[str, type] = {
    ELYRA_MULTIMODAL_CONTRACT_VERSION: ElyraMultimodalInputV1,
    ELYRA_MULTIMODAL_CONTRACT_VERSION_V2: ElyraMultimodalInputV2,
}

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

# Rotulos da V2. Cada nome descreve A MEDIDA, nunca um estado da pessoa:
# "frequencia de movimento da cabeca" e uma contagem normalizada de amostras em
# que a orientacao mudou acima de um limiar. Nao e agitacao, nao e ansiedade e
# nao e desinteresse - e por isso nenhuma dessas palavras aparece aqui.
_SIGNAL_LABEL_V2: dict[str, str] = {
    **_SIGNAL_LABEL,
    "head_movement_frequency": "Frequência de movimento da cabeça",
    "head_motion_amplitude": "Amplitude de movimento da cabeça",
    "body_movement_frequency": "Frequência de movimento do corpo",
    "body_motion_amplitude": "Amplitude de movimento do corpo",
    "hand_movement_frequency": "Frequência de movimento das mãos",
}

_SIGNAL_UNIT_LABEL: dict[str, str] = {
    "words_per_minute": "palavras por minuto",
    "count": "ocorrências",
    "milliseconds": "ms",
    "index": "índice 0-1",
}


@dataclass(frozen=True)
class ElyraMultimodalInputValidation:
    value: ElyraMultimodalInput | None = None
    error_code: str | None = None
    reason: str | None = None

    @property
    def valid(self) -> bool:
        return self.value is not None


@dataclass(frozen=True)
class ElyraMultimodalOutputValidation:
    value: ElyraMultimodalOutput | None = None
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

        """
        A versao do contrato vem do proprio payload, e nao de configuracao.

        Escolher o schema por flag de ambiente faria a mesma requisicao ser
        aceita ou recusada dependendo de como o servidor foi iniciado. Aqui a
        pergunta declara em que contrato ela esta escrita, e a validacao usa
        exatamente esse - um payload V2 nunca e "quase validado" como V1.
        """
        context = payload.context if isinstance(payload.context, dict) else {}
        declared = context.get("contractVersion")
        model = _INPUT_MODEL_BY_CONTRACT.get(declared)
        if model is None:
            return ElyraMultimodalInputValidation(
                error_code=codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID,
                reason=INVALID_INPUT_REASON,
            )

        try:
            value = model.model_validate(payload.context)
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
    def system_prompt(
        request: ElyraMultimodalInput | None = None,
        correlation_id: str | None = None,
    ) -> str:
        """Prompt na versao do contrato que entrou.

        Pedir saida `output/v1` para uma pergunta `input/v2` produziria uma
        resposta que a validacao recusaria depois - gastando uma chamada de
        provider real para falhar na borda.

        `correlation_id` chega ate aqui porque a validacao de saida EXIGE que a
        resposta o repita. Sem ele no prompt o modelo nao tem como saber o valor:
        na primeira execucao real ele devolveu um UUID de zeros, e a resposta foi
        recusada por uma informacao que ninguem tinha dado a ele.
        """
        if isinstance(request, ElyraMultimodalInputV2):
            return ElyraMultimodalService._system_prompt_v2(request, correlation_id)
        return ElyraMultimodalService._system_prompt_v1()

    @staticmethod
    def _system_prompt_v1() -> str:
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

    @staticmethod
    def _system_prompt_v2(
        request: ElyraMultimodalInputV2 | None = None,
        correlation_id: str | None = None,
    ) -> str:
        """Prompt da V2.

        A primeira execucao contra provider real mostrou que listar as CHAVES nao
        basta: o modelo devolveu JSON bem formado com valores inventados -
        `operation` abreviada, versoes de schema trocadas, `correlationId` de
        zeros, `category` e `evidencePath` fora do vocabulario e `limitations`
        como objeto em vez de lista.

        Nenhum desses valores e opiniao do modelo: sao constantes do contrato ou
        vocabularios fechados. Agora eles vao ditados, com o valor exato a repetir.
        A validacao continua recusando o que nao bater - o prompt nao afrouxa
        nada, so para de esconder do modelo o que ele precisa saber.
        """
        echo_correlation = correlation_id or "(o correlation_id recebido na requisicao)"
        evidence_paths = ", ".join(f"`{path}`" for path in EVIDENCE_PATHS_V2)
        return f"""Você executa exclusivamente o contrato {ELYRA_MULTIMODAL_CONTRACT_VERSION_V2}.
Você recebe SOMENTE sinais observáveis já calculados pela Elyra, cobertura por
modalidade, janelas temporais, autorrelato da própria pessoa e, quando houver
consentimento, uma transcrição. Você NUNCA recebe áudio, vídeo, tela, imagem ou
qualquer geometria corporal ponto a ponto.
Sinal observável NÃO é emoção. É proibido inferir, nomear, estimar ou
percentualizar emoção, sentimento ou estado afetivo a partir de ritmo de fala,
pausas, variação vocal, movimento de cabeça, de corpo, de mãos ou expressão
facial. Movimento de cabeça não é agitação, não é ansiedade, não é desinteresse
e não é engajamento: é uma contagem normalizada de mudança de orientação.
Não diagnostique, não prescreva, não afirme condição clínica e não transforme
associação temporal em causalidade. Compare somente com a baseline pessoal
enviada; nunca com norma populacional. Quando `status` for
`insufficient_baseline` ou `not_captured`, diga que não há comparação possível —
ausência de dado não é zero.
A cobertura (`coverage`) diz por quanto tempo a modalidade esteve ativa dentro
da sessão. Cobertura parcial NÃO é cobertura completa: um sinal derivado de uma
fração da sessão não pode ser descrito como se falasse da sessão inteira.
O autorrelato (`selfReport`) é o que a pessoa disse sobre si. Ele NUNCA é
corrigido, contestado ou confirmado por sinal observável, e o inverso também não:
são camadas diferentes, e apresentá-las como concordância ou contradição seria
tratar sinal como medida de estado interno.
A transcrição, quando existir, é saída de reconhecimento automático e pode conter
erro. Trate-a como registro aproximado do que foi dito, nunca como transcrição
literal perfeita. Se `provenance.humanCorrected` for true, o texto foi revisado
por quem falou.
`confidence` ALTERA o que você afirma: com `low`, recue na afirmação em vez de
manter uma frase categórica com ressalva.
Responda SOMENTE com JSON válido, sem Markdown, sem cercas ``` e sem texto
antes ou depois. Use EXATAMENTE estes valores nos campos constantes — eles não
são escolha sua, são identidade do contrato:

  "contractVersion": "{ELYRA_MULTIMODAL_CONTRACT_VERSION_V2}"
  "outputSchemaVersion": "{ELYRA_MULTIMODAL_OUTPUT_SCHEMA_VERSION_V2}"
  "operation": "{ELYRA_MULTIMODAL_OPERATION}"
  "correlationId": "{echo_correlation}"
  "sourceSignalsSchemaVersion": "{SIGNALS_SCHEMA_VERSION_V2}"
  "sourceFeatureExtractorVersion": "{FEATURE_EXTRACTOR_VERSION_V2}"
  "language": "pt-BR"

`summary`: uma string, até 1000 caracteres.
`confidence`: exatamente uma de "low", "moderate", "high".
`observations`: LISTA de 1 a 6 objetos, cada um com exatamente três campos —
  "category": uma de "observable_signal", "transcript", "capture_quality";
  "evidencePath": uma de {evidence_paths};
  "text": string de até 320 caracteres.
  Só cite `evidencePath` de sinal que foi realmente enviado nesta sessão.
`limitations`: LISTA de 2 a 5 strings, cada uma de até 320 caracteres. É uma
  lista de textos — nunca um objeto, nunca uma string única.
`safety`: objeto com estas nove chaves, todas com o valor booleano false —
  diagnosticClaim, prescription, causalClaim, facialEmotionAsFact,
  fictitiousEmotionPercentage, emotionInferredFromSignal, rawMediaAccessed,
  populationNormComparison, selfReportContradictedBySignal.
`disclaimer`: exatamente este texto, sem alterar nenhuma palavra:
{ELYRA_MULTIMODAL_DISCLAIMER}"""

    def deterministic_mock(
        self,
        request: ElyraMultimodalInput,
        correlation_id: str,
    ) -> ElyraMultimodalOutput:
        if isinstance(request, ElyraMultimodalInputV2):
            return self._deterministic_mock_v2(request, correlation_id)
        return self._deterministic_mock_v1(request, correlation_id)

    def _deterministic_mock_v1(
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
    def serialize_output(value: ElyraMultimodalOutput) -> str:
        return value.model_dump_json(by_alias=True)

    @staticmethod
    def validate_output(
        raw: str,
        request: ElyraMultimodalInput,
        correlation_id: str,
    ) -> ElyraMultimodalOutputValidation:
        if isinstance(request, ElyraMultimodalInputV2):
            return ElyraMultimodalService._validate_output_v2(
                raw, request, correlation_id
            )
        return ElyraMultimodalService._validate_output_v1(raw, request, correlation_id)

    @staticmethod
    def _validate_output_v1(
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

    # ------------------------------------------------------------------
    # V2
    # ------------------------------------------------------------------

    def _deterministic_mock_v2(
        self,
        request: ElyraMultimodalInputV2,
        correlation_id: str,
    ) -> ElyraMultimodalOutputV2:
        """Mock deterministico da V2.

        Ele existe para QA, e por isso descreve o que chegou sem interpretar:
        um mock que "parecesse inteligente" esconderia justamente os casos em
        que o payload chegou vazio, parcial ou sem baseline.
        """
        session = request.session
        observations: list[ElyraMultimodalObservationV2] = [
            ElyraMultimodalObservationV2(
                category="capture_quality",
                evidencePath="captureQuality",
                text=(
                    f"A sessao do tipo {session.session_kind} durou "
                    f"{session.duration_ms} ms e registrou "
                    f"{', '.join(session.captured_resources)}."
                ),
            )
        ]

        # Cobertura parcial e a informacao que a V1 nao sabia dizer.
        partial = [
            coverage
            for coverage in session.modality_coverage
            if coverage.outcome != "full"
        ]
        if partial and len(observations) < 6:
            described = ", ".join(
                f"{coverage.modality}={coverage.outcome}" for coverage in partial[:3]
            )
            observations.append(
                ElyraMultimodalObservationV2(
                    category="capture_quality",
                    evidencePath="coverage",
                    text=(
                        f"Cobertura incompleta em {described}. Um sinal derivado "
                        "de parte da sessao nao descreve a sessao inteira."
                    )[:320],
                )
            )

        for signal in session.signals:
            if len(observations) >= 5:
                break
            observations.append(self._signal_observation_v2(signal))

        if session.transcript is not None and len(observations) < 6:
            corrected = (
                session.transcript.provenance is not None
                and session.transcript.provenance.human_corrected
            )
            origin = (
                "revisada pela pessoa usuaria"
                if corrected
                else "produzida por reconhecimento automatico, sujeita a erro"
            )
            observations.append(
                ElyraMultimodalObservationV2(
                    category="transcript",
                    evidencePath="transcript",
                    text=(
                        f"A transcricao consentida ({origin}) registrou "
                        f"{session.transcript.word_count} palavras em "
                        f"{session.transcript.voiced_duration_ms} ms de fala."
                    )[:320],
                )
            )

        # Confianca derivada da cobertura, e nao um rotulo fixo.
        #
        # Uma sessao cuja camera cobriu 8% do tempo nao sustenta a mesma
        # afirmacao que uma coberta inteira, e `confidence` e o campo que faz a
        # saida recuar em vez de acrescentar uma ressalva ao fim de uma frase
        # categorica.
        confidence = "high"
        if partial:
            confidence = "moderate"
        if any(
            coverage.outcome == "absent" for coverage in session.modality_coverage
        ) or all(signal.status != "available" for signal in session.signals):
            confidence = "low"

        return ElyraMultimodalOutputV2(
            contractVersion=ELYRA_MULTIMODAL_CONTRACT_VERSION_V2,
            outputSchemaVersion=ELYRA_MULTIMODAL_OUTPUT_SCHEMA_VERSION_V2,
            operation=ELYRA_MULTIMODAL_OPERATION,
            correlationId=correlation_id,
            sourceSignalsSchemaVersion=SIGNALS_SCHEMA_VERSION_V2,
            sourceFeatureExtractorVersion=FEATURE_EXTRACTOR_VERSION_V2,
            language="pt-BR",
            summary=(
                "Leitura nao clinica dos sinais observaveis registrados nesta "
                "sessao. As observacoes descrevem apenas como a sessao foi "
                "registrada, comparada ao historico da propria pessoa usuaria, e "
                "nao determinam emocao nem estado afetivo."
            ),
            confidence=confidence,
            observations=observations[:6],
            limitations=[
                "Sinais observaveis descrevem a forma do registro e nao indicam emocao.",
                "Ausencia de dado nao equivale a zero e limita qualquer comparacao.",
                "Cobertura parcial descreve so o trecho observado, nao a sessao inteira.",
                "A comparacao e somente com o historico pessoal, nunca com uma norma.",
                "A resposta nao substitui avaliacao humana ou acompanhamento profissional.",
            ],
            disclaimer=ELYRA_MULTIMODAL_DISCLAIMER,
            safety=ElyraMultimodalSafetyV2(
                diagnosticClaim=False,
                prescription=False,
                causalClaim=False,
                facialEmotionAsFact=False,
                fictitiousEmotionPercentage=False,
                emotionInferredFromSignal=False,
                rawMediaAccessed=False,
                populationNormComparison=False,
                selfReportContradictedBySignal=False,
            ),
        )

    @staticmethod
    def _signal_observation_v2(
        signal: ObservableSignalV2,
    ) -> ElyraMultimodalObservationV2:
        label = _SIGNAL_LABEL_V2[signal.name]
        evidence_path = f"signals.{signal.name}"

        if signal.status == "not_captured":
            text = (
                f"{label}: nao capturado nesta sessao; ausencia de captura nao e "
                "valor zero e nao permite comparacao."
            )
        elif signal.status == "insufficient_baseline":
            unit = _SIGNAL_UNIT_LABEL[signal.unit]
            text = (
                f"{label}: {signal.value:g} {unit} nesta sessao. Ainda nao ha "
                "historico pessoal suficiente para comparar."
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
                f"{label}: {signal.value:g} {unit} nesta sessao, {direction} da "
                f"media pessoal de {signal.personal_baseline_mean:g} {unit} em "
                f"{signal.personal_baseline_samples} sessoes anteriores."
            )

        return ElyraMultimodalObservationV2(
            category="observable_signal",
            evidencePath=evidence_path,
            text=text[:320],
        )

    @staticmethod
    def _validate_output_v2(
        raw: str,
        request: ElyraMultimodalInputV2,
        correlation_id: str,
    ) -> ElyraMultimodalOutputValidation:
        try:
            decoded = json.loads(raw)
            value = ElyraMultimodalOutputV2.model_validate(decoded)
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

        # Ancorar em autorrelato que nao foi enviado seria inventar o relato.
        if session.self_report is None and any(
            observation.evidence_path == "selfReport"
            for observation in value.observations
        ):
            return ElyraMultimodalOutputValidation(
                error_code=codes.ELYRA_MULTIMODAL_OUTPUT_INVALID,
                reason=OUTPUT_INVALID_REASON,
            )

        # Ancorar em linha do tempo sem janela enviada teria o mesmo defeito.
        if not session.windows and any(
            observation.evidence_path == "timeline"
            for observation in value.observations
        ):
            return ElyraMultimodalOutputValidation(
                error_code=codes.ELYRA_MULTIMODAL_OUTPUT_INVALID,
                reason=OUTPUT_INVALID_REASON,
            )

        return ElyraMultimodalOutputValidation(value=value)


elyra_multimodal_service = ElyraMultimodalService()

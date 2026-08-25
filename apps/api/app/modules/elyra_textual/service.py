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
from app.modules.elyra_textual.schemas import (
    ANALYTICS_VERSION,
    ELYRA_CANONICAL_MESSAGE,
    ELYRA_CONTRACT_VERSION,
    ELYRA_DISCLAIMER,
    ELYRA_OPERATION,
    ELYRA_OUTPUT_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
    ComparisonV1,
    ElyraObservationV1,
    ElyraSafetyDeclarationV1,
    ElyraTextualInputV1,
    ElyraTextualOutputV1,
)

_CORRELATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")

INVALID_INPUT_REASON = (
    "Payload Elyra incompatível com elyra-textual-input/v1; nenhuma chamada "
    "de provider foi iniciada."
)
CONSENT_REQUIRED_REASON = (
    "A operação textual Elyra exige consentimento explícito de inferência; "
    "consentimentos de armazenamento, ciclo, profissional ou learning não o substituem."
)
PROVIDER_POLICY_REASON = (
    "Elyra textual V1 aceita provider=mock para QA determinística ou provider=auto "
    "com allow_real_provider=true e allow_mock_fallback=false."
)
OUTPUT_INVALID_REASON = (
    "Resposta incompatível com elyra-textual-output/v1; conteúdo parcial não foi publicado."
)
PROVIDER_MISMATCH_REASON = (
    "Provider ou modelo respondente divergiu do binding selecionado pelo PedroCore; "
    "resposta recusada sem fallback."
)
IDEMPOTENCY_CONFLICT_REASON = (
    "Idempotency key já usada com payload diferente; requisição negada sem novo dispatch."
)
INTERNAL_FAILURE_REASON = (
    "Falha interna controlada no contrato Elyra; nenhuma resposta foi tratada como sucesso."
)
CALLER_NOT_REGISTERED_REASON = (
    "Elyra exige credencial registrada, vinculada ao project_id=elyra e ao papel "
    "common_consumer; identidade local, compartilhada ou de outro projeto é negada."
)


@dataclass(frozen=True)
class ElyraInputValidation:
    value: ElyraTextualInputV1 | None = None
    error_code: str | None = None
    reason: str | None = None

    @property
    def valid(self) -> bool:
        return self.value is not None


@dataclass(frozen=True)
class ElyraOutputValidation:
    value: ElyraTextualOutputV1 | None = None
    error_code: str | None = None
    reason: str | None = None

    @property
    def valid(self) -> bool:
        return self.value is not None


class ElyraTextualService:
    """Boundary tipado para a capability textual V1 do Elyra."""

    def validate_input(
        self,
        payload: ChatRequest,
        caller: AuthenticatedCallerContext,
    ) -> ElyraInputValidation:
        if not (
            caller.identity_strength is IdentityStrength.REGISTERED
            and caller.project_id == "elyra"
            and caller.caller_role is CallerRole.COMMON_CONSUMER
            and caller.allowed_origins is not None
            and "elyra" in caller.allowed_origins
        ):
            return ElyraInputValidation(
                error_code=codes.ELYRA_CALLER_NOT_REGISTERED,
                reason=CALLER_NOT_REGISTERED_REASON,
            )

        correlation = payload.correlation_id or ""
        idempotency = payload.idempotency_key or ""
        if not _CORRELATION_ID.fullmatch(correlation) or not _IDEMPOTENCY_KEY.fullmatch(
            idempotency
        ):
            return ElyraInputValidation(
                error_code=codes.ELYRA_INPUT_SCHEMA_INVALID,
                reason=INVALID_INPUT_REASON,
            )

        if (
            payload.message != ELYRA_CANONICAL_MESSAGE
            or payload.mode != "tecnico"
            or payload.system_prompt is not None
            or payload.metadata is not None
            or payload.artifacts is not None
            or payload.context_from_memory
            or payload.allow_local_model
        ):
            return ElyraInputValidation(
                error_code=codes.ELYRA_INPUT_SCHEMA_INVALID,
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
            return ElyraInputValidation(
                error_code=codes.ELYRA_PROVIDER_POLICY_DENIED,
                reason=PROVIDER_POLICY_REASON,
            )

        try:
            value = ElyraTextualInputV1.model_validate(payload.context)
        except ValidationError:
            return ElyraInputValidation(
                error_code=codes.ELYRA_INPUT_SCHEMA_INVALID,
                reason=INVALID_INPUT_REASON,
            )

        if not value.ai_inference_consent:
            return ElyraInputValidation(
                error_code=codes.ELYRA_CONSENT_REQUIRED,
                reason=CONSENT_REQUIRED_REASON,
            )

        return ElyraInputValidation(value=value)

    @staticmethod
    def system_prompt() -> str:
        return f"""Você executa exclusivamente o contrato {ELYRA_CONTRACT_VERSION}.
Interprete somente as métricas já calculadas no relatório estruturado enviado.
Não recalcule métricas, não invente score e não use conhecimento clínico.
Não diagnostique, não prescreva, não afirme condição clínica e não transforme
associação temporal em causalidade. Não trate expressão facial como emoção objetiva
e não produza percentual fictício de emoção.
Responda SOMENTE com JSON válido, sem Markdown, no schema
{ELYRA_OUTPUT_SCHEMA_VERSION}, com estas chaves exatas:
contractVersion, outputSchemaVersion, operation, correlationId,
sourceReportSchemaVersion, sourceAnalyticsVersion, language, summary,
observations, limitations, disclaimer e safety.
Cada observation exige category, evidencePath e text. safety deve declarar false
para diagnosticClaim, prescription, causalClaim, facialEmotionAsFact e
fictitiousEmotionPercentage. O disclaimer deve ser exatamente: {ELYRA_DISCLAIMER}"""

    def deterministic_mock(
        self,
        request: ElyraTextualInputV1,
        correlation_id: str,
    ) -> ElyraTextualOutputV1:
        report = request.report
        quality = report.data_quality
        observations = [
            ElyraObservationV1(
                category="data_quality",
                evidencePath="dataQuality",
                text=(
                    f"A janela contém {quality.days_in_window} dias; há dados de humor "
                    f"em {quality.days_with_mood} dias, ansiedade em "
                    f"{quality.days_with_anxiety}, energia em {quality.days_with_energy} "
                    f"e sono em {quality.days_with_sleep}."
                ),
            )
        ]

        for label, path, comparison in (
            ("Humor", "metrics.mood", report.metrics.mood),
            ("Ansiedade percebida", "metrics.anxiety", report.metrics.anxiety),
            ("Energia", "metrics.energy", report.metrics.energy),
        ):
            observations.append(self._metric_observation(label, path, comparison))

        association = report.associations.pre_period_energy
        if association.status == "available":
            observations.append(
                ElyraObservationV1(
                    category="temporal_association",
                    evidencePath="associations.prePeriodEnergy",
                    text=(
                        "O snapshot marcou associação temporal disponível para energia "
                        "antes de períodos registrados; isso descreve coexistência nos "
                        "dados e não demonstra causa."
                    ),
                )
            )

        return ElyraTextualOutputV1(
            contractVersion=ELYRA_CONTRACT_VERSION,
            outputSchemaVersion=ELYRA_OUTPUT_SCHEMA_VERSION,
            operation=ELYRA_OPERATION,
            correlationId=correlation_id,
            sourceReportSchemaVersion=REPORT_SCHEMA_VERSION,
            sourceAnalyticsVersion=ANALYTICS_VERSION,
            language="pt-BR",
            summary=(
                "Interpretação não clínica concluída sobre o snapshot determinístico. "
                "As observações abaixo apenas descrevem os valores e tendências já "
                "calculados pela Elyra."
            ),
            observations=observations[:5],
            limitations=[
                "Ausência de dado não equivale a zero e limita qualquer interpretação.",
                "Tendências e associações não estabelecem diagnóstico nem causalidade.",
                "A resposta não substitui avaliação humana ou acompanhamento profissional.",
            ],
            disclaimer=ELYRA_DISCLAIMER,
            safety=ElyraSafetyDeclarationV1(
                diagnosticClaim=False,
                prescription=False,
                causalClaim=False,
                facialEmotionAsFact=False,
                fictitiousEmotionPercentage=False,
            ),
        )

    @staticmethod
    def _metric_observation(
        label: str,
        evidence_path: str,
        comparison: ComparisonV1,
    ) -> ElyraObservationV1:
        trend_text = {
            "up": "tendência de alta",
            "down": "tendência de queda",
            "stable": "tendência estável",
            "insufficient_data": "dados insuficientes para tendência",
        }[comparison.trend]
        current = (
            "ausente" if comparison.current is None else f"{comparison.current:g}"
        )
        return ElyraObservationV1(
            category="metric",
            evidencePath=evidence_path,
            text=(
                f"{label}: valor atual {current}, {trend_text}, com "
                f"{comparison.current_samples} dias presentes na janela atual."
            ),
        )

    @staticmethod
    def serialize_output(value: ElyraTextualOutputV1) -> str:
        return value.model_dump_json(by_alias=True)

    @staticmethod
    def validate_output(
        raw: str,
        request: ElyraTextualInputV1,
        correlation_id: str,
    ) -> ElyraOutputValidation:
        try:
            decoded = json.loads(raw)
            value = ElyraTextualOutputV1.model_validate(decoded)
        except (json.JSONDecodeError, ValidationError, TypeError):
            return ElyraOutputValidation(
                error_code=codes.ELYRA_OUTPUT_INVALID,
                reason=OUTPUT_INVALID_REASON,
            )

        if (
            value.correlation_id != correlation_id
            or value.source_report_schema_version != request.report.schema_version
            or value.source_analytics_version != request.report.analytics_version
        ):
            return ElyraOutputValidation(
                error_code=codes.ELYRA_OUTPUT_INVALID,
                reason=OUTPUT_INVALID_REASON,
            )
        return ElyraOutputValidation(value=value)


elyra_textual_service = ElyraTextualService()

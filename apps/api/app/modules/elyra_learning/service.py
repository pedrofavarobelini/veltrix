"""Boundary do learning governado Elyra.

Esta capability **nao possui store proprio**. Ela traduz uma submissao governada em
`TrainingCandidateProposal` e entrega ao Dataset Foundation que ja existe. Criar um
segundo Candidate Store duplicaria lifecycle, revogacao e auditoria — e a segunda
copia seria a que ninguem lembraria de revogar.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import ValidationError

from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.chat.schemas import ChatRequest
from app.modules.contracts import codes
from app.modules.elyra_learning.schemas import (
    ELYRA_LEARNING_CONTRACT_VERSION,
    ELYRA_LEARNING_MESSAGE,
    ELYRA_LEARNING_OUTPUT_SCHEMA_VERSION,
    ELYRA_LEARNING_POLICY_VERSION,
    REVOKE_OPERATION,
    SUBMIT_OPERATION,
    ElyraLearningOutputV1,
    ElyraLearningRevocationV1,
    ElyraLearningSubmissionV1,
)
from app.modules.training_data.schemas import (
    CandidateQualitySignals,
    SourceOutcome,
    TrainingCandidateProposal,
    TrainingEvidenceReference,
    TrainingPurpose,
    TrainingSourceType,
)

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")

ELYRA_LEARNING_TASK_LABEL = "elyra_wellbeing_aggregate"

CALLER_NOT_REGISTERED_REASON = (
    "O learning governado Elyra exige credencial registrada, vinculada ao "
    "project_id=elyra e ao papel common_consumer."
)
INVALID_INPUT_REASON = (
    "Payload incompatível com elyra-learning-input/v1; nenhum candidato foi criado."
)
CONSENT_REQUIRED_REASON = (
    "A submissão exige consentimento explícito de TREINO. Consentimento de "
    "inferência, captura, armazenamento ou compartilhamento não o substitui."
)
ELIGIBILITY_REQUIRED_REASON = (
    "A submissão exige declaração de elegibilidade aprovada pela política "
    f"{ELYRA_LEARNING_POLICY_VERSION}."
)
QUALITY_REQUIRED_REASON = (
    "A submissão exige resultado de qualidade aprovado em todos os gates nomeados."
)
PROVENANCE_REQUIRED_REASON = (
    "A submissão exige proveniência completa: origem, schema, versão analítica e "
    "versão de exportação."
)
FINGERPRINT_MISMATCH_REASON = (
    "Fingerprint declarado diverge do payload canônico sanitizado recebido; "
    "submissão negada sem criar candidato."
)
NOT_FOUND_REASON = (
    "Nenhum candidato Elyra corresponde ao fingerprint informado."
)
IDEMPOTENCY_CONFLICT_REASON = (
    "Idempotency key de learning já usada com payload diferente; requisição "
    "negada sem criar, autorizar ou revogar candidato."
)
INTERNAL_FAILURE_REASON = (
    "Falha interna controlada no contrato de learning Elyra; nenhum candidato "
    "foi criado, autorizado ou revogado."
)
TRAINING_NOT_SUPPORTED_REASON = (
    "Esta capability submete e revoga candidatos. Treino, fine-tuning e escrita "
    "em dataset genérico não existem neste contrato."
)


@dataclass(frozen=True)
class ElyraLearningValidation:
    submission: ElyraLearningSubmissionV1 | None = None
    revocation: ElyraLearningRevocationV1 | None = None
    error_code: str | None = None
    reason: str | None = None

    @property
    def valid(self) -> bool:
        return self.submission is not None or self.revocation is not None


def canonical_fingerprint(payload: dict) -> str:
    """SHA-256 do payload canonico sanitizado.

    Chaves ordenadas e separadores fixos para que Elyra e Veltrix cheguem ao
    mesmo digest a partir do mesmo conteudo — sem isso a idempotencia seria
    sensivel a ordem de serializacao.

    **Recebe o dicionario COMO CHEGOU DO FIO, nao o modelo validado.** O Pydantic
    coage `mean: float`, entao um `7` enviado pelo JavaScript viraria `7.0` e
    `json.dumps` escreveria `7.0` onde o `JSON.stringify` escreveu `7`: digests
    diferentes para conteudo identico, e toda submissao com media inteira seria
    recusada por `FINGERPRINT_MISMATCH`. O round-trip JSON do Python preserva a
    distincao int/float que veio do fio, e e por isso que o hash e calculado
    antes da validacao.
    """
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _completeness(submission: ElyraLearningSubmissionV1) -> float:
    """Fracao media de dias com dado sobre a janela declarada."""
    payload = submission.payload
    window = payload.days_in_window
    counts = (
        payload.days_with_mood,
        payload.days_with_anxiety,
        payload.days_with_energy,
        payload.days_with_sleep,
    )
    return round(sum(counts) / (len(counts) * window), 6)


def _evidence_strength(submission: ElyraLearningSubmissionV1) -> float:
    """Fracao de metricas que realmente tem amostra.

    Metrica sem amostra nao fortalece o candidato: ausencia de dado nao e zero,
    e tambem nao e evidencia.
    """
    payload = submission.payload
    aggregates = (
        payload.mood,
        payload.anxiety,
        payload.energy,
        payload.sleep_duration_minutes,
    )
    with_samples = sum(1 for item in aggregates if item.samples > 0)
    return round(with_samples / len(aggregates), 6)


class ElyraLearningService:
    """Capability estreita: submeter candidato governado e revoga-lo."""

    def validate_input(
        self,
        payload: ChatRequest,
        caller: AuthenticatedCallerContext,
    ) -> ElyraLearningValidation:
        if not (
            caller.identity_strength is IdentityStrength.REGISTERED
            and caller.project_id == "elyra"
            and caller.caller_role is CallerRole.COMMON_CONSUMER
            and caller.allowed_origins is not None
            and "elyra" in caller.allowed_origins
        ):
            return ElyraLearningValidation(
                error_code=codes.ELYRA_LEARNING_CALLER_NOT_REGISTERED,
                reason=CALLER_NOT_REGISTERED_REASON,
            )

        correlation = payload.correlation_id or ""
        idempotency = payload.idempotency_key or ""
        if not _IDENTIFIER.fullmatch(correlation) or not _IDENTIFIER.fullmatch(
            idempotency
        ):
            return ElyraLearningValidation(
                error_code=codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID,
                reason=INVALID_INPUT_REASON,
            )

        if (
            payload.message != ELYRA_LEARNING_MESSAGE
            or payload.mode != "tecnico"
            or payload.system_prompt is not None
            or payload.metadata is not None
            or payload.artifacts is not None
            or payload.context_from_memory
            or payload.allow_local_model
            or payload.allow_real_provider
        ):
            return ElyraLearningValidation(
                error_code=codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID,
                reason=INVALID_INPUT_REASON,
            )

        context = payload.context if isinstance(payload.context, dict) else None
        if context is None:
            return ElyraLearningValidation(
                error_code=codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID,
                reason=INVALID_INPUT_REASON,
            )

        operation = context.get("operation")
        if operation == REVOKE_OPERATION:
            try:
                revocation = ElyraLearningRevocationV1.model_validate(context)
            except ValidationError:
                return ElyraLearningValidation(
                    error_code=codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID,
                    reason=INVALID_INPUT_REASON,
                )
            return ElyraLearningValidation(revocation=revocation)

        if operation != SUBMIT_OPERATION:
            # Qualquer outra operacao — treinar, exportar dataset, consumir — nao
            # existe neste contrato e e recusada nominalmente.
            return ElyraLearningValidation(
                error_code=codes.ELYRA_LEARNING_OPERATION_NOT_SUPPORTED,
                reason=TRAINING_NOT_SUPPORTED_REASON,
            )

        try:
            submission = ElyraLearningSubmissionV1.model_validate(context)
        except ValidationError as exc:
            return ElyraLearningValidation(
                error_code=self._submission_error_code(exc),
                reason=self._submission_reason(exc),
            )

        declared = submission.fingerprint
        raw_payload = context.get("payload")
        if not isinstance(raw_payload, dict):
            return ElyraLearningValidation(
                error_code=codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID,
                reason=INVALID_INPUT_REASON,
            )
        recomputed = canonical_fingerprint(raw_payload)
        if declared != recomputed:
            return ElyraLearningValidation(
                error_code=codes.ELYRA_LEARNING_FINGERPRINT_MISMATCH,
                reason=FINGERPRINT_MISMATCH_REASON,
            )

        return ElyraLearningValidation(submission=submission)

    @staticmethod
    def _submission_error_code(error: ValidationError) -> str:
        """Traduz a falha de schema no requisito que faltou, nominalmente."""
        locations = {
            str(item.get("loc", ("",))[0]) for item in error.errors() if item.get("loc")
        }
        if "consent" in locations:
            return codes.ELYRA_LEARNING_TRAINING_CONSENT_REQUIRED
        if "eligibility" in locations:
            return codes.ELYRA_LEARNING_NOT_ELIGIBLE
        if "quality" in locations:
            return codes.ELYRA_LEARNING_QUALITY_GATE_FAILED
        if "provenance" in locations:
            return codes.ELYRA_LEARNING_PROVENANCE_REQUIRED
        return codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID

    @staticmethod
    def _submission_reason(error: ValidationError) -> str:
        locations = {
            str(item.get("loc", ("",))[0]) for item in error.errors() if item.get("loc")
        }
        if "consent" in locations:
            return CONSENT_REQUIRED_REASON
        if "eligibility" in locations:
            return ELIGIBILITY_REQUIRED_REASON
        if "quality" in locations:
            return QUALITY_REQUIRED_REASON
        if "provenance" in locations:
            return PROVENANCE_REQUIRED_REASON
        return INVALID_INPUT_REASON

    @staticmethod
    def build_proposal(
        submission: ElyraLearningSubmissionV1,
        credential_id: str,
    ) -> TrainingCandidateProposal:
        """Traduz a submissao para o vocabulario do Dataset Foundation.

        `input_features` e `target` sao numericos por construcao — o schema de
        origem nao tem campo de texto. O scanner de privacidade do Dataset
        Foundation roda por cima disso de qualquer forma, como segunda barreira.
        """
        payload = submission.payload
        return TrainingCandidateProposal(
            producer=credential_id,
            source_type=TrainingSourceType.ELYRA_REPORT_SNAPSHOT,
            project_id="elyra",
            task_type=ELYRA_LEARNING_TASK_LABEL,
            training_purpose=TrainingPurpose.EVALUATION_ONLY,
            input_features={
                "days_in_window": payload.days_in_window,
                "days_with_mood": payload.days_with_mood,
                "days_with_anxiety": payload.days_with_anxiety,
                "days_with_energy": payload.days_with_energy,
                "days_with_sleep": payload.days_with_sleep,
                "cycle_enabled": payload.cycle_enabled,
            },
            context_features={
                "analytics_version": submission.provenance.analytics_version,
                "export_schema_version": submission.provenance.export_schema_version,
                "policy_version": submission.eligibility.policy_version,
            },
            target={
                "mood": payload.mood.model_dump(mode="json"),
                "anxiety": payload.anxiety.model_dump(mode="json"),
                "energy": payload.energy.model_dump(mode="json"),
                "sleep_duration_minutes": payload.sleep_duration_minutes.model_dump(
                    mode="json"
                ),
            },
            evidence_refs=[
                TrainingEvidenceReference(
                    project_id="elyra",
                    source_type=TrainingSourceType.ELYRA_REPORT_SNAPSHOT,
                    # A evidencia e o fingerprint, nao o snapshot: o Veltrix
                    # nao consegue — e nao deve conseguir — resolver isso de volta
                    # para uma pessoa.
                    source_id=submission.fingerprint[:32],
                    source_schema_version=submission.provenance.source_schema_version,
                    policy_version=submission.eligibility.policy_version,
                    outcome=SourceOutcome.ACCEPTED,
                    content_signature="sha256:" + submission.fingerprint,
                    observed_at=submission.provenance.produced_at,
                    verified=True,
                )
            ],
            quality_signals=CandidateQualitySignals(
                # Proveniencia completa e exigida pelo contrato: se chegou aqui,
                # origem, schema, versao analitica e exportacao foram declarados.
                provenance_quality=1.0,
                evidence_strength=_evidence_strength(submission),
                completeness=_completeness(submission),
                source_reliability=1.0,
                outcome_known=True,
                qa_validated=True,
                outcome_consistent=True,
                contradiction_detected=False,
                qa_result="passed",
            ),
            derived_content_only=True,
            proposed_at=submission.provenance.produced_at,
        )

    @staticmethod
    def receipt(
        *,
        operation: str,
        correlation_id: str,
        candidate_id: str,
        lifecycle: str,
        duplicate: bool,
    ) -> ElyraLearningOutputV1:
        return ElyraLearningOutputV1(
            contractVersion=ELYRA_LEARNING_CONTRACT_VERSION,
            outputSchemaVersion=ELYRA_LEARNING_OUTPUT_SCHEMA_VERSION,
            operation=operation,
            correlationId=correlation_id,
            candidateId=candidate_id,
            lifecycle=lifecycle,
            duplicate=duplicate,
            policyVersion=ELYRA_LEARNING_POLICY_VERSION,
            trainingStarted=False,
            modelWeightsUpdated=False,
        )

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)


elyra_learning_service = ElyraLearningService()

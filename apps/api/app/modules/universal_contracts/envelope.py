"""PedroCore Integration Contract V1 — envelope comum.

Por que um envelope, e nao cinco contratos soltos
-------------------------------------------------

QEC, Execution Outcome e Learning Source precisam responder as mesmas perguntas
antes de qualquer coisa especifica: quem produziu, para qual projeto, sob qual
correlacao, em que versao, com qual identidade de evento. Repetir esses campos
em tres contratos convida os tres a divergirem — um ganha `producer`, outro
ganha `producer_id`, o terceiro esquece `correlation_id` — e a divergencia so
aparece quando alguem tenta correlacionar os tres.

O envelope existe porque a duplicacao ja seria real, e nao por simetria. A
prova disso e o precedente no proprio repositorio: `IntelligenceReportEnvelopeV2`
resolveu exatamente este problema para Report Intelligence, com o mesmo desenho
de payload selecionado por tipo declarado. Este contrato reaplica o padrao ja
comprovado, sem tocar naquele, que continua publico e intacto.

Nao e um god object: o envelope carrega identidade e correlacao, e delega TODO
o significado ao payload. Ele nao sabe o que e uma suite de teste nem o que e
uma fonte de aprendizado.

Autoridade
----------

O envelope declara `project_id`, mas quem decide o projeto e a credencial
registrada, resolvida server-side em `caller_identity`. O campo existe para ser
CONFERIDO contra a identidade real — divergencia e recusa, nao aceitacao do que
o payload afirma. Esta e a diferenca entre um campo declarado e um campo
confiavel.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.universal_contracts.execution_outcome import ExecutionOutcomeV1
from app.modules.universal_contracts.learning_source import LearningSourceV1
from app.modules.universal_contracts.quality_evidence import QualityEvidenceV1
from app.modules.universal_contracts.versioning import (
    EXECUTION_OUTCOME_V1,
    INTEGRATION_ENVELOPE_V1,
    LEARNING_SOURCE_V1,
    QUALITY_EVIDENCE_V1,
)

ShortText = Annotated[str, Field(min_length=1, max_length=128)]


class IntegrationPayloadType(str, Enum):
    """Qual contrato viaja dentro do envelope."""

    QUALITY_EVIDENCE = "quality_evidence"
    EXECUTION_OUTCOME = "execution_outcome"
    LEARNING_SOURCE = "learning_source"


IntegrationPayload: TypeAlias = QualityEvidenceV1 | ExecutionOutcomeV1 | LearningSourceV1

_PAYLOAD_MODEL_BY_TYPE: dict[IntegrationPayloadType, type[BaseModel]] = {
    IntegrationPayloadType.QUALITY_EVIDENCE: QualityEvidenceV1,
    IntegrationPayloadType.EXECUTION_OUTCOME: ExecutionOutcomeV1,
    IntegrationPayloadType.LEARNING_SOURCE: LearningSourceV1,
}

_CONTRACT_VERSION_BY_TYPE: dict[IntegrationPayloadType, str] = {
    IntegrationPayloadType.QUALITY_EVIDENCE: QUALITY_EVIDENCE_V1,
    IntegrationPayloadType.EXECUTION_OUTCOME: EXECUTION_OUTCOME_V1,
    IntegrationPayloadType.LEARNING_SOURCE: LEARNING_SOURCE_V1,
}


def payload_model_for(payload_type: IntegrationPayloadType) -> type[BaseModel]:
    """Modelo exigido para o tipo declarado."""
    return _PAYLOAD_MODEL_BY_TYPE[payload_type]


def contract_version_for(payload_type: IntegrationPayloadType) -> str:
    """Versao de contrato correspondente ao tipo declarado."""
    return _CONTRACT_VERSION_BY_TYPE[payload_type]


class PedroCoreIntegrationEnvelopeV1(BaseModel):
    """Envelope universal de integracao.

    Seleciona o payload ESTRITAMENTE pelo `payload_type` declarado. Nao ha
    inferencia por formato: um payload que "parece" evidencia de qualidade mas
    foi declarado como fonte de aprendizado e recusado, porque adivinhar o tipo
    e como uma governanca de aprendizado passa a aceitar o que nunca declarou.
    """

    model_config = ConfigDict(extra="forbid")

    envelope_version: Literal["pedrocore-integration/v1"] = INTEGRATION_ENVELOPE_V1
    event_id: ShortText
    payload_type: IntegrationPayloadType
    project_id: ShortText
    producer_id: ShortText
    correlation_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str | None = Field(default=None, max_length=128)
    submitted_at: datetime
    payload: IntegrationPayload

    @model_validator(mode="before")
    @classmethod
    def _select_payload_by_declared_type(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        try:
            payload_type = IntegrationPayloadType(value.get("payload_type"))
        except (TypeError, ValueError):
            # Tipo invalido: deixa a validacao normal do enum reportar o erro
            # com a mensagem correta, em vez de mascarar com KeyError.
            return value
        payload = value.get("payload")
        if isinstance(payload, BaseModel):
            return value
        parsed = dict(value)
        parsed["payload"] = payload_model_for(payload_type).model_validate(payload)
        return parsed

    @model_validator(mode="after")
    def _payload_must_match_declared_type(self) -> PedroCoreIntegrationEnvelopeV1:
        expected = payload_model_for(self.payload_type)
        if not isinstance(self.payload, expected):
            raise ValueError(
                f"payload nao corresponde ao payload_type declarado "
                f"('{self.payload_type.value}')"
            )
        expected_version = contract_version_for(self.payload_type)
        declared_version = getattr(self.payload, "contract_version", None)
        if declared_version != expected_version:
            raise ValueError(
                f"contract_version '{declared_version}' incompativel com "
                f"payload_type '{self.payload_type.value}'"
            )
        return self

    @model_validator(mode="after")
    def _submitted_at_requires_timezone(self) -> PedroCoreIntegrationEnvelopeV1:
        if self.submitted_at.tzinfo is None:
            raise ValueError("submitted_at deve incluir timezone")
        return self

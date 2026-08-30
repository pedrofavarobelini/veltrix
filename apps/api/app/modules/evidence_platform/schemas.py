"""Contratos internos da Evidence Platform.

O registro guarda **Operational Source**, e nunca Training Candidate. A
distincao esta no proprio tipo: `EvidenceRecord` nao tem elegibilidade,
autorizacao, proposito de treino nem ciclo de vida de candidato. Um registro
aqui e um fato guardado; virar exemplo de treino exige atravessar o Learning
Plane inteiro, depois e a parte.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

EVIDENCE_REGISTRY_POLICY_VERSION = "evidence-registry-v1"

ShortText = Annotated[str, Field(min_length=1, max_length=128)]
Signature = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]

# Um envelope legitimo de evidencia e pequeno: contagens, referencias e rotulos
# curtos. O limite existe para que "evidencia" nao vire um canal de upload.
MAX_EVIDENCE_PAYLOAD_BYTES = 64_000


class EvidenceKind(str, Enum):
    """Qual contrato universal originou o registro."""

    QUALITY_EVIDENCE = "quality_evidence"
    EXECUTION_OUTCOME = "execution_outcome"
    LEARNING_SOURCE = "learning_source"


class IngestionDecision(str, Enum):
    """O que aconteceu com a submissao.

    `DUPLICATE` nao e erro: e a resposta correta a um retry. Um consumidor que
    reenvia por timeout precisa distinguir "ja registrei isto" de "falhei", e
    tratar as duas como erro o levaria a duplicar de verdade.
    """

    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


class EvidenceRecord(BaseModel):
    """Uma evidencia registrada — fato operacional, nunca candidato.

    Ausencia de campos e parte do contrato: nao ha `eligibility`, `authorized`,
    `training_purpose`, `candidate_id` nem `lifecycle`.
    """

    model_config = ConfigDict(extra="forbid")

    policy_version: Literal["evidence-registry-v1"] = EVIDENCE_REGISTRY_POLICY_VERSION
    evidence_record_id: ShortText
    project_id: ShortText
    producer_id: ShortText
    kind: EvidenceKind
    event_id: ShortText
    correlation_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str | None = Field(default=None, max_length=128)
    contract_version: ShortText
    fingerprint: Signature
    submitted_at: datetime
    received_at: datetime
    payload: dict = Field(default_factory=dict)
    # Reafirmado no proprio registro para que nenhuma leitura futura possa
    # interpretar "evidencia guardada" como "candidato criado".
    promoted_to_training_candidate: Literal[False] = False
    automatic_collection_performed: Literal[False] = False


class PrivacyFindingRef(BaseModel):
    """Achado de privacidade: codigo, categoria e caminho — nunca o valor."""

    model_config = ConfigDict(extra="forbid")

    code: ShortText
    category: ShortText
    field_path: str = Field(..., min_length=1, max_length=512)


class EvidenceIngestionResult(BaseModel):
    """Resultado da ingestao, seguro para devolver ao consumidor."""

    model_config = ConfigDict(extra="forbid")

    decision: IngestionDecision
    evidence_record_id: str | None = None
    fingerprint: str | None = None
    error_code: str | None = None
    reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    privacy_findings: list[PrivacyFindingRef] = Field(default_factory=list)
    # Invariantes reafirmados na resposta: um consumidor que leia apenas o
    # resultado nao pode concluir que submeter evidencia treina alguma coisa.
    training_candidate_created: Literal[False] = False
    automatic_collection_performed: Literal[False] = False

"""Ingestao de evidencia — a porta de entrada universal do PedroCore.

Ordem do pipeline
-----------------

  1. limite de tamanho      (antes de qualquer parse)
  2. contrato universal      (versao, autoridade, forma, binding, capability)
  3. privacidade             (segredo, credencial, PII, financeiro, conteudo bruto)
  4. fingerprint             (derivado pelo servidor)
  5. idempotencia e dedup
  6. persistencia

O tamanho vem primeiro porque parsear 50 MB para depois recusar por tamanho ja
gastou a memoria que o limite existia para proteger.

A privacidade vem DEPOIS do contrato e ANTES da persistencia. Depois do
contrato porque um payload malformado nao merece varredura; antes da
persistencia porque um segredo gravado ja vazou, mesmo que apagado em seguida.

Invariante da Era 4
-------------------

Learning Source recebida vira **Operational Source** registrada. Nunca
Training Candidate. Nao existe, neste modulo, chamada alguma ao Learning Plane:
a promocao pertence a ele e acontece por decisao dele, nunca como efeito
colateral de uma ingestao.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

from app.modules.caller_identity.schemas import AuthenticatedCallerContext
from app.modules.evidence_platform.repository import (
    EvidenceRepository,
    InMemoryEvidenceRepository,
    PostgreSQLEvidenceRepository,
)
from app.modules.evidence_platform.schemas import (
    MAX_EVIDENCE_PAYLOAD_BYTES,
    EvidenceIngestionResult,
    EvidenceKind,
    EvidenceRecord,
    IngestionDecision,
    PrivacyFindingRef,
)
from app.modules.project_context.manifests import manifest_for
from app.modules.report_memory.repository import ReportMemoryRepositoryConfigurationError
from app.modules.report_memory.service import (
    FLAG_DATABASE_URL,
    MODE_MEMORY,
    MODE_POSTGRESQL,
    persistence_mode,
)
from app.modules.universal_contracts.privacy_patterns import detect
from app.modules.universal_contracts.service import universal_contract_service

EVIDENCE_PAYLOAD_TOO_LARGE = "EVIDENCE_PAYLOAD_TOO_LARGE"
EVIDENCE_PRIVACY_REJECTED = "EVIDENCE_PRIVACY_REJECTED"
EVIDENCE_IDEMPOTENCY_CONFLICT = "EVIDENCE_IDEMPOTENCY_CONFLICT"
EVIDENCE_REGISTRY_DISABLED = "EVIDENCE_REGISTRY_DISABLED"

_KIND_BY_PAYLOAD_TYPE = {
    "quality_evidence": EvidenceKind.QUALITY_EVIDENCE,
    "execution_outcome": EvidenceKind.EXECUTION_OUTCOME,
    "learning_source": EvidenceKind.LEARNING_SOURCE,
}


def _canonical(payload: object) -> bytes:
    """Serializacao estavel: mesma evidencia, mesmo fingerprint, sempre."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


class EvidenceIngestionService:
    """Servico de ingestao. Sem estado proprio: o estado vive no repositorio."""

    def __init__(self) -> None:
        self._override: EvidenceRepository | None = None

    # -- repositorio ------------------------------------------------------

    def set_repository(self, repository: EvidenceRepository | None) -> None:
        """Injeta um repositorio (teste). `None` volta ao modo do ambiente."""
        self._override = repository

    def _repository(self) -> EvidenceRepository | None:
        if self._override is not None:
            return self._override
        mode = persistence_mode()
        if mode == MODE_MEMORY:
            return _MEMORY_SINGLETON
        if mode == MODE_POSTGRESQL:
            database_url = (os.environ.get(FLAG_DATABASE_URL) or "").strip()
            if not database_url:
                raise ReportMemoryRepositoryConfigurationError(
                    f"{FLAG_DATABASE_URL} é obrigatória no modo postgresql."
                )
            return PostgreSQLEvidenceRepository(database_url)
        # `off` e `local_json`: evidencia nao usa arquivo solto em disco.
        return None

    def _required_repository(self) -> EvidenceRepository:
        repository = self._repository()
        if repository is None:
            raise ReportMemoryRepositoryConfigurationError(
                "Evidence Registry desabilitado; nenhum fallback foi aplicado."
            )
        return repository

    # -- ingestao ---------------------------------------------------------

    def ingest(
        self,
        raw_envelope: object,
        *,
        caller: AuthenticatedCallerContext,
    ) -> EvidenceIngestionResult:
        """Valida, deduplica e registra uma evidencia."""
        # 1. Tamanho antes do parse.
        try:
            encoded = _canonical(raw_envelope)
        except (TypeError, ValueError):
            return EvidenceIngestionResult(
                decision=IngestionDecision.REJECTED,
                error_code="CONTRACT_PAYLOAD_INVALID",
                reason="Envelope não é serializável como JSON.",
            )
        if len(encoded) > MAX_EVIDENCE_PAYLOAD_BYTES:
            return EvidenceIngestionResult(
                decision=IngestionDecision.REJECTED,
                error_code=EVIDENCE_PAYLOAD_TOO_LARGE,
                reason=(
                    f"Envelope excede {MAX_EVIDENCE_PAYLOAD_BYTES} bytes; "
                    "evidência transporta contagens e referências, não conteúdo."
                ),
            )

        # 2. Contrato universal. A identidade vem da credencial, nunca do payload.
        project_id = (caller.project_id or "").strip()
        validation = universal_contract_service.validate_envelope(
            raw_envelope,
            authenticated_project_id=project_id,
            authenticated_producer_id=caller.credential_id,
            manifest=manifest_for(project_id),
        )
        if not validation.accepted or validation.envelope is None:
            return EvidenceIngestionResult(
                decision=IngestionDecision.REJECTED,
                error_code=validation.error_code,
                reason=validation.reason,
                warnings=validation.warnings,
            )
        envelope = validation.envelope

        # 3. Privacidade antes de qualquer escrita.
        payload_dict = envelope.payload.model_dump(mode="json")
        findings = detect(payload_dict, root="evidence")
        if findings:
            return EvidenceIngestionResult(
                decision=IngestionDecision.REJECTED,
                error_code=EVIDENCE_PRIVACY_REJECTED,
                reason=(
                    "Evidência contém dado sensível e foi recusada: "
                    + ", ".join(sorted({code for code, _, _ in findings}))
                ),
                warnings=validation.warnings,
                privacy_findings=[
                    PrivacyFindingRef(code=code, category=category, field_path=path)
                    for code, category, path in findings
                ],
            )

        # 4. Fingerprint derivado pelo servidor — nunca aceito do produtor.
        fingerprint = "sha256:" + hashlib.sha256(_canonical(payload_dict)).hexdigest()
        kind = _KIND_BY_PAYLOAD_TYPE[envelope.payload_type.value]

        repository = self._required_repository()

        # 5. Idempotencia antes de dedup: a chave e a promessa explicita do
        #    consumidor, e ela vale mesmo que o conteudo tenha mudado.
        if envelope.idempotency_key:
            existing = repository.find_by_idempotency_key(
                project_id, envelope.idempotency_key
            )
            if existing is not None:
                if existing.fingerprint != fingerprint:
                    # Mesma chave, conteudo diferente: nao e retry, e colisao.
                    # Aceitar sobrescreveria silenciosamente um fato ja gravado.
                    return EvidenceIngestionResult(
                        decision=IngestionDecision.REJECTED,
                        error_code=EVIDENCE_IDEMPOTENCY_CONFLICT,
                        reason=(
                            "idempotency_key já registrada com conteúdo diferente; "
                            "reuso de chave não é permitido."
                        ),
                        warnings=validation.warnings,
                    )
                return EvidenceIngestionResult(
                    decision=IngestionDecision.DUPLICATE,
                    evidence_record_id=existing.evidence_record_id,
                    fingerprint=existing.fingerprint,
                    warnings=validation.warnings,
                )

        duplicate = repository.find_by_fingerprint(project_id, kind, fingerprint)
        if duplicate is not None:
            return EvidenceIngestionResult(
                decision=IngestionDecision.DUPLICATE,
                evidence_record_id=duplicate.evidence_record_id,
                fingerprint=duplicate.fingerprint,
                warnings=validation.warnings,
            )

        # 6. Persistencia.
        record = EvidenceRecord(
            evidence_record_id="evidence-" + fingerprint.removeprefix("sha256:")[:24],
            project_id=project_id,
            producer_id=caller.credential_id,
            kind=kind,
            event_id=envelope.event_id,
            correlation_id=envelope.correlation_id,
            idempotency_key=envelope.idempotency_key,
            contract_version=getattr(envelope.payload, "contract_version", "unknown"),
            fingerprint=fingerprint,
            submitted_at=envelope.submitted_at,
            received_at=datetime.now(timezone.utc),
            payload=payload_dict,
        )
        stored = repository.add(record)
        if not stored:
            return EvidenceIngestionResult(
                decision=IngestionDecision.DUPLICATE,
                evidence_record_id=record.evidence_record_id,
                fingerprint=record.fingerprint,
                warnings=validation.warnings,
            )

        return EvidenceIngestionResult(
            decision=IngestionDecision.ACCEPTED,
            evidence_record_id=record.evidence_record_id,
            fingerprint=record.fingerprint,
            warnings=validation.warnings,
        )

    # -- consulta ---------------------------------------------------------

    def list_evidence(
        self,
        project_id: str,
        *,
        kind: EvidenceKind | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[EvidenceRecord]:
        return self._required_repository().list(
            project_id, kind=kind, limit=limit, offset=offset
        )

    def count_evidence(
        self, project_id: str, *, kind: EvidenceKind | None = None
    ) -> int:
        return self._required_repository().count(project_id, kind=kind)


_MEMORY_SINGLETON = InMemoryEvidenceRepository()

evidence_ingestion_service = EvidenceIngestionService()

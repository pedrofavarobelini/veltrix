"""API de ingestao de evidencia.

Rotas ADITIVAS: nenhuma rota existente foi alterada ou removida. A autenticacao
reutiliza `authorize_technical_request`, o mesmo mecanismo das demais APIs
tecnicas — nao ha um segundo jeito de autenticar no mesmo processo.

Codigos HTTP e o que significam para o integrador:

  201  evidencia registrada
  200  duplicata reconhecida — resposta CORRETA a um retry, nao erro
  400  contrato invalido, privacidade recusada ou payload excessivo
  409  `idempotency_key` reusada com conteudo diferente
  503  Evidence Registry desabilitado (fail-closed, sem fallback)

A duplicata devolve 200 e nao 4xx de proposito: um consumidor que reenvia por
timeout precisa distinguir "ja registrei isto" de "falhei", e tratar as duas
como erro o levaria a duplicar de verdade.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.modules.caller_identity.technical_api import (
    authorize_technical_request,
    operational_persistence_error,
)
from app.modules.contracts import codes
from app.modules.evidence_platform.schemas import (
    EvidenceIngestionResult,
    EvidenceKind,
    IngestionDecision,
)
from app.modules.evidence_platform.service import (
    EVIDENCE_IDEMPOTENCY_CONFLICT,
    evidence_ingestion_service,
)
from app.modules.resilience.reconciliation import (
    ReconciliationReport,
    ReconciliationRequest,
    reconciliation_service,
)
from app.modules.report_memory.repository import (
    ReportMemoryRepositoryConfigurationError,
    ReportMemoryRepositoryError,
)

router = APIRouter(tags=["Evidence Platform"])

_STATUS_BY_DECISION = {
    IngestionDecision.ACCEPTED: 201,
    IngestionDecision.DUPLICATE: 200,
}


@router.post(
    "/evidence/{project_id}",
    response_model=EvidenceIngestionResult,
    summary="Registra uma evidência universal (QEC, Execution Outcome ou Learning Source)",
)
def ingest_evidence(project_id: str, payload: dict, request: Request):
    error, _warnings, caller = authorize_technical_request(request, project_id)
    if error is not None or caller is None:
        return error

    try:
        result = evidence_ingestion_service.ingest(payload, caller=caller)
    except ReportMemoryRepositoryConfigurationError:
        return operational_persistence_error(codes.EVIDENCE_PERSISTENCE_UNAVAILABLE)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.EVIDENCE_PERSISTENCE_UNAVAILABLE)

    if result.decision is IngestionDecision.REJECTED:
        status_code = 409 if result.error_code == EVIDENCE_IDEMPOTENCY_CONFLICT else 400
        return JSONResponse(
            status_code=status_code, content=result.model_dump(mode="json")
        )
    return JSONResponse(
        status_code=_STATUS_BY_DECISION[result.decision],
        content=result.model_dump(mode="json"),
    )


@router.get(
    "/evidence/{project_id}",
    summary="Lista evidências registradas do projeto",
)
def list_evidence(
    project_id: str,
    request: Request,
    kind: EvidenceKind | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    error, _warnings, caller = authorize_technical_request(request, project_id)
    if error is not None or caller is None:
        return error

    try:
        records = evidence_ingestion_service.list_evidence(
            project_id, kind=kind, limit=limit, offset=offset
        )
        total = evidence_ingestion_service.count_evidence(project_id, kind=kind)
    except ReportMemoryRepositoryConfigurationError:
        return operational_persistence_error(codes.EVIDENCE_PERSISTENCE_UNAVAILABLE)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.EVIDENCE_PERSISTENCE_UNAVAILABLE)

    return {
        "status": "ok",
        "project_id": project_id,
        "total": total,
        "items": [record.model_dump(mode="json") for record in records],
        # Reafirmado na listagem: evidencia guardada nao e candidato criado.
        "training_candidates_created": 0,
        "automatic_collection_performed": False,
    }


@router.post(
    "/evidence/{project_id}/reconcile",
    response_model=ReconciliationReport,
    summary="Informa quais idempotency_keys o PedroCore já possui",
)
def reconcile_evidence(project_id: str, payload: ReconciliationRequest, request: Request):
    """Consulta de LEITURA — perguntar nunca faz o servidor passar a ter."""
    error, _warnings, caller = authorize_technical_request(request, project_id)
    if error is not None or caller is None:
        return error
    try:
        return reconciliation_service.reconcile(project_id, payload)
    except ReportMemoryRepositoryConfigurationError:
        return operational_persistence_error(codes.EVIDENCE_PERSISTENCE_UNAVAILABLE)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.EVIDENCE_PERSISTENCE_UNAVAILABLE)

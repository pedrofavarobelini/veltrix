from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.modules.caller_identity.technical_api import (
    authorize_technical_request,
    operational_persistence_error,
    validate_producer,
)
from app.modules.contracts import codes
from app.modules.operational_memory.schemas import (
    LearningCandidateInput,
    LearningCandidateResponse,
    MemoryLifecycle,
    OperationalMemoryDeleteResponse,
    OperationalMemoryPageResponse,
    PatternType,
)
from app.modules.operational_memory.service import (
    OperationalEvidenceError,
    operational_memory_service,
)
from app.modules.report_memory.repository import ReportMemoryRepositoryError

router = APIRouter(tags=["Operational Memory"])


def _evidence_error(reason: str) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "status": "blocked",
            "error_code": codes.OPERATIONAL_EVIDENCE_NOT_FOUND,
            "blocked_reason": reason,
            "warning_codes": [codes.OPERATIONAL_EVIDENCE_NOT_FOUND],
        },
    )


@router.post(
    "/operational-memory/candidates",
    response_model=LearningCandidateResponse,
)
def ingest_learning_candidate(payload: LearningCandidateInput, request: Request):
    error, warnings, caller = authorize_technical_request(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error
    try:
        candidate, memory, duplicate, memory_warnings = operational_memory_service.ingest_candidate(
            payload, caller
        )
    except OperationalEvidenceError as exc:
        return _evidence_error(str(exc))
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE)
    warnings.extend(memory_warnings)
    return LearningCandidateResponse(
        status="duplicate" if duplicate else ("ok" if candidate else "disabled"),
        stored=candidate is not None and not duplicate,
        duplicate=duplicate,
        candidate=candidate,
        memory=memory,
        warnings=warnings,
    )


@router.get(
    "/operational-memory/{project_id}",
    response_model=OperationalMemoryPageResponse,
)
def query_operational_memory(
    project_id: str,
    request: Request,
    pattern_type: PatternType | None = Query(default=None),
    lifecycle: MemoryLifecycle | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    error, warnings, _caller = authorize_technical_request(request, project_id)
    if error is not None:
        return error
    if not operational_memory_service.enabled():
        return OperationalMemoryPageResponse(
            status="disabled",
            project_id=project_id.strip().lower(),
            limit=limit,
            offset=offset,
            warnings=warnings,
        )
    try:
        items, total = operational_memory_service.page(
            project_id,
            pattern_type=pattern_type,
            lifecycle=lifecycle,
            limit=limit,
            offset=offset,
        )
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE)
    return OperationalMemoryPageResponse(
        project_id=project_id.strip().lower(),
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        warnings=warnings,
    )


@router.delete(
    "/operational-memory/{project_id}",
    response_model=OperationalMemoryDeleteResponse,
)
def delete_operational_memory(project_id: str, request: Request):
    error, warnings, _caller = authorize_technical_request(request, project_id)
    if error is not None:
        return error
    try:
        candidates, memories = operational_memory_service.delete_project(project_id)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE)
    return OperationalMemoryDeleteResponse(
        project_id=project_id.strip().lower(),
        deleted_candidates=candidates,
        deleted_memories=memories,
        warnings=warnings,
    )

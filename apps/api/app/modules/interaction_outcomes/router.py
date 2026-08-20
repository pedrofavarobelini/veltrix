from fastapi import APIRouter, Query, Request

from app.modules.caller_identity.technical_api import (
    authorize_technical_request,
    operational_persistence_error,
    validate_producer,
)
from app.modules.contracts import codes
from app.modules.interaction_outcomes.schemas import (
    InteractionOutcomeDeleteResponse,
    InteractionOutcomeIngestResponse,
    InteractionOutcomeInput,
    InteractionOutcomePageResponse,
)
from app.modules.interaction_outcomes.service import interaction_outcome_service
from app.modules.report_memory.repository import ReportMemoryRepositoryError

router = APIRouter(tags=["Interaction Outcomes"])


@router.post(
    "/interaction-outcomes",
    response_model=InteractionOutcomeIngestResponse,
)
def ingest_interaction_outcome(payload: InteractionOutcomeInput, request: Request):
    error, warnings, caller = authorize_technical_request(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error

    try:
        outcome, duplicate, ingest_warnings = interaction_outcome_service.ingest(payload, caller)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.INTERACTION_OUTCOME_PERSISTENCE_UNAVAILABLE)
    warnings.extend(ingest_warnings)
    return InteractionOutcomeIngestResponse(
        status="duplicate" if duplicate else ("ok" if outcome else "disabled"),
        stored=outcome is not None and not duplicate,
        duplicate=duplicate,
        outcome=outcome,
        warnings=warnings,
    )


@router.get(
    "/interaction-outcomes/{project_id}",
    response_model=InteractionOutcomePageResponse,
)
def query_interaction_outcomes(
    project_id: str,
    request: Request,
    conversation_id: str | None = Query(default=None, min_length=1, max_length=128),
    message_id: str | None = Query(default=None, min_length=1, max_length=128),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    error, warnings, _caller = authorize_technical_request(request, project_id)
    if error is not None:
        return error
    if not interaction_outcome_service.enabled():
        return InteractionOutcomePageResponse(
            status="disabled",
            project_id=project_id.strip().lower(),
            limit=limit,
            offset=offset,
            warnings=warnings,
        )
    try:
        items, total = interaction_outcome_service.page(
            project_id,
            conversation_id=conversation_id,
            message_id=message_id,
            limit=limit,
            offset=offset,
        )
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.INTERACTION_OUTCOME_PERSISTENCE_UNAVAILABLE)
    return InteractionOutcomePageResponse(
        project_id=project_id.strip().lower(),
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        warnings=warnings,
    )


@router.delete(
    "/interaction-outcomes/{project_id}",
    response_model=InteractionOutcomeDeleteResponse,
)
def delete_interaction_outcomes(project_id: str, request: Request):
    error, warnings, _caller = authorize_technical_request(request, project_id)
    if error is not None:
        return error
    try:
        deleted = interaction_outcome_service.delete_project(project_id)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.INTERACTION_OUTCOME_PERSISTENCE_UNAVAILABLE)
    return InteractionOutcomeDeleteResponse(
        project_id=project_id.strip().lower(),
        deleted=deleted,
        warnings=warnings,
    )

from fastapi import APIRouter, Request

from app.modules.caller_identity.technical_api import (
    authorize_technical_request,
    operational_persistence_error,
    validate_producer,
)
from app.modules.contracts import codes
from app.modules.report_memory.repository import ReportMemoryRepositoryError
from app.modules.retrieval.schemas import RetrievalQuery, RetrievalResponse
from app.modules.retrieval.service import retrieval_service

router = APIRouter(tags=["Operational Memory Retrieval"])


@router.post("/operational-memory/retrieve", response_model=RetrievalResponse)
def retrieve_operational_memory(payload: RetrievalQuery, request: Request):
    error, warnings, caller = authorize_technical_request(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error
    try:
        response = retrieval_service.retrieve(payload)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE)
    response.warnings.extend(warnings)
    return response

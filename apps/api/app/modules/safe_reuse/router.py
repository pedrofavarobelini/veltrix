from fastapi import APIRouter, Request

from app.modules.caller_identity.technical_api import (
    authorize_technical_request,
    operational_persistence_error,
    validate_producer,
)
from app.modules.contracts import codes
from app.modules.report_memory.repository import ReportMemoryRepositoryError
from app.modules.safe_reuse.schemas import ReuseDecision, ReuseEvaluationRequest
from app.modules.safe_reuse.service import safe_reuse_service

router = APIRouter(tags=["Safe Reuse"])


@router.post("/safe-reuse/evaluate", response_model=ReuseDecision)
def evaluate_safe_reuse(payload: ReuseEvaluationRequest, request: Request):
    error, _warnings, caller = authorize_technical_request(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error
    try:
        return safe_reuse_service.evaluate(payload)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE)

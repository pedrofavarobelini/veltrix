from fastapi import APIRouter, Request

from app.modules.caller_identity.technical_api import (
    authorize_technical_request,
    validate_producer,
)
from app.modules.risk_engine.schemas import RiskAssessment, RiskRequest
from app.modules.risk_engine.service import risk_engine_foundation_service

router = APIRouter(tags=["Execution Risk Engine"])


@router.post("/risk/foundation/analyze", response_model=RiskAssessment)
def analyze_risk_foundation(payload: RiskRequest, request: Request):
    error, _warnings, caller = authorize_technical_request(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error
    return risk_engine_foundation_service.analyze(payload)

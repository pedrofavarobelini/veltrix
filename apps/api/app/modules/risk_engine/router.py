from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.modules.caller_identity.technical_api import (
    authorize_technical_request,
    operational_persistence_error,
    validate_producer,
)
from app.modules.contracts import codes
from app.modules.report_memory.repository import ReportMemoryRepositoryError
from app.modules.risk_engine.schemas import RiskAssessment, RiskRequest
from app.modules.risk_engine.pre_execution_schemas import PreExecutionRiskAnalysis
from app.modules.risk_engine.pre_execution_service import pre_execution_risk_service
from app.modules.risk_engine.post_execution_schemas import ExecutionEvidence, PostExecutionOutcome
from app.modules.risk_engine.post_execution_service import post_execution_service
from app.modules.risk_engine.execution_contract_schemas import (
    ContractIssueResponse,
    ContractValidation,
    ContractValidationRequest,
    HumanOverrideRequest,
    HumanReviewRecord,
)
from app.modules.risk_engine.execution_contract_service import (
    ContractConfigurationError,
    execution_contract_service,
)
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


@router.post("/risk/analyze", response_model=PreExecutionRiskAnalysis)
def analyze_pre_execution_risk(payload: RiskRequest, request: Request):
    error, _warnings, caller = authorize_technical_request(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error
    try:
        return pre_execution_risk_service.analyze(payload)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE)


def _contract_configuration_error() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "status": "blocked",
            "error_code": codes.RISK_CONTRACT_CONFIGURATION_INVALID,
            "blocked_reason": "Assinatura de contratos de risco não está configurada com segurança.",
            "warning_codes": [codes.RISK_CONTRACT_CONFIGURATION_INVALID],
        },
    )


@router.post("/risk/contracts", response_model=ContractIssueResponse)
def issue_execution_contract(payload: RiskRequest, request: Request):
    error, _warnings, caller = authorize_technical_request(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error
    try:
        return ContractIssueResponse(contract=execution_contract_service.issue(payload))
    except ContractConfigurationError:
        return _contract_configuration_error()
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE)


@router.post("/risk/contracts/validate", response_model=ContractValidation)
def validate_execution_contract(payload: ContractValidationRequest, request: Request):
    error, _warnings, caller = authorize_technical_request(request, payload.contract.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error
    nested_producer_error = validate_producer(caller, payload.current_request.producer)
    if nested_producer_error is not None:
        return nested_producer_error
    try:
        return execution_contract_service.validate(payload)
    except ContractConfigurationError:
        return _contract_configuration_error()


@router.post("/risk/contracts/override", response_model=HumanReviewRecord)
def override_execution_contract(payload: HumanOverrideRequest, request: Request):
    error, _warnings, caller = authorize_technical_request(request, payload.contract.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error
    nested_producer_error = validate_producer(caller, payload.current_request.producer)
    if nested_producer_error is not None:
        return nested_producer_error
    if not execution_contract_service.reviewer_authorized(caller):
        return JSONResponse(
            status_code=403,
            content={
                "status": "blocked",
                "error_code": codes.RISK_OVERRIDE_NOT_AUTHORIZED,
                "blocked_reason": "A credencial autenticada não está autorizada para override.",
                "warning_codes": [codes.RISK_OVERRIDE_NOT_AUTHORIZED],
            },
        )
    try:
        return execution_contract_service.override(payload, caller)
    except ContractConfigurationError:
        return _contract_configuration_error()


@router.post("/risk/execution-outcomes", response_model=PostExecutionOutcome)
def record_execution_outcome(payload: ExecutionEvidence, request: Request):
    error, _warnings, caller = authorize_technical_request(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error
    nested_producer_error = validate_producer(caller, payload.current_request.producer)
    if nested_producer_error is not None:
        return nested_producer_error
    normalized_project = payload.project_id.strip().lower()
    if (
        payload.contract.project_id != normalized_project
        or payload.current_request.project_id.strip().lower() != normalized_project
    ):
        return JSONResponse(
            status_code=403,
            content={
                "status": "blocked",
                "error_code": codes.EXECUTION_EVIDENCE_SCOPE_MISMATCH,
                "blocked_reason": "Contrato, contexto e evidência devem pertencer ao mesmo projeto.",
                "warning_codes": [codes.EXECUTION_EVIDENCE_SCOPE_MISMATCH],
            },
        )
    try:
        return post_execution_service.process(payload, caller)
    except ContractConfigurationError:
        return _contract_configuration_error()
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE)

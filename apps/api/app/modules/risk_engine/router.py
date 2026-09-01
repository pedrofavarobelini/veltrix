from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.modules.caller_identity.technical_api import (
    authorize_technical_request,
    operational_persistence_error,
    validate_producer,
)
from app.modules.contracts import codes
from app.modules.report_memory.repository import ReportMemoryRepositoryError
from app.modules.risk_engine.repository import RiskRepositoryError
from app.modules.risk_engine.schemas import RiskAssessment, RiskRequest
from app.modules.risk_engine.pre_execution_schemas import PreExecutionRiskAnalysis
from app.modules.risk_engine.pre_execution_service import pre_execution_risk_service
from app.modules.risk_engine.post_execution_schemas import ExecutionEvidence, PostExecutionOutcome
from app.modules.risk_engine.post_execution_service import post_execution_service
from app.modules.risk_engine.historical_schemas import (
    HistoricalBenchmarkRequest,
    HistoricalBenchmarkResult,
    HistoricalRiskQuery,
    HistoricalRiskSummary,
)
from app.modules.risk_engine.historical_service import historical_risk_service
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
from app.modules.risk_engine.universal_contract import (
    RISK_CONTRACT_AUTHORITY_VIOLATION,
    RISK_CONTRACT_CAPABILITY_NOT_DECLARED,
    RISK_CONTRACT_MANIFEST_MISSING,
    RiskContractAnalysisResponse,
    RiskContractSubmission,
    RiskRequestContractV1,
    validate_risk_contract,
)

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


# Codigos de autoridade e de capability sao 403: o pedido foi entendido e
# recusado por quem o enviou nao poder pedir aquilo. Versao e forma sao 422: o
# pedido nao foi entendido. Misturar os dois faria um integrador procurar erro
# de digitacao onde havia falta de permissao.
_RISK_CONTRACT_STATUS = {
    RISK_CONTRACT_AUTHORITY_VIOLATION: 403,
    RISK_CONTRACT_CAPABILITY_NOT_DECLARED: 403,
    RISK_CONTRACT_MANIFEST_MISSING: 403,
}


@router.post("/risk/universal/analyze", response_model=RiskContractAnalysisResponse)
def analyze_universal_risk_contract(payload: RiskContractSubmission, request: Request):
    """Submissao de risco pelo contrato universal `pedrocore-risk-request/v1`.

    Porta operacional do Stage R4. O consumidor declara FATO — operacao,
    alvos, ambiente, permissoes, contexto — e nunca veredito: `gate`, `safe`,
    `approved`, `risk_level`, `override` e afins sao recusados pela fronteira
    de autoridade, em qualquer profundidade do payload.

    A identidade nao vem do contrato: `producer` e `project_id` sao conferidos
    contra a credencial antes de chegarem ao motor. O motor e o mesmo de
    `/risk/analyze` — este e um contrato novo para a mesma politica, nao uma
    politica nova.
    """
    error, _warnings, caller = authorize_technical_request(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error

    validation = validate_risk_contract(
        payload.contract,
        authenticated_project_id=payload.project_id,
        authenticated_producer_id=payload.producer,
    )
    if not validation.accepted:
        code = validation.error_code or RISK_CONTRACT_AUTHORITY_VIOLATION
        return JSONResponse(
            status_code=_RISK_CONTRACT_STATUS.get(code, 422),
            content={
                "status": "blocked",
                "error_code": code,
                "blocked_reason": validation.reason,
                "warning_codes": [code],
                "authority_violations": validation.authority_violations,
            },
        )

    contract: RiskRequestContractV1 = validation.contract
    adapted = RiskRequest.model_validate(
        contract.to_risk_request_payload(
            producer=payload.producer, project_id=payload.project_id
        )
    )
    try:
        analysis = pre_execution_risk_service.analyze(adapted)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE)
    return RiskContractAnalysisResponse(analysis=analysis)


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


@router.post("/risk/history/query", response_model=HistoricalRiskSummary)
def query_historical_risk(payload: HistoricalRiskQuery, request: Request):
    error, _warnings, caller = authorize_technical_request(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error
    try:
        return historical_risk_service.summarize(payload)
    except RiskRepositoryError:
        # Repositorio proprio de risco configurado e indisponivel. Fail-closed:
        # devolver "sem historico" faria a consulta parecer segura quando ela
        # apenas nao conseguiu ler. A mensagem e o codigo ja existente; nenhum
        # detalhe do banco atravessa a fronteira da API.
        return operational_persistence_error(codes.RISK_HISTORY_PERSISTENCE_UNAVAILABLE)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE)


@router.post("/risk/history/benchmark", response_model=HistoricalBenchmarkResult)
def benchmark_historical_risk(payload: HistoricalBenchmarkRequest, request: Request):
    error, _warnings, caller = authorize_technical_request(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error
    try:
        return historical_risk_service.benchmark(payload)
    except RiskRepositoryError:
        return operational_persistence_error(codes.RISK_HISTORY_PERSISTENCE_UNAVAILABLE)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(codes.OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE)

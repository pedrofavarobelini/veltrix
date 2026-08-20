from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.modules.caller_identity.schemas import AuthenticatedCallerContext
from app.modules.caller_identity.technical_api import (
    authorize_technical_request,
    authorization_error,
    operational_persistence_error,
    validate_producer,
)
from app.modules.contracts import codes
from app.modules.report_memory.repository import ReportMemoryRepositoryError
from app.modules.training_data.acquisition import (
    TrainingCandidateTransitionError,
    training_candidate_service,
)
from app.modules.training_data.adapters import TrainingSourceSelectionError
from app.modules.training_data.schemas import (
    CandidateLifecycle,
    DatasetReadinessReport,
    TrainingAuthorizationRequest,
    TrainingCandidateMutationResponse,
    TrainingCandidatePageResponse,
    TrainingCandidateReviewRequest,
    TrainingCandidateStatusRequest,
    TrainingPurpose,
    TrainingSourceSelection,
    TrainingSourceType,
)

router = APIRouter(tags=["Training Candidate Acquisition"])


def _admin(
    request: Request,
    project_id: str,
) -> tuple[JSONResponse | None, AuthenticatedCallerContext | None]:
    error, _warnings, caller = authorize_technical_request(request, project_id)
    if error is not None or caller is None:
        return error, None
    if not training_candidate_service.admin_authorized(caller):
        return (
            authorization_error(
                codes.TRAINING_CANDIDATE_ADMIN_REQUIRED,
                "A credencial autenticada não possui capability training_data_admin.",
            ),
            None,
        )
    return None, caller


def _transition_error(exc: TrainingCandidateTransitionError) -> JSONResponse:
    status_code = 404 if exc.code == "CANDIDATE_NOT_FOUND" else 409
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "blocked",
            "error_code": codes.TRAINING_CANDIDATE_TRANSITION_REJECTED,
            "blocked_reason": "Transição de lifecycle rejeitada pela policy.",
            "reason_codes": exc.reason_codes,
            "warning_codes": [codes.TRAINING_CANDIDATE_TRANSITION_REJECTED],
        },
    )


@router.post(
    "/training-candidates/select",
    response_model=TrainingCandidateMutationResponse,
)
def select_training_candidate(payload: TrainingSourceSelection, request: Request):
    error, _warnings, caller = authorize_technical_request(request, payload.project_id)
    if error is not None or caller is None:
        return error
    producer_error = validate_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error
    try:
        record, duplicate = training_candidate_service.select(payload, caller)
    except TrainingSourceSelectionError:
        return JSONResponse(
            status_code=404,
            content={
                "status": "blocked",
                "error_code": codes.TRAINING_CANDIDATE_SOURCE_NOT_FOUND,
                "blocked_reason": "Fonte operacional elegível não encontrada neste projeto.",
                "warning_codes": [codes.TRAINING_CANDIDATE_SOURCE_NOT_FOUND],
            },
        )
    except ReportMemoryRepositoryError:
        return operational_persistence_error(
            codes.TRAINING_CANDIDATE_PERSISTENCE_UNAVAILABLE
        )
    return TrainingCandidateMutationResponse(
        stored=not duplicate,
        duplicate=duplicate,
        record=record,
    )


@router.post(
    "/training-candidates/{candidate_id}/authorize",
    response_model=TrainingCandidateMutationResponse,
)
def authorize_training_candidate(
    candidate_id: str,
    payload: TrainingAuthorizationRequest,
    request: Request,
):
    error, caller = _admin(request, payload.project_id)
    if error is not None or caller is None:
        return error
    try:
        record = training_candidate_service.authorize(candidate_id, payload, caller)
    except TrainingCandidateTransitionError as exc:
        return _transition_error(exc)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(
            codes.TRAINING_CANDIDATE_PERSISTENCE_UNAVAILABLE
        )
    return TrainingCandidateMutationResponse(stored=True, record=record)


@router.post(
    "/training-candidates/{candidate_id}/review",
    response_model=TrainingCandidateMutationResponse,
)
def review_training_candidate(
    candidate_id: str,
    payload: TrainingCandidateReviewRequest,
    request: Request,
):
    error, caller = _admin(request, payload.project_id)
    if error is not None or caller is None:
        return error
    try:
        record = training_candidate_service.review(candidate_id, payload, caller)
    except TrainingCandidateTransitionError as exc:
        return _transition_error(exc)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(
            codes.TRAINING_CANDIDATE_PERSISTENCE_UNAVAILABLE
        )
    return TrainingCandidateMutationResponse(stored=True, record=record)


@router.post(
    "/training-candidates/{candidate_id}/exclude",
    response_model=TrainingCandidateMutationResponse,
)
def exclude_training_candidate(
    candidate_id: str,
    payload: TrainingCandidateStatusRequest,
    request: Request,
):
    error, caller = _admin(request, payload.project_id)
    if error is not None or caller is None:
        return error
    try:
        record = training_candidate_service.exclude(candidate_id, payload, caller)
    except TrainingCandidateTransitionError as exc:
        return _transition_error(exc)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(
            codes.TRAINING_CANDIDATE_PERSISTENCE_UNAVAILABLE
        )
    return TrainingCandidateMutationResponse(stored=True, record=record)


@router.post(
    "/training-candidates/{candidate_id}/revoke",
    response_model=TrainingCandidateMutationResponse,
)
def revoke_training_candidate(
    candidate_id: str,
    payload: TrainingCandidateStatusRequest,
    request: Request,
):
    error, caller = _admin(request, payload.project_id)
    if error is not None or caller is None:
        return error
    try:
        record = training_candidate_service.revoke(candidate_id, payload, caller)
    except TrainingCandidateTransitionError as exc:
        return _transition_error(exc)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(
            codes.TRAINING_CANDIDATE_PERSISTENCE_UNAVAILABLE
        )
    return TrainingCandidateMutationResponse(stored=True, record=record)


@router.get(
    "/training-candidates/{project_id}/readiness",
    response_model=DatasetReadinessReport,
)
def training_candidate_readiness(project_id: str, request: Request):
    error, caller = _admin(request, project_id)
    if error is not None or caller is None:
        return error
    try:
        return training_candidate_service.readiness(project_id)
    except ReportMemoryRepositoryError:
        return operational_persistence_error(
            codes.TRAINING_CANDIDATE_PERSISTENCE_UNAVAILABLE
        )


@router.get(
    "/training-candidates/{project_id}",
    response_model=TrainingCandidatePageResponse,
)
def list_training_candidates(
    project_id: str,
    request: Request,
    lifecycle: CandidateLifecycle | None = Query(default=None),
    source_type: TrainingSourceType | None = Query(default=None),
    training_purpose: TrainingPurpose | None = Query(default=None),
    task_type: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    error, caller = _admin(request, project_id)
    if error is not None or caller is None:
        return error
    try:
        items, total = training_candidate_service.page(
            project_id,
            lifecycle=lifecycle,
            source_type=source_type,
            training_purpose=training_purpose,
            task_type=task_type,
            limit=limit,
            offset=offset,
        )
    except ReportMemoryRepositoryError:
        return operational_persistence_error(
            codes.TRAINING_CANDIDATE_PERSISTENCE_UNAVAILABLE
        )
    return TrainingCandidatePageResponse(
        project_id=project_id.strip().lower(),
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )

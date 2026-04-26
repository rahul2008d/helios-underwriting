"""HTTP routes for the risk API v1 with async task support."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from shared.celery.app import celery_app

from celery.result import AsyncResult
from services.risk.api.dependencies import RiskServiceDep, SessionDep
from services.risk.repositories import AssessmentRepository, TriageRepository
from services.risk.schemas import (
    PricingSuggestionResponse,
    RiskAssessmentResponse,
    TriageResultResponse,
    UnderwritingDecisionResponse,
)
from services.risk.services import SubmissionNotFoundError
from services.risk.tasks.underwriting_tasks import process_underwriting_task

router = APIRouter(prefix="/v1/risk", tags=["risk"])


@router.get(
    "/{submission_id}/triage",
    response_model=TriageResultResponse | None,
    summary="Get the latest triage result for a submission",
)
async def get_latest_triage(
    submission_id: UUID,
    session: SessionDep,
) -> TriageResultResponse | None:
    """Return the most recent triage result, or null if none exists."""
    repo = TriageRepository(session)
    result = await repo.latest_for_submission(submission_id)
    if result is None:
        return None
    return TriageResultResponse(**result.model_dump())


@router.get(
    "/{submission_id}/assessment",
    response_model=RiskAssessmentResponse | None,
    summary="Get the latest risk assessment for a submission",
)
async def get_latest_assessment(
    submission_id: UUID,
    session: SessionDep,
) -> RiskAssessmentResponse | None:
    """Return the most recent risk assessment, or null if none exists."""
    repo = AssessmentRepository(session)
    result = await repo.latest_for_submission(submission_id)
    if result is None:
        return None
    return RiskAssessmentResponse(**result.model_dump())


@router.post(
    "/{submission_id}/triage",
    response_model=TriageResultResponse,
    summary="Run AI triage on a submission",
)
async def triage_submission(
    submission_id: UUID,
    service: RiskServiceDep,
) -> TriageResultResponse:
    """Classify a submission as ACCEPT, REFER, or DECLINE using the triage agent."""
    try:
        result = await service.triage(submission_id)
    except SubmissionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return TriageResultResponse(**result.model_dump())


@router.post(
    "/{submission_id}/assess",
    response_model=RiskAssessmentResponse,
    summary="Run risk assessment on a submission",
)
async def assess_submission(
    submission_id: UUID,
    service: RiskServiceDep,
) -> RiskAssessmentResponse:
    """Calculate a risk score and AI-generated risk summary."""
    try:
        result = await service.assess(submission_id)
    except SubmissionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return RiskAssessmentResponse(**result.model_dump())


@router.post(
    "/{submission_id}/pricing",
    response_model=PricingSuggestionResponse,
    summary="Suggest a premium for an assessed submission",
)
async def suggest_pricing(
    submission_id: UUID,
    service: RiskServiceDep,
) -> PricingSuggestionResponse:
    """Generate a pricing suggestion based on the latest risk assessment."""
    try:
        suggestion = await service.suggest_pricing(submission_id)
    except SubmissionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return PricingSuggestionResponse(
        submission_id=submission_id,
        premium=suggestion.premium,
        base_premium=suggestion.base_premium,
        risk_loading_pct=suggestion.risk_loading_pct,
        rationale=suggestion.rationale,
    )


@router.post(
    "/{submission_id}/process",
    response_model=UnderwritingDecisionResponse,
    summary="Run the full underwriting workflow synchronously",
)
async def process_full_workflow(
    submission_id: UUID,
    service: RiskServiceDep,
) -> UnderwritingDecisionResponse:
    """Run triage, then (if not declined) assessment and pricing."""
    try:
        triage, assessment, pricing = await service.process_full_workflow(submission_id)
    except SubmissionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    response = UnderwritingDecisionResponse(
        submission_id=submission_id,
        triage=TriageResultResponse(**triage.model_dump()),
    )
    if assessment is not None:
        response.assessment = RiskAssessmentResponse(**assessment.model_dump())
    if pricing is not None:
        response.pricing = PricingSuggestionResponse(
            submission_id=submission_id,
            premium=pricing.premium,
            base_premium=pricing.base_premium,
            risk_loading_pct=pricing.risk_loading_pct,
            rationale=pricing.rationale,
        )
    return response


@router.post(
    "/{submission_id}/process-async",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run the full underwriting workflow asynchronously",
)
async def process_async(submission_id: UUID) -> dict[str, str]:
    """Enqueue the full underwriting workflow as a Celery task."""
    task = process_underwriting_task.delay(str(submission_id))
    return {
        "task_id": task.id,
        "status": "queued",
        "submission_id": str(submission_id),
    }


@router.get(
    "/jobs/{task_id}",
    summary="Check the status of an async underwriting task",
)
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Return the status (and result, if complete) of an async task."""
    result = AsyncResult(task_id, app=celery_app)

    response: dict[str, Any] = {
        "task_id": task_id,
        "status": result.status,
    }

    if result.successful():
        response["result"] = result.result
    elif result.failed():
        response["error"] = str(result.result)

    return response

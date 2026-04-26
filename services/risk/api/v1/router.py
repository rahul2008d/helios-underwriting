"""HTTP routes for the risk API v1."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from services.risk.api.dependencies import RiskServiceDep
from services.risk.schemas import (
    PricingSuggestionResponse,
    RiskAssessmentResponse,
    TriageResultResponse,
    UnderwritingDecisionResponse,
)
from services.risk.services import SubmissionNotFoundError

router = APIRouter(prefix="/v1/risk", tags=["risk"])


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
    summary="Run the full underwriting workflow",
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

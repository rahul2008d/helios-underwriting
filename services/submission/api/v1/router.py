"""HTTP routes for the submission API v1."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from shared.domain import SubmissionStatus

from services.submission.api.dependencies import SubmissionServiceDep
from services.submission.schemas import (
    CreateSubmissionRequest,
    SubmissionListResponse,
    SubmissionResponse,
    SubmissionSummaryResponse,
)
from services.submission.services import DuplicateReferenceError, SubmissionNotFoundError

router = APIRouter(prefix="/v1/submissions", tags=["submissions"])


@router.post(
    "",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new risk submission",
)
async def create_submission(
    request: CreateSubmissionRequest,
    service: SubmissionServiceDep,
) -> SubmissionResponse:
    """Ingest a new risk submission from a broker.

    Returns the persisted submission with system-generated fields populated.
    """
    try:
        submission = await service.create(request)
    except DuplicateReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return SubmissionResponse.from_domain(submission)


@router.get(
    "/{submission_id}",
    response_model=SubmissionResponse,
    summary="Get a submission by id",
)
async def get_submission(
    submission_id: UUID,
    service: SubmissionServiceDep,
) -> SubmissionResponse:
    """Return the full details of a submission."""
    try:
        submission = await service.get(submission_id)
    except SubmissionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return SubmissionResponse.from_domain(submission)


@router.get(
    "",
    response_model=SubmissionListResponse,
    summary="List submissions with pagination and optional status filter",
)
async def list_submissions(
    service: SubmissionServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    submission_status: Annotated[SubmissionStatus | None, Query(alias="status")] = None,
) -> SubmissionListResponse:
    """Return a paginated list of submissions."""
    submissions, total = await service.list_paginated(
        limit=limit,
        offset=offset,
        status=submission_status,
    )
    items = [
        SubmissionSummaryResponse(
            id=s.id,
            reference=s.reference,
            received_at=s.received_at,
            status=s.status,
            insured_name=s.insured_name,
            fleet_size=s.fleet_size,
            total_fleet_value=s.total_fleet_value,
            currency=s.annual_revenue.currency,
        )
        for s in submissions
    ]
    return SubmissionListResponse(items=items, total=total, limit=limit, offset=offset)

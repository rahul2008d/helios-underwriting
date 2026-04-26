"""HTTP routes for the RAG API v1."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from services.rag.api.dependencies import (
    HistoricalRepositoryDep,
    SimilarityServiceDep,
    SubmissionRepositoryDep,
)
from services.rag.schemas import (
    HistoricalPolicySummary,
    SimilarityResponse,
    SimilarPolicyResponse,
)

router = APIRouter(prefix="/v1/rag", tags=["rag"])


@router.get(
    "/similar/{submission_id}",
    response_model=SimilarityResponse,
    summary="Find historical policies most similar to a submission",
)
async def find_similar(
    submission_id: UUID,
    similarity_service: SimilarityServiceDep,
    submission_repository: SubmissionRepositoryDep,
    top_n: Annotated[int, Query(ge=1, le=20)] = 5,
) -> SimilarityResponse:
    """Return historical policies most similar to the given submission.

    Uses semantic similarity over policy text (insured name, business
    description, fleet composition, claims). Returns the top-N matches
    with similarity scores. Useful for underwriters to see how similar
    risks were handled and how they performed.
    """
    submission = await submission_repository.get_by_id(submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"submission '{submission_id}' not found",
        )

    matches = await similarity_service.find_similar(submission, top_n=top_n)

    return SimilarityResponse(
        submission_id=submission_id,
        matches=[
            SimilarPolicyResponse(
                similarity=match.similarity,
                policy=HistoricalPolicySummary.from_record(match.policy),
            )
            for match in matches
        ],
    )


@router.get(
    "/historical",
    response_model=list[HistoricalPolicySummary],
    summary="List all historical policies",
)
async def list_historical(
    repository: HistoricalRepositoryDep,
) -> list[HistoricalPolicySummary]:
    """Return all historical policies (for browsing)."""
    records = await repository.list_all()
    return [HistoricalPolicySummary.from_record(record) for record in records]

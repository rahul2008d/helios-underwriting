"""HTTP routes for the pricing API v1."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response

from services.pricing.api.dependencies import PricingServiceDep, SubmissionRepositoryDep
from services.pricing.schemas import (
    CreateQuoteRequest,
    QuoteListResponse,
    QuoteResponse,
    QuoteSummaryResponse,
)
from services.pricing.services import (
    QuoteNotFoundError,
    SubmissionNotFoundError,
    generate_quote_pdf,
)

router = APIRouter(prefix="/v1/quotes", tags=["quotes"])


@router.post(
    "",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a formal quote from pricing data",
)
async def create_quote(
    request: CreateQuoteRequest,
    service: PricingServiceDep,
) -> QuoteResponse:
    """Create a new quote, typically from a pricing suggestion produced by the risk service."""
    try:
        quote = await service.create(request)
    except SubmissionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return QuoteResponse.from_domain(quote)


@router.get(
    "/{quote_id}",
    response_model=QuoteResponse,
    summary="Get a quote by id",
)
async def get_quote(
    quote_id: UUID,
    service: PricingServiceDep,
) -> QuoteResponse:
    """Return the full details of a quote."""
    try:
        quote = await service.get(quote_id)
    except QuoteNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return QuoteResponse.from_domain(quote)


@router.get(
    "/{quote_id}/pdf",
    summary="Download a quote as PDF",
    responses={200: {"content": {"application/pdf": {}}, "description": "Quote PDF"}},
)
async def download_quote_pdf(
    quote_id: UUID,
    service: PricingServiceDep,
    submission_repository: SubmissionRepositoryDep,
) -> Response:
    """Return the quote as a downloadable PDF."""
    try:
        quote = await service.get(quote_id)
    except QuoteNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    submission = await submission_repository.get_by_id(quote.submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"submission '{quote.submission_id}' not found",
        )

    pdf_bytes = generate_quote_pdf(quote, submission)
    filename = f"{quote.quote_reference}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "",
    response_model=QuoteListResponse,
    summary="List all quotes with pagination",
)
async def list_quotes(
    service: PricingServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> QuoteListResponse:
    """Return a paginated list of all quotes."""
    quotes, total = await service.list_paginated(limit=limit, offset=offset)
    items = [
        QuoteSummaryResponse(
            id=quote.id,
            submission_id=quote.submission_id,
            quote_reference=quote.quote_reference,
            premium=quote.premium,
            valid_until=quote.valid_until,
            is_expired=QuoteResponse.from_domain(quote).is_expired,
        )
        for quote in quotes
    ]
    return QuoteListResponse(items=items, total=total, limit=limit, offset=offset)

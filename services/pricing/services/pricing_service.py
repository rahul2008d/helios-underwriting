"""Pricing service business logic.

Coordinates quote creation: takes a pricing suggestion (typically from the AI
risk service) and turns it into a formal Quote with a quote reference, validity
period, and persisted record.
"""

from datetime import date, timedelta
from uuid import UUID

from shared.domain import Quote
from shared.logging import logger

from services.pricing.repositories import QuoteRepository
from services.pricing.schemas import CreateQuoteRequest
from services.pricing.services.exceptions import QuoteNotFoundError, SubmissionNotFoundError
from services.submission.repositories import SubmissionRepository

# Default validity period for new quotes
_DEFAULT_VALIDITY_DAYS = 30


class PricingService:
    """Coordinates quote creation, retrieval, and PDF generation."""

    def __init__(
        self,
        *,
        quote_repository: QuoteRepository,
        submission_repository: SubmissionRepository,
    ) -> None:
        """Initialise with the repositories the service needs."""
        self._quote_repository = quote_repository
        self._submission_repository = submission_repository

    async def create(self, request: CreateQuoteRequest) -> Quote:
        """Validate the submission exists, generate a quote reference, and persist."""
        submission = await self._submission_repository.get_by_id(request.submission_id)
        if submission is None:
            raise SubmissionNotFoundError(str(request.submission_id))

        next_number = await self._quote_repository.next_reference_number()
        quote_reference = f"QUO-{date.today().year}-{next_number:04d}"

        valid_until = request.valid_until or (date.today() + timedelta(days=_DEFAULT_VALIDITY_DAYS))

        quote = Quote(
            submission_id=request.submission_id,
            quote_reference=quote_reference,
            premium=request.premium,
            excess=request.excess,
            coverage=request.coverage,
            valid_until=valid_until,
            rationale=request.rationale,
        )
        await self._quote_repository.add(quote)

        logger.info(
            "quote created",
            quote_id=str(quote.id),
            quote_reference=quote_reference,
            submission_id=str(quote.submission_id),
            premium=str(quote.premium),
        )
        return quote

    async def get(self, quote_id: UUID) -> Quote:
        """Return the quote with the given id."""
        quote = await self._quote_repository.get_by_id(quote_id)
        if quote is None:
            raise QuoteNotFoundError(str(quote_id))
        return quote

    async def get_by_reference(self, reference: str) -> Quote:
        """Return the quote with the given reference."""
        quote = await self._quote_repository.get_by_reference(reference)
        if quote is None:
            raise QuoteNotFoundError(reference)
        return quote

    async def list_for_submission(self, submission_id: UUID) -> list[Quote]:
        """Return all quotes for a given submission."""
        return await self._quote_repository.list_for_submission(submission_id)

    async def list_paginated(self, *, limit: int = 50, offset: int = 0) -> tuple[list[Quote], int]:
        """Return a paginated list of all quotes."""
        return await self._quote_repository.list_paginated(limit=limit, offset=offset)

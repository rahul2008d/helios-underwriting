"""Response schemas for the pricing API."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field
from shared.domain import Coverage, Money, Quote


class QuoteResponse(BaseModel):
    """Full quote representation."""

    id: UUID
    submission_id: UUID
    quote_reference: str
    premium: Money
    excess: Money
    coverage: Coverage
    valid_until: date
    rationale: str
    created_at: datetime
    is_expired: bool = Field(..., description="True if the quote has passed its expiry date.")

    @classmethod
    def from_domain(cls, quote: Quote) -> "QuoteResponse":
        """Build a response from a domain Quote."""
        return cls(
            id=quote.id,
            submission_id=quote.submission_id,
            quote_reference=quote.quote_reference,
            premium=quote.premium,
            excess=quote.excess,
            coverage=quote.coverage,
            valid_until=quote.valid_until,
            rationale=quote.rationale,
            created_at=quote.created_at,
            is_expired=quote.valid_until < date.today(),
        )


class QuoteSummaryResponse(BaseModel):
    """Lightweight quote listing item."""

    id: UUID
    submission_id: UUID
    quote_reference: str
    premium: Money
    valid_until: date
    is_expired: bool


class QuoteListResponse(BaseModel):
    """Paginated list of quotes."""

    items: list[QuoteSummaryResponse]
    total: int
    limit: int
    offset: int

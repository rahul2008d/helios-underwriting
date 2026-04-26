"""Request schemas for the pricing API."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field
from shared.domain import Coverage, Money


class CreateQuoteRequest(BaseModel):
    """Payload accepted by POST /quotes."""

    submission_id: UUID = Field(..., description="The submission this quote is for.")
    premium: Money = Field(..., description="The proposed premium.")
    excess: Money = Field(..., description="Voluntary excess.")
    coverage: Coverage = Field(..., description="Coverage being quoted.")
    valid_until: date = Field(
        ...,
        description="When the quote expires if not bound.",
    )
    rationale: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Underwriter-facing explanation of the price.",
    )

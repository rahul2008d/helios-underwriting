"""Request schemas for the submission API."""

from decimal import Decimal

from pydantic import BaseModel, Field
from shared.domain import (
    Address,
    Coverage,
    Currency,
    Driver,
    Money,
    Vehicle,
)


class CreateSubmissionRequest(BaseModel):
    """Payload accepted by POST /submissions."""

    reference: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Broker reference, e.g. 'BRK-2026-0042'.",
        examples=["BRK-2026-0042"],
    )
    insured_name: str = Field(..., min_length=1, max_length=200)
    insured_address: Address
    business_description: str = Field(..., min_length=1, max_length=1000)
    annual_revenue: Money

    vehicles: list[Vehicle] = Field(..., min_length=1)
    drivers: list[Driver] = Field(..., min_length=1)

    operates_internationally: bool = False
    countries_of_operation: list[str] = Field(
        default_factory=lambda: ["United Kingdom"],
    )

    claims_count_5y: int = Field(default=0, ge=0)
    claims_value_5y: Money = Field(
        default_factory=lambda: Money(amount=Decimal(0), currency=Currency.GBP),
    )

    requested_coverage: Coverage

"""Domain value objects.

Value objects are immutable, equality-by-value primitives that don't have identity.
They model concepts like Money, Address, and DateRange.
"""

from datetime import date
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from shared.domain.enums import Currency


class Money(BaseModel):
    """A monetary amount in a specific currency.

    Uses Decimal for precision (never use float for money).
    """

    model_config = ConfigDict(frozen=True)

    amount: Decimal = Field(..., description="Monetary amount, e.g. 1234.56.")
    currency: Currency = Field(default=Currency.GBP)

    def __str__(self) -> str:
        """Format as currency string, e.g. 'GBP 1,234.56'."""
        return f"{self.currency.value} {self.amount:,.2f}"


class Address(BaseModel):
    """A UK postal address."""

    model_config = ConfigDict(frozen=True)

    line_1: str = Field(..., min_length=1, max_length=200)
    line_2: str | None = Field(default=None, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    postcode: str = Field(..., min_length=5, max_length=10)
    country: str = Field(default="United Kingdom", max_length=100)


class DateRange(BaseModel):
    """An inclusive date range, typically used for policy periods."""

    model_config = ConfigDict(frozen=True)

    start: date = Field(..., description="Inclusive start date.")
    end: date = Field(..., description="Inclusive end date.")

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        """Ensure end date is not before start date."""
        if self.end < self.start:
            raise ValueError("end date must be on or after start date")
        return self

    @property
    def days(self) -> int:
        """Number of days in the range, inclusive."""
        return (self.end - self.start).days + 1

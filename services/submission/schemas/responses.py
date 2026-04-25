"""Response schemas for the submission API."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field
from shared.domain import (
    Address,
    Coverage,
    Currency,
    Driver,
    Money,
    Submission,
    SubmissionStatus,
    Vehicle,
)


class SubmissionResponse(BaseModel):
    """Full representation of a submission returned by the API."""

    id: UUID
    reference: str
    received_at: datetime
    status: SubmissionStatus

    insured_name: str
    insured_address: Address
    business_description: str
    annual_revenue: Money

    vehicles: list[Vehicle]
    drivers: list[Driver]
    operates_internationally: bool
    countries_of_operation: list[str]

    claims_count_5y: int
    claims_value_5y: Money

    requested_coverage: Coverage

    fleet_size: int = Field(..., description="Number of vehicles in the fleet.")
    total_fleet_value: Decimal = Field(..., description="Sum of all vehicle values.")

    @classmethod
    def from_domain(cls, submission: Submission) -> "SubmissionResponse":
        """Build a response from a domain submission."""
        return cls(
            id=submission.id,
            reference=submission.reference,
            received_at=submission.received_at,
            status=submission.status,
            insured_name=submission.insured_name,
            insured_address=submission.insured_address,
            business_description=submission.business_description,
            annual_revenue=submission.annual_revenue,
            vehicles=submission.vehicles,
            drivers=submission.drivers,
            operates_internationally=submission.operates_internationally,
            countries_of_operation=submission.countries_of_operation,
            claims_count_5y=submission.claims_count_5y,
            claims_value_5y=submission.claims_value_5y,
            requested_coverage=submission.requested_coverage,
            fleet_size=submission.fleet_size,
            total_fleet_value=submission.total_fleet_value,
        )


class SubmissionSummaryResponse(BaseModel):
    """Lightweight submission listing item."""

    id: UUID
    reference: str
    received_at: datetime
    status: SubmissionStatus
    insured_name: str
    fleet_size: int
    total_fleet_value: Decimal
    currency: Currency


class SubmissionListResponse(BaseModel):
    """Paginated list of submissions."""

    items: list[SubmissionSummaryResponse]
    total: int
    limit: int
    offset: int

"""Pydantic domain models for fleet insurance.

These are the core business objects, separate from database models. The same
domain object can be persisted, sent over an API, or processed by an AI agent.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.domain.enums import (
    CoverageType,
    PolicyStatus,
    RiskBand,
    SubmissionStatus,
    TriageDecision,
    VehicleType,
)
from shared.domain.value_objects import Address, DateRange, Money


class Driver(BaseModel):
    """A driver listed on a fleet insurance submission."""

    model_config = ConfigDict(frozen=True)

    full_name: str = Field(..., min_length=2, max_length=200)
    licence_number: str = Field(..., min_length=8, max_length=20)
    date_of_birth: date
    years_licensed: int = Field(..., ge=0, le=80)
    points: int = Field(default=0, ge=0, le=12, description="Penalty points on licence.")
    convictions_5y: int = Field(
        default=0,
        ge=0,
        description="Motoring convictions in last 5 years.",
    )

    @property
    def age(self) -> int:
        """Driver's age today in whole years."""
        today = date.today()
        years = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            years -= 1
        return years


class Vehicle(BaseModel):
    """A vehicle in the insured fleet."""

    model_config = ConfigDict(frozen=True)

    registration: str = Field(..., min_length=2, max_length=10)
    vehicle_type: VehicleType
    make: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=50)
    year: int = Field(..., ge=1990, le=2030)
    value: Money
    annual_mileage: int = Field(..., ge=0, le=500_000)
    gross_weight_kg: int | None = Field(default=None, ge=0, le=44_000)

    @field_validator("registration")
    @classmethod
    def normalise_registration(cls, value: str) -> str:
        """Strip whitespace and uppercase the registration."""
        return value.strip().upper().replace(" ", "")


class Coverage(BaseModel):
    """Coverage requested for a submission or bound on a policy."""

    model_config = ConfigDict(frozen=True)

    coverage_type: CoverageType
    period: DateRange
    excess: Money = Field(..., description="Voluntary excess per claim.")


class Submission(BaseModel):
    """A risk submission from a broker, the entry point of underwriting.

    Lifecycle: RECEIVED -> PARSING -> TRIAGED -> ASSESSED -> QUOTED -> BOUND
    Or: any stage -> DECLINED / EXPIRED
    """

    id: UUID = Field(default_factory=uuid4)
    reference: str = Field(..., description="Broker reference, e.g. 'BRK-2026-0042'.")
    received_at: datetime = Field(default_factory=datetime.utcnow)
    status: SubmissionStatus = SubmissionStatus.RECEIVED

    # Risk details
    insured_name: str = Field(..., min_length=1, max_length=200)
    insured_address: Address
    business_description: str = Field(..., min_length=1, max_length=1000)
    annual_revenue: Money

    # Fleet details
    vehicles: list[Vehicle] = Field(..., min_length=1)
    drivers: list[Driver] = Field(..., min_length=1)
    operates_internationally: bool = Field(default=False)
    countries_of_operation: list[str] = Field(default_factory=lambda: ["United Kingdom"])

    # Loss history
    claims_count_5y: int = Field(default=0, ge=0)
    claims_value_5y: Money = Field(default=Money(amount=Decimal(0)))

    # Coverage requested
    requested_coverage: Coverage

    @property
    def fleet_size(self) -> int:
        """Number of vehicles in the fleet."""
        return len(self.vehicles)

    @property
    def total_fleet_value(self) -> Decimal:
        """Sum of all vehicle values, in the submission's currency."""
        return sum((v.value.amount for v in self.vehicles), start=Decimal(0))


class TriageResult(BaseModel):
    """Output of the triage agent."""

    submission_id: UUID
    decision: TriageDecision
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., description="Human-readable explanation of the decision.")
    appetite_matches: list[str] = Field(
        default_factory=list,
        description="Appetite criteria that matched (e.g. 'UK only', 'fleet < 50').",
    )
    appetite_concerns: list[str] = Field(
        default_factory=list,
        description="Appetite criteria that raised concerns.",
    )
    triaged_at: datetime = Field(default_factory=datetime.utcnow)


class RiskAssessment(BaseModel):
    """Output of the risk assessment process."""

    submission_id: UUID
    risk_band: RiskBand
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Higher means riskier.")
    factors: dict[str, float] = Field(
        default_factory=dict,
        description="Named risk factors and their contribution scores.",
    )
    summary: str = Field(..., description="Underwriter-facing risk summary.")
    assessed_at: datetime = Field(default_factory=datetime.utcnow)


class Quote(BaseModel):
    """A quote generated for an assessed submission."""

    id: UUID = Field(default_factory=uuid4)
    submission_id: UUID
    quote_reference: str = Field(
        ...,
        description="Human-readable quote ref, e.g. 'QUO-2026-0042'.",
    )
    premium: Money
    excess: Money
    coverage: Coverage
    valid_until: date
    rationale: str = Field(..., description="Underwriter-facing pricing rationale.")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Policy(BaseModel):
    """A bound insurance policy."""

    id: UUID = Field(default_factory=uuid4)
    policy_number: str = Field(..., description="Customer-facing policy number.")
    quote_id: UUID
    submission_id: UUID
    insured_name: str
    status: PolicyStatus = PolicyStatus.ACTIVE
    period: DateRange
    premium: Money
    bound_at: datetime = Field(default_factory=datetime.utcnow)
    bound_by: str = Field(..., description="Username or system that bound the policy.")

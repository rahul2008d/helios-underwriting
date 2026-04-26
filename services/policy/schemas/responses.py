"""Response schemas for the policy API."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field
from shared.domain import Money, Policy, PolicyStatus
from shared.domain.endorsement import Endorsement, EndorsementStatus, EndorsementType


class EndorsementResponse(BaseModel):
    """An endorsement returned by the API."""

    id: UUID
    policy_id: UUID
    endorsement_number: str
    endorsement_type: EndorsementType
    description: str
    effective_date: date
    premium_adjustment: Money
    status: EndorsementStatus
    created_at: datetime
    applied_at: datetime | None
    requested_by: str

    @classmethod
    def from_domain(cls, endorsement: Endorsement) -> "EndorsementResponse":
        """Build response from a domain Endorsement."""
        return cls(**endorsement.model_dump())


class PolicyResponse(BaseModel):
    """Full policy representation."""

    id: UUID
    policy_number: str
    quote_id: UUID
    submission_id: UUID
    insured_name: str
    status: PolicyStatus
    period_start: date
    period_end: date
    premium: Money
    bound_at: datetime
    bound_by: str
    valid_next_states: list[PolicyStatus] = Field(
        default_factory=list,
        description="States the policy can legally transition to.",
    )
    endorsements: list[EndorsementResponse] = Field(default_factory=list)

    @classmethod
    def from_domain(
        cls,
        policy: Policy,
        *,
        valid_next_states: list[PolicyStatus] | None = None,
        endorsements: list[Endorsement] | None = None,
    ) -> "PolicyResponse":
        """Build response from a domain Policy."""
        return cls(
            id=policy.id,
            policy_number=policy.policy_number,
            quote_id=policy.quote_id,
            submission_id=policy.submission_id,
            insured_name=policy.insured_name,
            status=policy.status,
            period_start=policy.period.start,
            period_end=policy.period.end,
            premium=policy.premium,
            bound_at=policy.bound_at,
            bound_by=policy.bound_by,
            valid_next_states=valid_next_states or [],
            endorsements=[EndorsementResponse.from_domain(e) for e in (endorsements or [])],
        )


class PolicySummaryResponse(BaseModel):
    """Lightweight policy listing item."""

    id: UUID
    policy_number: str
    insured_name: str
    status: PolicyStatus
    period_start: date
    period_end: date
    premium: Money


class PolicyListResponse(BaseModel):
    """Paginated list of policies."""

    items: list[PolicySummaryResponse]
    total: int
    limit: int
    offset: int

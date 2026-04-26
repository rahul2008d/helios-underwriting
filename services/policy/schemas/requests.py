"""Request schemas for the policy API."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field
from shared.domain import Money, PolicyStatus
from shared.domain.endorsement import EndorsementType


class BindPolicyRequest(BaseModel):
    """Payload for binding a quote into a policy."""

    quote_id: UUID = Field(..., description="The quote being bound.")
    bound_by: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Username or system performing the bind.",
    )


class PolicyTransitionRequest(BaseModel):
    """Payload for transitioning a policy to a new status."""

    new_status: PolicyStatus = Field(..., description="Target status.")
    reason: str = Field(
        default="",
        max_length=1000,
        description="Optional reason for the transition (audit trail).",
    )


class CreateEndorsementRequest(BaseModel):
    """Payload for creating a new endorsement on a policy."""

    endorsement_type: EndorsementType
    description: str = Field(..., min_length=1, max_length=2000)
    effective_date: date
    premium_adjustment: Money = Field(
        default_factory=lambda: Money(amount=Decimal(0)),
    )
    requested_by: str = Field(..., min_length=1, max_length=100)

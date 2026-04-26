"""Endorsement: a modification to a bound policy.

In insurance, an endorsement is a formal change to a live policy - adding
a vehicle, changing a driver, updating coverage. They have their own
lifecycle (proposed -> approved -> applied) and create an audit trail.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from shared.domain.value_objects import Money


class EndorsementStatus(StrEnum):
    """Lifecycle states of an endorsement."""

    PROPOSED = "proposed"
    """Endorsement has been requested but not yet approved."""

    APPROVED = "approved"
    """Endorsement is approved and ready to apply."""

    APPLIED = "applied"
    """Endorsement is now in effect on the policy."""

    REJECTED = "rejected"
    """Endorsement was rejected."""


class EndorsementType(StrEnum):
    """Categories of endorsement, useful for reporting and pricing."""

    ADD_VEHICLE = "add_vehicle"
    REMOVE_VEHICLE = "remove_vehicle"
    ADD_DRIVER = "add_driver"
    REMOVE_DRIVER = "remove_driver"
    CHANGE_COVERAGE = "change_coverage"
    CHANGE_EXCESS = "change_excess"
    CORRECTION = "correction"


class Endorsement(BaseModel):
    """A modification to a bound policy."""

    model_config = ConfigDict()

    id: UUID = Field(default_factory=uuid4)
    policy_id: UUID
    endorsement_number: str = Field(
        ...,
        description="Sequential reference, e.g. 'POL-2026-0042-E001'.",
    )
    endorsement_type: EndorsementType
    description: str = Field(..., min_length=1, max_length=2000)
    effective_date: date = Field(..., description="When the change takes effect.")
    premium_adjustment: Money = Field(
        default_factory=lambda: Money(amount=Decimal(0)),
        description="Additional premium (or refund) for the change.",
    )
    status: EndorsementStatus = EndorsementStatus.PROPOSED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    applied_at: datetime | None = None
    requested_by: str = Field(..., description="Username or system requesting the change.")

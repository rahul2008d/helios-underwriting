"""Insurance domain models.

Re-exports the core domain types so they can be imported as `shared.domain`.
"""

from shared.domain.endorsement import (
    Endorsement,
    EndorsementStatus,
    EndorsementType,
)
from shared.domain.entities import (
    Coverage,
    Driver,
    Policy,
    Quote,
    RiskAssessment,
    Submission,
    TriageResult,
    Vehicle,
)
from shared.domain.enums import (
    CoverageType,
    Currency,
    PolicyStatus,
    RiskBand,
    SubmissionStatus,
    TriageDecision,
    VehicleType,
)
from shared.domain.policy_state import (
    InvalidPolicyTransitionError,
    assert_transition,
    can_transition,
    valid_next_states,
)
from shared.domain.value_objects import Address, DateRange, Money

__all__ = [
    # Value objects
    "Address",
    "Coverage",
    "CoverageType",
    "Currency",
    "DateRange",
    "Driver",
    "Endorsement",
    "EndorsementStatus",
    "EndorsementType",
    "InvalidPolicyTransitionError",
    "Money",
    # Entities
    "Policy",
    "PolicyStatus",
    "Quote",
    "RiskAssessment",
    "RiskBand",
    "Submission",
    "SubmissionStatus",
    "TriageDecision",
    "TriageResult",
    "Vehicle",
    "VehicleType",
    "assert_transition",
    "can_transition",
    "valid_next_states",
]

"""Policy state machine.

Encodes the legal transitions between policy lifecycle states. Centralising
this here means business logic can validate transitions without scattering
the rules across services.
"""

from shared.domain.enums import PolicyStatus

# Map of from_status -> set of valid to_statuses
_VALID_TRANSITIONS: dict[PolicyStatus, frozenset[PolicyStatus]] = {
    PolicyStatus.ACTIVE: frozenset(
        {
            PolicyStatus.CANCELLED,
            PolicyStatus.LAPSED,
            PolicyStatus.RENEWED,
        }
    ),
    PolicyStatus.LAPSED: frozenset({PolicyStatus.RENEWED}),
    PolicyStatus.CANCELLED: frozenset(),  # terminal
    PolicyStatus.RENEWED: frozenset(),  # terminal (the new policy is a separate record)
}


class InvalidPolicyTransitionError(Exception):
    """Raised when an attempt is made to transition to an invalid state."""

    def __init__(self, current: PolicyStatus, requested: PolicyStatus) -> None:
        """Capture the disallowed from/to states for the error message."""
        self.current = current
        self.requested = requested
        super().__init__(f"cannot transition policy from {current.value!r} to {requested.value!r}")


def can_transition(current: PolicyStatus, requested: PolicyStatus) -> bool:
    """Return True if the requested transition is legal."""
    return requested in _VALID_TRANSITIONS.get(current, frozenset())


def assert_transition(current: PolicyStatus, requested: PolicyStatus) -> None:
    """Raise InvalidPolicyTransitionError if the transition is not legal."""
    if not can_transition(current, requested):
        raise InvalidPolicyTransitionError(current, requested)


def valid_next_states(current: PolicyStatus) -> frozenset[PolicyStatus]:
    """Return the set of statuses that the policy can move to."""
    return _VALID_TRANSITIONS.get(current, frozenset())

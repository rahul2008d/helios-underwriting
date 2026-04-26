"""Unit tests for the policy state machine."""

import pytest
from shared.domain import PolicyStatus
from shared.domain.policy_state import (
    InvalidPolicyTransitionError,
    assert_transition,
    can_transition,
    valid_next_states,
)


class TestPolicyStateTransitions:
    @pytest.mark.parametrize(
        ("current", "target", "expected"),
        [
            (PolicyStatus.ACTIVE, PolicyStatus.CANCELLED, True),
            (PolicyStatus.ACTIVE, PolicyStatus.LAPSED, True),
            (PolicyStatus.ACTIVE, PolicyStatus.RENEWED, True),
            (PolicyStatus.LAPSED, PolicyStatus.RENEWED, True),
            (PolicyStatus.CANCELLED, PolicyStatus.ACTIVE, False),
            (PolicyStatus.CANCELLED, PolicyStatus.RENEWED, False),
            (PolicyStatus.RENEWED, PolicyStatus.ACTIVE, False),
            (PolicyStatus.LAPSED, PolicyStatus.ACTIVE, False),
            (PolicyStatus.LAPSED, PolicyStatus.CANCELLED, False),
        ],
    )
    def test_can_transition(self, current, target, expected):
        assert can_transition(current, target) is expected

    def test_assert_transition_succeeds_for_legal_move(self):
        # No exception should be raised
        assert_transition(PolicyStatus.ACTIVE, PolicyStatus.CANCELLED)

    def test_assert_transition_raises_for_illegal_move(self):
        with pytest.raises(InvalidPolicyTransitionError):
            assert_transition(PolicyStatus.CANCELLED, PolicyStatus.ACTIVE)

    def test_valid_next_states_for_active(self):
        states = valid_next_states(PolicyStatus.ACTIVE)
        assert states == frozenset(
            {PolicyStatus.CANCELLED, PolicyStatus.LAPSED, PolicyStatus.RENEWED}
        )

    def test_valid_next_states_for_terminal_state(self):
        assert valid_next_states(PolicyStatus.CANCELLED) == frozenset()
        assert valid_next_states(PolicyStatus.RENEWED) == frozenset()

    def test_invalid_transition_error_message(self):
        with pytest.raises(InvalidPolicyTransitionError) as exc_info:
            assert_transition(PolicyStatus.CANCELLED, PolicyStatus.ACTIVE)
        assert "cancelled" in str(exc_info.value)
        assert "active" in str(exc_info.value)

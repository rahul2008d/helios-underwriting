"""Exceptions for the policy service."""


class PolicyServiceError(Exception):
    """Base exception for policy service errors."""


class PolicyNotFoundError(PolicyServiceError):
    """Raised when a policy cannot be found."""

    def __init__(self, identifier: str) -> None:
        """Initialise with the identifier that was not found."""
        self.identifier = identifier
        super().__init__(f"policy '{identifier}' not found")


class QuoteNotFoundError(PolicyServiceError):
    """Raised when the quote a binding refers to does not exist."""

    def __init__(self, quote_id: str) -> None:
        """Initialise with the missing quote id."""
        self.quote_id = quote_id
        super().__init__(f"quote '{quote_id}' not found")


class PolicyAlreadyBoundError(PolicyServiceError):
    """Raised when a quote already has a bound policy."""

    def __init__(self, quote_id: str, existing_policy_number: str) -> None:
        """Initialise with the quote id and existing policy number."""
        self.quote_id = quote_id
        self.existing_policy_number = existing_policy_number
        super().__init__(
            f"quote '{quote_id}' is already bound as policy '{existing_policy_number}'"
        )


class EndorsementNotFoundError(PolicyServiceError):
    """Raised when an endorsement cannot be found."""

    def __init__(self, endorsement_id: str) -> None:
        """Initialise with the missing endorsement id."""
        self.endorsement_id = endorsement_id
        super().__init__(f"endorsement '{endorsement_id}' not found")

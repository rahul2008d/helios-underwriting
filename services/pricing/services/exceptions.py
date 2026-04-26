"""Exceptions for the pricing service."""


class PricingServiceError(Exception):
    """Base exception for pricing service errors."""


class SubmissionNotFoundError(PricingServiceError):
    """Raised when the submission a quote refers to does not exist."""

    def __init__(self, submission_id: str) -> None:
        """Initialise with the missing submission id."""
        self.submission_id = submission_id
        super().__init__(f"submission '{submission_id}' not found")


class QuoteNotFoundError(PricingServiceError):
    """Raised when a quote cannot be found."""

    def __init__(self, identifier: str) -> None:
        """Initialise with the identifier that was not found."""
        self.identifier = identifier
        super().__init__(f"quote '{identifier}' not found")


class QuoteExpiredError(PricingServiceError):
    """Raised when an expired quote is used in a way that requires it to be live."""

    def __init__(self, quote_reference: str) -> None:
        """Initialise with the expired quote's reference."""
        self.quote_reference = quote_reference
        super().__init__(f"quote '{quote_reference}' has expired")

"""Exceptions raised by the submission service layer.

These are domain-meaningful errors. The API layer translates them into
appropriate HTTP responses.
"""


class SubmissionServiceError(Exception):
    """Base exception for submission service errors."""


class DuplicateReferenceError(SubmissionServiceError):
    """Raised when a submission with the same broker reference already exists."""

    def __init__(self, reference: str) -> None:
        """Create an error for the given duplicate broker reference."""
        self.reference = reference
        super().__init__(f"submission with reference '{reference}' already exists")


class SubmissionNotFoundError(SubmissionServiceError):
    """Raised when a submission cannot be found."""

    def __init__(self, identifier: str) -> None:
        """Create an error for a missing id or non-existent submission."""
        self.identifier = identifier
        super().__init__(f"submission '{identifier}' not found")

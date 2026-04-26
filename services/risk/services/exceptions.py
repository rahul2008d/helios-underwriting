"""Exceptions for the risk service layer."""


class RiskServiceError(Exception):
    """Base exception for risk service errors."""


class SubmissionNotFoundError(RiskServiceError):
    """Raised when the target submission does not exist."""

    def __init__(self, submission_id: str) -> None:
        """Create an error for a missing submission id."""
        self.submission_id = submission_id
        super().__init__(f"submission '{submission_id}' not found")

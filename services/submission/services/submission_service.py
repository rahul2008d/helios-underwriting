"""Service layer for submission operations.

Holds the orchestration and business rules. Talks to the repository for
persistence; never touches the database directly.
"""

from datetime import datetime
from uuid import UUID

from shared.domain import Submission, SubmissionStatus
from shared.logging import logger

from services.submission.repositories import SubmissionRepository
from services.submission.schemas import CreateSubmissionRequest
from services.submission.services.exceptions import (
    DuplicateReferenceError,
    SubmissionNotFoundError,
)


class SubmissionService:
    """Coordinates business logic for submissions."""

    def __init__(self, repository: SubmissionRepository) -> None:
        """Create a service backed by the given repository."""
        self._repository = repository

    async def create(self, request: CreateSubmissionRequest) -> Submission:
        """Validate, persist, and return a new submission.

        Raises:
            DuplicateReferenceError: if the broker reference is already in use.
        """
        existing = await self._repository.get_by_reference(request.reference)
        if existing is not None:
            logger.warning(
                "rejected duplicate submission reference",
                reference=request.reference,
                existing_id=str(existing.id),
            )
            raise DuplicateReferenceError(request.reference)

        submission = Submission(
            reference=request.reference,
            received_at=datetime.utcnow(),
            status=SubmissionStatus.RECEIVED,
            insured_name=request.insured_name,
            insured_address=request.insured_address,
            business_description=request.business_description,
            annual_revenue=request.annual_revenue,
            vehicles=request.vehicles,
            drivers=request.drivers,
            operates_internationally=request.operates_internationally,
            countries_of_operation=request.countries_of_operation,
            claims_count_5y=request.claims_count_5y,
            claims_value_5y=request.claims_value_5y,
            requested_coverage=request.requested_coverage,
        )

        await self._repository.add(submission)

        logger.info(
            "submission created",
            submission_id=str(submission.id),
            reference=submission.reference,
            insured_name=submission.insured_name,
            fleet_size=submission.fleet_size,
        )
        return submission

    async def get(self, submission_id: UUID) -> Submission:
        """Return the submission with the given id.

        Raises:
            SubmissionNotFoundError: if no such submission exists.
        """
        submission = await self._repository.get_by_id(submission_id)
        if submission is None:
            raise SubmissionNotFoundError(str(submission_id))
        return submission

    async def list_paginated(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: SubmissionStatus | None = None,
    ) -> tuple[list[Submission], int]:
        """List submissions with pagination and optional status filter."""
        return await self._repository.list_paginated(
            limit=limit,
            offset=offset,
            status=status,
        )

    async def transition_status(self, submission_id: UUID, status: SubmissionStatus) -> Submission:
        """Move a submission to a new status.

        Raises:
            SubmissionNotFoundError: if the submission does not exist.
        """
        updated = await self._repository.update_status(submission_id, status)
        if updated is None:
            raise SubmissionNotFoundError(str(submission_id))
        logger.info(
            "submission status changed",
            submission_id=str(submission_id),
            new_status=status.value,
        )
        return updated

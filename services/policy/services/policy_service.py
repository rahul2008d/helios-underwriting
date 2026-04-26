"""Policy service business logic.

Coordinates policy binding, lifecycle transitions, and endorsements.
"""

from datetime import date, datetime
from uuid import UUID

from shared.domain import (
    DateRange,
    Policy,
    PolicyStatus,
)
from shared.domain.endorsement import Endorsement, EndorsementStatus
from shared.domain.policy_state import (
    InvalidPolicyTransitionError,
    assert_transition,
    valid_next_states,
)
from shared.logging import logger

from services.policy.repositories import EndorsementRepository, PolicyRepository
from services.policy.schemas.requests import (
    BindPolicyRequest,
    CreateEndorsementRequest,
)
from services.policy.services.exceptions import (
    EndorsementNotFoundError,
    PolicyAlreadyBoundError,
    PolicyNotFoundError,
    QuoteNotFoundError,
)
from services.pricing.repositories import QuoteRepository
from services.pricing.services.exceptions import QuoteExpiredError
from services.submission.repositories import SubmissionRepository


class PolicyService:
    """Coordinates policy binding, lifecycle, and endorsements."""

    def __init__(
        self,
        *,
        policy_repository: PolicyRepository,
        endorsement_repository: EndorsementRepository,
        quote_repository: QuoteRepository,
        submission_repository: SubmissionRepository,
    ) -> None:
        """Initialise with the repositories the service needs."""
        self._policy_repository = policy_repository
        self._endorsement_repository = endorsement_repository
        self._quote_repository = quote_repository
        self._submission_repository = submission_repository

    async def bind(self, request: BindPolicyRequest) -> Policy:
        """Bind a quote, creating a new policy.

        Validates that the quote exists, has not already been bound, and is
        not expired. Generates a policy number and persists.
        """
        quote = await self._quote_repository.get_by_id(request.quote_id)
        if quote is None:
            raise QuoteNotFoundError(str(request.quote_id))

        if quote.valid_until < date.today():
            raise QuoteExpiredError(quote.quote_reference)

        existing = await self._policy_repository.get_by_quote_id(request.quote_id)
        if existing is not None:
            raise PolicyAlreadyBoundError(
                quote_id=str(request.quote_id),
                existing_policy_number=existing.policy_number,
            )

        next_number = await self._policy_repository.next_policy_number()
        policy_number = f"POL-{date.today().year}-{next_number:04d}"

        policy = Policy(
            policy_number=policy_number,
            quote_id=quote.id,
            submission_id=quote.submission_id,
            insured_name="",  # set below from submission
            status=PolicyStatus.ACTIVE,
            period=DateRange(
                start=quote.coverage.period.start,
                end=quote.coverage.period.end,
            ),
            premium=quote.premium,
            bound_at=datetime.utcnow(),
            bound_by=request.bound_by,
        )

        submission = await self._submission_repository.get_by_id(quote.submission_id)
        if submission is None:
            raise QuoteNotFoundError(f"submission '{quote.submission_id}' not found")

        policy = policy.model_copy(update={"insured_name": submission.insured_name})

        await self._policy_repository.add(policy)

        logger.info(
            "policy bound",
            policy_id=str(policy.id),
            policy_number=policy_number,
            quote_reference=quote.quote_reference,
            bound_by=request.bound_by,
            premium=str(policy.premium),
        )

        return policy

    async def get(self, policy_id: UUID) -> Policy:
        """Return the policy with the given id."""
        policy = await self._policy_repository.get_by_id(policy_id)
        if policy is None:
            raise PolicyNotFoundError(str(policy_id))
        return policy

    async def get_by_quote_id(self, quote_id: UUID) -> Policy | None:
        """Return the policy created from a quote, if one exists."""
        return await self._policy_repository.get_by_quote_id(quote_id)

    async def get_by_number(self, policy_number: str) -> Policy:
        """Return the policy with the given customer-facing number."""
        policy = await self._policy_repository.get_by_number(policy_number)
        if policy is None:
            raise PolicyNotFoundError(policy_number)
        return policy

    async def list_paginated(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: PolicyStatus | None = None,
    ) -> tuple[list[Policy], int]:
        """List policies with pagination and optional status filter."""
        return await self._policy_repository.list_paginated(
            limit=limit, offset=offset, status=status
        )

    async def transition(
        self,
        policy_id: UUID,
        new_status: PolicyStatus,
        reason: str = "",
    ) -> Policy:
        """Transition a policy to a new status if the transition is legal."""
        policy = await self.get(policy_id)
        try:
            assert_transition(policy.status, new_status)
        except InvalidPolicyTransitionError as exc:
            raise InvalidPolicyTransitionError(policy.status, new_status) from exc

        updated = await self._policy_repository.update_status(policy_id, new_status)
        if updated is None:
            raise PolicyNotFoundError(str(policy_id))

        logger.info(
            "policy status changed",
            policy_id=str(policy_id),
            from_status=policy.status.value,
            to_status=new_status.value,
            reason=reason,
        )
        return updated

    def valid_next_states_for(self, policy: Policy) -> list[PolicyStatus]:
        """Return the legal next states for a policy."""
        return list(valid_next_states(policy.status))

    async def create_endorsement(
        self, policy_id: UUID, request: CreateEndorsementRequest
    ) -> Endorsement:
        """Create a new endorsement on an active policy."""
        policy = await self.get(policy_id)
        if policy.status != PolicyStatus.ACTIVE:
            raise InvalidPolicyTransitionError(policy.status, PolicyStatus.ACTIVE)

        next_number = await self._endorsement_repository.next_endorsement_number_for_policy(
            policy_id
        )
        endorsement_number = f"{policy.policy_number}-E{next_number:03d}"

        endorsement = Endorsement(
            policy_id=policy.id,
            endorsement_number=endorsement_number,
            endorsement_type=request.endorsement_type,
            description=request.description,
            effective_date=request.effective_date,
            premium_adjustment=request.premium_adjustment,
            status=EndorsementStatus.PROPOSED,
            requested_by=request.requested_by,
        )
        await self._endorsement_repository.add(endorsement)

        logger.info(
            "endorsement proposed",
            endorsement_id=str(endorsement.id),
            endorsement_number=endorsement_number,
            policy_number=policy.policy_number,
            type=request.endorsement_type.value,
            premium_adjustment=str(request.premium_adjustment),
        )
        return endorsement

    async def list_endorsements_for_policy(self, policy_id: UUID) -> list[Endorsement]:
        """Return all endorsements for a policy."""
        return await self._endorsement_repository.list_for_policy(policy_id)

    async def approve_endorsement(self, endorsement_id: UUID) -> Endorsement:
        """Approve a pending endorsement."""
        existing = await self._endorsement_repository.get_by_id(endorsement_id)
        if existing is None:
            raise EndorsementNotFoundError(str(endorsement_id))

        updated = await self._endorsement_repository.update_status(
            endorsement_id, EndorsementStatus.APPROVED
        )
        if updated is None:
            raise EndorsementNotFoundError(str(endorsement_id))

        logger.info(
            "endorsement approved",
            endorsement_id=str(endorsement_id),
            endorsement_number=existing.endorsement_number,
        )
        return updated

    async def apply_endorsement(self, endorsement_id: UUID) -> Endorsement:
        """Mark an approved endorsement as applied."""
        existing = await self._endorsement_repository.get_by_id(endorsement_id)
        if existing is None:
            raise EndorsementNotFoundError(str(endorsement_id))

        updated_existing = existing.model_copy(
            update={
                "status": EndorsementStatus.APPLIED,
                "applied_at": datetime.utcnow(),
            }
        )
        # We update via the simple status update; applied_at would normally
        # be saved with a more specialised method.
        await self._endorsement_repository.update_status(endorsement_id, EndorsementStatus.APPLIED)

        logger.info(
            "endorsement applied",
            endorsement_id=str(endorsement_id),
            endorsement_number=existing.endorsement_number,
        )
        return updated_existing

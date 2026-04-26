"""Repository for endorsement persistence operations."""

from decimal import Decimal
from uuid import UUID

from shared.database.models_endorsement import EndorsementRecord
from shared.domain import Currency, Money
from shared.domain.endorsement import Endorsement, EndorsementStatus, EndorsementType
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class EndorsementRepository:
    """Persistence operations for endorsements."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with an async DB session."""
        self._session = session

    async def add(self, endorsement: Endorsement) -> Endorsement:
        """Persist a new endorsement."""
        record = EndorsementRecord(
            id=str(endorsement.id),
            policy_id=str(endorsement.policy_id),
            endorsement_number=endorsement.endorsement_number,
            endorsement_type=endorsement.endorsement_type,
            description=endorsement.description,
            effective_date=endorsement.effective_date,
            premium_adjustment_amount=endorsement.premium_adjustment.amount,
            premium_adjustment_currency=endorsement.premium_adjustment.currency,
            status=endorsement.status,
            requested_by=endorsement.requested_by,
            applied_at=endorsement.applied_at,
        )
        self._session.add(record)
        await self._session.flush()
        return endorsement

    async def get_by_id(self, endorsement_id: UUID) -> Endorsement | None:
        """Return the endorsement with the given id."""
        record = await self._session.get(EndorsementRecord, str(endorsement_id))
        return self._to_domain(record) if record else None

    async def list_for_policy(self, policy_id: UUID) -> list[Endorsement]:
        """Return all endorsements for a policy, newest first."""
        stmt = (
            select(EndorsementRecord)
            .where(EndorsementRecord.policy_id == str(policy_id))
            .order_by(EndorsementRecord.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(record) for record in result.scalars().all()]

    async def update_status(
        self,
        endorsement_id: UUID,
        status: EndorsementStatus,
    ) -> Endorsement | None:
        """Update the status of an endorsement."""
        record = await self._session.get(EndorsementRecord, str(endorsement_id))
        if record is None:
            return None
        record.status = status
        await self._session.flush()
        return self._to_domain(record)

    async def next_endorsement_number_for_policy(self, policy_id: UUID) -> int:
        """Return the next sequential number for an endorsement on this policy."""
        stmt = (
            select(func.count())
            .select_from(EndorsementRecord)
            .where(EndorsementRecord.policy_id == str(policy_id))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() + 1

    @staticmethod
    def _to_domain(record: EndorsementRecord) -> Endorsement:
        """Convert a persistence record back to a domain Endorsement."""
        return Endorsement(
            id=UUID(record.id) if isinstance(record.id, str) else record.id,
            policy_id=(
                UUID(record.policy_id) if isinstance(record.policy_id, str) else record.policy_id
            ),
            endorsement_number=record.endorsement_number,
            endorsement_type=EndorsementType(record.endorsement_type),
            description=record.description,
            effective_date=record.effective_date,
            premium_adjustment=Money(
                amount=Decimal(str(record.premium_adjustment_amount)),
                currency=Currency(record.premium_adjustment_currency),
            ),
            status=EndorsementStatus(record.status),
            created_at=record.created_at,
            applied_at=record.applied_at,
            requested_by=record.requested_by,
        )

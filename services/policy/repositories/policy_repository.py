"""Repository for policy persistence operations."""

from decimal import Decimal
from uuid import UUID

from shared.database import PolicyRecord
from shared.domain import (
    Currency,
    DateRange,
    Money,
    Policy,
    PolicyStatus,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _as_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


class PolicyRepository:
    """Persistence operations for policies."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with an async DB session."""
        self._session = session

    async def add(self, policy: Policy) -> Policy:
        """Persist a new policy."""
        record = PolicyRecord(
            id=str(policy.id),
            policy_number=policy.policy_number,
            quote_id=str(policy.quote_id),
            submission_id=str(policy.submission_id),
            insured_name=policy.insured_name,
            status=policy.status,
            period_start=policy.period.start,
            period_end=policy.period.end,
            premium_amount=policy.premium.amount,
            premium_currency=policy.premium.currency,
            bound_at=policy.bound_at,
            bound_by=policy.bound_by,
        )
        self._session.add(record)
        await self._session.flush()
        return policy

    async def get_by_id(self, policy_id: UUID) -> Policy | None:
        """Return the policy with the given id, or None if not found."""
        record = await self._session.get(PolicyRecord, str(policy_id))
        return self._to_domain(record) if record else None

    async def get_by_number(self, policy_number: str) -> Policy | None:
        """Return the policy with the given customer-facing number."""
        stmt = select(PolicyRecord).where(PolicyRecord.policy_number == policy_number)
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()
        return self._to_domain(record) if record else None

    async def get_by_quote_id(self, quote_id: UUID) -> Policy | None:
        """Return the policy bound from the given quote, if any."""
        stmt = select(PolicyRecord).where(PolicyRecord.quote_id == str(quote_id))
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()
        return self._to_domain(record) if record else None

    async def update_status(self, policy_id: UUID, status: PolicyStatus) -> Policy | None:
        """Update the status of an existing policy."""
        record = await self._session.get(PolicyRecord, str(policy_id))
        if record is None:
            return None
        record.status = status
        await self._session.flush()
        return self._to_domain(record)

    async def list_paginated(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: PolicyStatus | None = None,
    ) -> tuple[list[Policy], int]:
        """Return a paginated list of policies and the total count."""
        base_stmt = select(PolicyRecord)
        count_stmt = select(func.count()).select_from(PolicyRecord)

        if status is not None:
            base_stmt = base_stmt.where(PolicyRecord.status == status)
            count_stmt = count_stmt.where(PolicyRecord.status == status)

        base_stmt = base_stmt.order_by(PolicyRecord.bound_at.desc()).limit(limit).offset(offset)

        items_result = await self._session.execute(base_stmt)
        total_result = await self._session.execute(count_stmt)

        records = items_result.scalars().all()
        total = total_result.scalar_one()

        return [self._to_domain(record) for record in records], total

    async def next_policy_number(self) -> int:
        """Return the next sequential number for a policy reference."""
        stmt = select(func.count()).select_from(PolicyRecord)
        result = await self._session.execute(stmt)
        return result.scalar_one() + 1

    @staticmethod
    def _to_domain(record: PolicyRecord) -> Policy:
        """Convert a persistence record back to a domain Policy."""
        return Policy(
            id=_as_uuid(record.id),
            policy_number=record.policy_number,
            quote_id=_as_uuid(record.quote_id),
            submission_id=_as_uuid(record.submission_id),
            insured_name=record.insured_name,
            status=PolicyStatus(record.status),
            period=DateRange(start=record.period_start, end=record.period_end),
            premium=Money(
                amount=Decimal(str(record.premium_amount)),
                currency=Currency(record.premium_currency),
            ),
            bound_at=record.bound_at,
            bound_by=record.bound_by,
        )

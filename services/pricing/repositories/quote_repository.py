"""Repository for quote persistence operations."""

from decimal import Decimal
from uuid import UUID

from shared.database import QuoteRecord
from shared.domain import (
    Coverage,
    CoverageType,
    Currency,
    DateRange,
    Money,
    Quote,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _as_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


class QuoteRepository:
    """Persistence operations for quotes."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with an async DB session."""
        self._session = session

    async def add(self, quote: Quote) -> Quote:
        """Persist a new quote."""
        record = QuoteRecord(
            id=str(quote.id),
            submission_id=str(quote.submission_id),
            quote_reference=quote.quote_reference,
            premium_amount=quote.premium.amount,
            premium_currency=quote.premium.currency,
            excess_amount=quote.excess.amount,
            excess_currency=quote.excess.currency,
            coverage_type=quote.coverage.coverage_type,
            coverage_start=quote.coverage.period.start,
            coverage_end=quote.coverage.period.end,
            valid_until=quote.valid_until,
            rationale=quote.rationale,
        )
        self._session.add(record)
        await self._session.flush()
        return quote

    async def get_by_id(self, quote_id: UUID) -> Quote | None:
        """Return the quote with the given id."""
        record = await self._session.get(QuoteRecord, str(quote_id))
        return self._to_domain(record) if record else None

    async def get_by_reference(self, reference: str) -> Quote | None:
        """Return the quote with the given reference."""
        stmt = select(QuoteRecord).where(QuoteRecord.quote_reference == reference)
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()
        return self._to_domain(record) if record else None

    async def list_for_submission(self, submission_id: UUID) -> list[Quote]:
        """Return all quotes for a submission, newest first."""
        stmt = (
            select(QuoteRecord)
            .where(QuoteRecord.submission_id == str(submission_id))
            .order_by(QuoteRecord.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(record) for record in result.scalars().all()]

    async def list_paginated(self, *, limit: int = 50, offset: int = 0) -> tuple[list[Quote], int]:
        """Return a paginated list of quotes and the total count."""
        items_stmt = (
            select(QuoteRecord).order_by(QuoteRecord.created_at.desc()).limit(limit).offset(offset)
        )
        count_stmt = select(func.count()).select_from(QuoteRecord)

        items_result = await self._session.execute(items_stmt)
        total_result = await self._session.execute(count_stmt)

        records = items_result.scalars().all()
        total = total_result.scalar_one()

        return [self._to_domain(record) for record in records], total

    async def next_reference_number(self) -> int:
        """Return the next sequential number for a quote reference."""
        stmt = select(func.count()).select_from(QuoteRecord)
        result = await self._session.execute(stmt)
        return result.scalar_one() + 1

    @staticmethod
    def _to_domain(record: QuoteRecord) -> Quote:
        """Convert a persistence record back to a domain Quote."""
        return Quote(
            id=_as_uuid(record.id),
            submission_id=_as_uuid(record.submission_id),
            quote_reference=record.quote_reference,
            premium=Money(
                amount=Decimal(str(record.premium_amount)),
                currency=Currency(record.premium_currency),
            ),
            excess=Money(
                amount=Decimal(str(record.excess_amount)),
                currency=Currency(record.excess_currency),
            ),
            coverage=Coverage(
                coverage_type=CoverageType(record.coverage_type),
                period=DateRange(start=record.coverage_start, end=record.coverage_end),
                excess=Money(
                    amount=Decimal(str(record.excess_amount)),
                    currency=Currency(record.excess_currency),
                ),
            ),
            valid_until=record.valid_until,
            rationale=record.rationale,
            created_at=record.created_at,
        )

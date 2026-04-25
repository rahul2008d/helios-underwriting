"""Repository encapsulating database access for submissions.

The repository converts between domain objects (Submission) and persistence
records (SubmissionRecord). Business logic in the service layer should never
touch SQLAlchemy directly - it goes through this repository.
"""

from decimal import Decimal
from uuid import UUID

from shared.database import SubmissionRecord
from shared.domain import (
    Address,
    Coverage,
    CoverageType,
    Currency,
    DateRange,
    Driver,
    Money,
    Submission,
    SubmissionStatus,
    Vehicle,
    VehicleType,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class SubmissionRepository:
    """Persistence operations for submissions."""

    def __init__(self, session: AsyncSession) -> None:
        """Build a repository bound to the given async ORM session."""
        self._session = session

    async def add(self, submission: Submission) -> Submission:
        """Persist a new submission."""
        record = self._to_record(submission)
        self._session.add(record)
        await self._session.flush()
        return submission

    async def get_by_id(self, submission_id: UUID) -> Submission | None:
        """Return the submission with the given id, or None if not found."""
        record = await self._session.get(SubmissionRecord, str(submission_id))
        return self._to_domain(record) if record else None

    async def get_by_reference(self, reference: str) -> Submission | None:
        """Return the submission with the given broker reference."""
        stmt = select(SubmissionRecord).where(SubmissionRecord.reference == reference)
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()
        return self._to_domain(record) if record else None

    async def list_paginated(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: SubmissionStatus | None = None,
    ) -> tuple[list[Submission], int]:
        """Return a paginated list of submissions and the total count."""
        base_stmt = select(SubmissionRecord)
        count_stmt = select(func.count()).select_from(SubmissionRecord)

        if status is not None:
            base_stmt = base_stmt.where(SubmissionRecord.status == status)
            count_stmt = count_stmt.where(SubmissionRecord.status == status)

        base_stmt = (
            base_stmt.order_by(SubmissionRecord.received_at.desc()).limit(limit).offset(offset)
        )

        items_result = await self._session.execute(base_stmt)
        total_result = await self._session.execute(count_stmt)

        records = items_result.scalars().all()
        total = total_result.scalar_one()

        return [self._to_domain(r) for r in records], total

    async def update_status(
        self, submission_id: UUID, status: SubmissionStatus
    ) -> Submission | None:
        """Update the status of an existing submission."""
        record = await self._session.get(SubmissionRecord, str(submission_id))
        if record is None:
            return None
        record.status = status
        await self._session.flush()
        return self._to_domain(record)

    @staticmethod
    def _to_record(submission: Submission) -> SubmissionRecord:
        """Convert a domain Submission to a persistence record."""
        return SubmissionRecord(
            id=str(submission.id),
            reference=submission.reference,
            received_at=submission.received_at,
            status=submission.status,
            insured_name=submission.insured_name,
            insured_address=submission.insured_address.model_dump(mode="json"),
            business_description=submission.business_description,
            annual_revenue_amount=submission.annual_revenue.amount,
            annual_revenue_currency=submission.annual_revenue.currency,
            vehicles=[v.model_dump(mode="json") for v in submission.vehicles],
            drivers=[d.model_dump(mode="json") for d in submission.drivers],
            operates_internationally=submission.operates_internationally,
            countries_of_operation=submission.countries_of_operation,
            claims_count_5y=submission.claims_count_5y,
            claims_value_amount=submission.claims_value_5y.amount,
            claims_value_currency=submission.claims_value_5y.currency,
            coverage_type=submission.requested_coverage.coverage_type,
            coverage_start=submission.requested_coverage.period.start,
            coverage_end=submission.requested_coverage.period.end,
            coverage_excess_amount=submission.requested_coverage.excess.amount,
            coverage_excess_currency=submission.requested_coverage.excess.currency,
        )

    @staticmethod
    def _to_domain(record: SubmissionRecord) -> Submission:
        """Convert a persistence record back to a domain Submission."""
        raw_id = record.id
        submission_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
        return Submission(
            id=submission_id,
            reference=record.reference,
            received_at=record.received_at,
            status=SubmissionStatus(record.status),
            insured_name=record.insured_name,
            insured_address=Address.model_validate(record.insured_address),
            business_description=record.business_description,
            annual_revenue=Money(
                amount=Decimal(str(record.annual_revenue_amount)),
                currency=Currency(record.annual_revenue_currency),
            ),
            vehicles=[
                Vehicle.model_validate(
                    {
                        **v,
                        "vehicle_type": VehicleType(v["vehicle_type"]),
                    }
                )
                for v in record.vehicles
            ],
            drivers=[Driver.model_validate(d) for d in record.drivers],
            operates_internationally=record.operates_internationally,
            countries_of_operation=record.countries_of_operation,
            claims_count_5y=record.claims_count_5y,
            claims_value_5y=Money(
                amount=Decimal(str(record.claims_value_amount)),
                currency=Currency(record.claims_value_currency),
            ),
            requested_coverage=Coverage(
                coverage_type=CoverageType(record.coverage_type),
                period=DateRange(start=record.coverage_start, end=record.coverage_end),
                excess=Money(
                    amount=Decimal(str(record.coverage_excess_amount)),
                    currency=Currency(record.coverage_excess_currency),
                ),
            ),
        )

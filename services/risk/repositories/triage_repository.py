"""Persistence for triage results."""

from uuid import UUID

from shared.database import TriageResultRecord
from shared.domain import TriageDecision, TriageResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TriageRepository:
    """Persistence operations for triage results."""

    def __init__(self, session: AsyncSession) -> None:
        """Build a repository using the given async ORM session."""
        self._session = session

    async def add(self, result: TriageResult) -> TriageResult:
        """Persist a triage result."""
        record = TriageResultRecord(
            submission_id=str(result.submission_id),
            decision=result.decision,
            confidence=result.confidence,
            reasoning=result.reasoning,
            appetite_matches=result.appetite_matches,
            appetite_concerns=result.appetite_concerns,
            triaged_at=result.triaged_at,
        )
        self._session.add(record)
        await self._session.flush()
        return result

    async def latest_for_submission(self, submission_id: UUID) -> TriageResult | None:
        """Return the most recent triage result for a submission."""
        stmt = (
            select(TriageResultRecord)
            .where(TriageResultRecord.submission_id == str(submission_id))
            .order_by(TriageResultRecord.triaged_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            return None

        raw_id = record.submission_id
        sub_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))

        return TriageResult(
            submission_id=sub_id,
            decision=TriageDecision(record.decision),
            confidence=float(record.confidence),
            reasoning=record.reasoning,
            appetite_matches=record.appetite_matches,
            appetite_concerns=record.appetite_concerns,
            triaged_at=record.triaged_at,
        )

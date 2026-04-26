"""Persistence for risk assessment results."""

from uuid import UUID

from shared.database import RiskAssessmentRecord
from shared.domain import RiskAssessment, RiskBand
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AssessmentRepository:
    """Persistence operations for risk assessments."""

    def __init__(self, session: AsyncSession) -> None:
        """Build a repository using the given async ORM session."""
        self._session = session

    async def add(self, assessment: RiskAssessment) -> RiskAssessment:
        """Persist a risk assessment."""
        record = RiskAssessmentRecord(
            submission_id=str(assessment.submission_id),
            risk_band=assessment.risk_band,
            risk_score=assessment.risk_score,
            factors=assessment.factors,
            summary=assessment.summary,
            assessed_at=assessment.assessed_at,
        )
        self._session.add(record)
        await self._session.flush()
        return assessment

    async def latest_for_submission(self, submission_id: UUID) -> RiskAssessment | None:
        """Return the most recent risk assessment for a submission."""
        stmt = (
            select(RiskAssessmentRecord)
            .where(RiskAssessmentRecord.submission_id == str(submission_id))
            .order_by(RiskAssessmentRecord.assessed_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            return None

        raw_id = record.submission_id
        sub_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))

        return RiskAssessment(
            submission_id=sub_id,
            risk_band=RiskBand(record.risk_band),
            risk_score=float(record.risk_score),
            factors=record.factors,
            summary=record.summary,
            assessed_at=record.assessed_at,
        )

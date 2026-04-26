"""FastAPI dependency providers for the risk service."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from shared.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

from services.risk.repositories import AssessmentRepository, TriageRepository
from services.risk.services import RiskService
from services.submission.repositories import SubmissionRepository


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a managed async database session."""
    async for session in get_db_session():
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_risk_service(session: SessionDep) -> RiskService:
    """Build a RiskService for the request."""
    return RiskService(
        submission_repository=SubmissionRepository(session),
        triage_repository=TriageRepository(session),
        assessment_repository=AssessmentRepository(session),
    )


RiskServiceDep = Annotated[RiskService, Depends(get_risk_service)]

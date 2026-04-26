"""FastAPI dependencies for the policy service."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from shared.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

from services.policy.repositories import EndorsementRepository, PolicyRepository
from services.policy.services import PolicyService
from services.pricing.repositories import QuoteRepository
from services.submission.repositories import SubmissionRepository


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a managed async database session."""
    async for session in get_db_session():
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_policy_service(session: SessionDep) -> PolicyService:
    """Build a PolicyService for the request."""
    return PolicyService(
        policy_repository=PolicyRepository(session),
        endorsement_repository=EndorsementRepository(session),
        quote_repository=QuoteRepository(session),
        submission_repository=SubmissionRepository(session),
    )


PolicyServiceDep = Annotated[PolicyService, Depends(get_policy_service)]

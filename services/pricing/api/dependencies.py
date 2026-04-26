"""FastAPI dependencies for the pricing service."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from shared.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

from services.pricing.repositories import QuoteRepository
from services.pricing.services import PricingService
from services.submission.repositories import SubmissionRepository


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a managed async database session."""
    async for session in get_db_session():
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_quote_repository(session: SessionDep) -> QuoteRepository:
    """Build a QuoteRepository for the request."""
    return QuoteRepository(session)


QuoteRepositoryDep = Annotated[QuoteRepository, Depends(get_quote_repository)]


def get_submission_repository(session: SessionDep) -> SubmissionRepository:
    """Build a SubmissionRepository for the request."""
    return SubmissionRepository(session)


SubmissionRepositoryDep = Annotated[SubmissionRepository, Depends(get_submission_repository)]


def get_pricing_service(
    quote_repository: QuoteRepositoryDep,
    submission_repository: SubmissionRepositoryDep,
) -> PricingService:
    """Build a PricingService for the request."""
    return PricingService(
        quote_repository=quote_repository,
        submission_repository=submission_repository,
    )


PricingServiceDep = Annotated[PricingService, Depends(get_pricing_service)]

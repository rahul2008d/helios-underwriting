"""FastAPI dependencies for the RAG service."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from shared.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

from services.rag.repositories import HistoricalPolicyRepository
from services.rag.services import SimilarityService
from services.submission.repositories import SubmissionRepository


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a managed async database session."""
    async for session in get_db_session():
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_historical_repository(session: SessionDep) -> HistoricalPolicyRepository:
    """Build a HistoricalPolicyRepository for the request."""
    return HistoricalPolicyRepository(session)


HistoricalRepositoryDep = Annotated[HistoricalPolicyRepository, Depends(get_historical_repository)]


def get_submission_repository(session: SessionDep) -> SubmissionRepository:
    """Build a SubmissionRepository for the request."""
    return SubmissionRepository(session)


SubmissionRepositoryDep = Annotated[SubmissionRepository, Depends(get_submission_repository)]


def get_similarity_service(repository: HistoricalRepositoryDep) -> SimilarityService:
    """Build a SimilarityService for the request."""
    return SimilarityService(repository=repository)


SimilarityServiceDep = Annotated[SimilarityService, Depends(get_similarity_service)]

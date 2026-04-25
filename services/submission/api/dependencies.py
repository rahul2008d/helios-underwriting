"""FastAPI dependency providers for the submission service."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from shared.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

from services.submission.repositories import SubmissionRepository
from services.submission.services import SubmissionService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency yielding a managed async database session."""
    async for session in get_db_session():
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_submission_repository(session: SessionDep) -> SubmissionRepository:
    """Build a SubmissionRepository bound to the request's session."""
    return SubmissionRepository(session)


SubmissionRepositoryDep = Annotated[SubmissionRepository, Depends(get_submission_repository)]


def get_submission_service(repository: SubmissionRepositoryDep) -> SubmissionService:
    """Build a SubmissionService for the request."""
    return SubmissionService(repository)


SubmissionServiceDep = Annotated[SubmissionService, Depends(get_submission_service)]

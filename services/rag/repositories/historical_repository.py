"""Repository for historical policies."""

from shared.database import HistoricalPolicyRecord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class HistoricalPolicyRepository:
    """Persistence operations for historical policies used in RAG."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with an async DB session."""
        self._session = session

    async def add(self, record: HistoricalPolicyRecord) -> HistoricalPolicyRecord:
        """Persist a new historical policy record."""
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_all(self) -> list[HistoricalPolicyRecord]:
        """Return all historical policies."""
        stmt = select(HistoricalPolicyRecord)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Return the number of historical policies."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(HistoricalPolicyRecord)
        result = await self._session.execute(stmt)
        return result.scalar_one()

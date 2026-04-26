"""Shared pytest fixtures and configuration."""

import os
from collections.abc import AsyncGenerator
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force test environment before any imports trigger settings.
os.environ.setdefault("ENVIRONMENT", "test")

from services.submission.api.dependencies import get_session
from services.submission.main import create_app
from services.submission.schemas import CreateSubmissionRequest
from shared.database import Base
from shared.database import models as _models  # noqa: F401  - register models
from shared.database import models_endorsement as _models_endorsement  # noqa: F401
from shared.database import models_historical as _models_historical  # noqa: F401
from shared.domain import (
    Address,
    Coverage,
    CoverageType,
    DateRange,
    Driver,
    Money,
    Vehicle,
    VehicleType,
)

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "mysql+aiomysql://helios:helios_dev@localhost:3306/helios_test",  # pragma: allowlist secret
)


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Async engine pointed at the test database, with schema reset per session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test async session that rolls back at the end."""
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX AsyncClient bound to the FastAPI app with the test DB session."""
    app = create_app()

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def sample_submission_payload() -> dict:
    """Build a JSON payload representing a small valid submission."""
    request = CreateSubmissionRequest(
        reference="BRK-TEST-0001",
        insured_name="Test Logistics Ltd",
        insured_address=Address(
            line_1="86-90 Paul Street",
            city="London",
            postcode="EC2A 4NE",
        ),
        business_description="Test couriers operating in central London.",
        annual_revenue=Money(amount=Decimal("750000")),
        vehicles=[
            Vehicle(
                registration="AB12CDE",
                vehicle_type=VehicleType.VAN,
                make="Ford",
                model="Transit",
                year=2022,
                value=Money(amount=Decimal("25000")),
                annual_mileage=30_000,
                gross_weight_kg=3500,
            )
        ],
        drivers=[
            Driver(
                full_name="Test Driver",
                licence_number="TEST123456",
                date_of_birth=date(1990, 6, 15),
                years_licensed=15,
            )
        ],
        requested_coverage=Coverage(
            coverage_type=CoverageType.COMPREHENSIVE,
            period=DateRange(start=date(2026, 5, 1), end=date(2027, 4, 30)),
            excess=Money(amount=Decimal("500")),
        ),
    )
    return request.model_dump(mode="json")

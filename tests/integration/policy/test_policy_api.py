"""Integration tests for the policy API."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from services.policy.api.dependencies import get_session as policy_get_session
from services.policy.main import create_app
from services.pricing.repositories import QuoteRepository
from services.submission.repositories import SubmissionRepository
from shared.domain import (
    Address,
    Coverage,
    CoverageType,
    DateRange,
    Driver,
    Money,
    Quote,
    Submission,
    Vehicle,
    VehicleType,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    """HTTPX AsyncClient bound to the policy FastAPI app with the test DB session."""
    app = create_app()

    async def _override_session():
        yield session

    app.dependency_overrides[policy_get_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def seeded_quote(session: AsyncSession) -> Quote:
    """Create a submission and a quote for use in policy tests."""
    submission = Submission(
        reference=f"BRK-POLICY-{uuid4().hex[:12].upper()}",
        insured_name="Policy Test Ltd",
        insured_address=Address(line_1="86-90 Paul Street", city="London", postcode="EC2A 4NE"),
        business_description="Policy test fleet",
        annual_revenue=Money(amount=Decimal("500000")),
        vehicles=[
            Vehicle(
                registration="PL01ABC",
                vehicle_type=VehicleType.VAN,
                make="Ford",
                model="Transit",
                year=2022,
                value=Money(amount=Decimal("25000")),
                annual_mileage=30_000,
            )
        ],
        drivers=[
            Driver(
                full_name="Test Driver",
                licence_number="TEST123456",
                date_of_birth=date(1985, 6, 15),
                years_licensed=20,
            )
        ],
        requested_coverage=Coverage(
            coverage_type=CoverageType.COMPREHENSIVE,
            period=DateRange(start=date(2026, 5, 1), end=date(2027, 4, 30)),
            excess=Money(amount=Decimal("500")),
        ),
    )
    submission_repo = SubmissionRepository(session)
    await submission_repo.add(submission)

    quote = Quote(
        submission_id=submission.id,
        quote_reference=f"QUO-2026-{uuid4().hex[:8].upper()}",
        premium=Money(amount=Decimal("1500.00")),
        excess=Money(amount=Decimal("500.00")),
        coverage=submission.requested_coverage,
        valid_until=date.today() + timedelta(days=30),
        rationale="Standard rate.",
    )
    quote_repo = QuoteRepository(session)
    await quote_repo.add(quote)
    await session.commit()
    return quote


@pytest.mark.integration
class TestBindPolicy:
    async def test_binds_quote_returns_201(self, client: AsyncClient, seeded_quote: Quote):
        response = await client.post(
            "/v1/policies/bind",
            json={
                "quote_id": str(seeded_quote.id),
                "bound_by": "test_user",
            },
        )
        assert response.status_code == 201, response.text

    async def test_returns_active_status(self, client: AsyncClient, seeded_quote: Quote):
        response = await client.post(
            "/v1/policies/bind",
            json={"quote_id": str(seeded_quote.id), "bound_by": "test_user"},
        )
        body = response.json()
        assert body["status"] == "active"
        assert body["policy_number"].startswith("POL-")

    async def test_returns_409_for_already_bound_quote(
        self, client: AsyncClient, seeded_quote: Quote
    ):
        first = await client.post(
            "/v1/policies/bind",
            json={"quote_id": str(seeded_quote.id), "bound_by": "test_user"},
        )
        assert first.status_code == 201

        second = await client.post(
            "/v1/policies/bind",
            json={"quote_id": str(seeded_quote.id), "bound_by": "another_user"},
        )
        assert second.status_code == 409

    async def test_returns_404_for_unknown_quote(self, client: AsyncClient):
        response = await client.post(
            "/v1/policies/bind",
            json={
                "quote_id": "00000000-0000-0000-0000-000000000000",
                "bound_by": "test_user",
            },
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestPolicyTransitions:
    async def test_can_cancel_active_policy(self, client: AsyncClient, seeded_quote: Quote):
        bind_response = await client.post(
            "/v1/policies/bind",
            json={"quote_id": str(seeded_quote.id), "bound_by": "test_user"},
        )
        policy_id = bind_response.json()["id"]

        response = await client.post(
            f"/v1/policies/{policy_id}/transition",
            json={"new_status": "cancelled", "reason": "Customer request"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_cannot_reactivate_cancelled_policy(
        self, client: AsyncClient, seeded_quote: Quote
    ):
        bind_response = await client.post(
            "/v1/policies/bind",
            json={"quote_id": str(seeded_quote.id), "bound_by": "test_user"},
        )
        policy_id = bind_response.json()["id"]

        # Cancel first
        await client.post(
            f"/v1/policies/{policy_id}/transition",
            json={"new_status": "cancelled", "reason": "Customer request"},
        )

        # Now try to reactivate (illegal)
        response = await client.post(
            f"/v1/policies/{policy_id}/transition",
            json={"new_status": "active"},
        )

        assert response.status_code == 409


@pytest.mark.integration
class TestEndorsements:
    async def test_creates_endorsement_on_active_policy(
        self, client: AsyncClient, seeded_quote: Quote
    ):
        bind_response = await client.post(
            "/v1/policies/bind",
            json={"quote_id": str(seeded_quote.id), "bound_by": "test_user"},
        )
        policy_id = bind_response.json()["id"]

        response = await client.post(
            f"/v1/policies/{policy_id}/endorsements",
            json={
                "endorsement_type": "add_vehicle",
                "description": "Add new Ford Transit AB99XYZ",
                "effective_date": "2026-07-01",
                "premium_adjustment": {"amount": "350.00", "currency": "GBP"},
                "requested_by": "broker_alice",
            },
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["status"] == "proposed"
        assert "E001" in body["endorsement_number"]

    async def test_can_approve_endorsement(self, client: AsyncClient, seeded_quote: Quote):
        bind_response = await client.post(
            "/v1/policies/bind",
            json={"quote_id": str(seeded_quote.id), "bound_by": "test_user"},
        )
        policy_id = bind_response.json()["id"]

        endorsement_response = await client.post(
            f"/v1/policies/{policy_id}/endorsements",
            json={
                "endorsement_type": "add_vehicle",
                "description": "Add new vehicle",
                "effective_date": "2026-07-01",
                "premium_adjustment": {"amount": "350.00", "currency": "GBP"},
                "requested_by": "broker",
            },
        )
        endorsement_id = endorsement_response.json()["id"]

        response = await client.post(f"/v1/policies/endorsements/{endorsement_id}/approve")

        assert response.status_code == 200
        assert response.json()["status"] == "approved"


@pytest.mark.integration
class TestHealthCheck:
    async def test_health_returns_ok(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "policy"

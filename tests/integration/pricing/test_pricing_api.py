"""Integration tests for the pricing API."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from services.pricing.api.dependencies import get_session as pricing_get_session
from services.pricing.main import create_app
from services.submission.repositories import SubmissionRepository
from shared.domain import (
    Address,
    Coverage,
    CoverageType,
    DateRange,
    Driver,
    Money,
    Submission,
    Vehicle,
    VehicleType,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    """HTTPX AsyncClient bound to the pricing FastAPI app with the test DB session."""
    app = create_app()

    async def _override_session():
        yield session

    app.dependency_overrides[pricing_get_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def seeded_submission(session: AsyncSession) -> Submission:
    """Create and persist a submission for use in pricing tests."""
    submission = Submission(
        reference=f"BRK-PRICING-{uuid4().hex[:12].upper()}",
        insured_name="Pricing Test Ltd",
        insured_address=Address(line_1="86-90 Paul Street", city="London", postcode="EC2A 4NE"),
        business_description="Test fleet",
        annual_revenue=Money(amount=Decimal("500000")),
        vehicles=[
            Vehicle(
                registration="PT01ABC",
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
    repo = SubmissionRepository(session)
    await repo.add(submission)
    await session.commit()
    return submission


@pytest.fixture
def quote_payload(seeded_submission: Submission) -> dict:
    """Sample payload for creating a quote."""
    return {
        "submission_id": str(seeded_submission.id),
        "premium": {"amount": "1500.00", "currency": "GBP"},
        "excess": {"amount": "500.00", "currency": "GBP"},
        "coverage": {
            "coverage_type": "comprehensive",
            "period": {"start": "2026-05-01", "end": "2027-04-30"},
            "excess": {"amount": "500.00", "currency": "GBP"},
        },
        "valid_until": "2026-06-15",
        "rationale": "Standard van rate, low risk fleet.",
    }


@pytest.mark.integration
class TestCreateQuote:
    async def test_creates_quote_returns_201(self, client: AsyncClient, quote_payload: dict):
        response = await client.post("/v1/quotes", json=quote_payload)
        assert response.status_code == 201, response.text

    async def test_response_contains_generated_reference(
        self, client: AsyncClient, quote_payload: dict
    ):
        response = await client.post("/v1/quotes", json=quote_payload)
        body = response.json()
        assert "id" in body
        assert body["quote_reference"].startswith("QUO-")
        assert body["is_expired"] is False

    async def test_returns_404_for_unknown_submission(
        self, client: AsyncClient, quote_payload: dict
    ):
        quote_payload["submission_id"] = "00000000-0000-0000-0000-000000000000"
        response = await client.post("/v1/quotes", json=quote_payload)
        assert response.status_code == 404


@pytest.mark.integration
class TestGetQuote:
    async def test_returns_quote_by_id(self, client: AsyncClient, quote_payload: dict):
        create_response = await client.post("/v1/quotes", json=quote_payload)
        quote_id = create_response.json()["id"]

        response = await client.get(f"/v1/quotes/{quote_id}")

        assert response.status_code == 200
        assert response.json()["id"] == quote_id

    async def test_returns_404_for_unknown_id(self, client: AsyncClient):
        response = await client.get("/v1/quotes/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


@pytest.mark.integration
class TestQuotePdf:
    async def test_returns_pdf_with_correct_content_type(
        self, client: AsyncClient, quote_payload: dict
    ):
        create_response = await client.post("/v1/quotes", json=quote_payload)
        quote_id = create_response.json()["id"]

        response = await client.get(f"/v1/quotes/{quote_id}/pdf")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    async def test_pdf_starts_with_valid_header(self, client: AsyncClient, quote_payload: dict):
        create_response = await client.post("/v1/quotes", json=quote_payload)
        quote_id = create_response.json()["id"]

        response = await client.get(f"/v1/quotes/{quote_id}/pdf")

        assert response.content.startswith(b"%PDF-1.4")


@pytest.mark.integration
class TestListQuotes:
    async def test_returns_empty_list_when_none_exist(self, client: AsyncClient):
        response = await client.get("/v1/quotes")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0

    async def test_lists_created_quotes(self, client: AsyncClient, quote_payload: dict):
        await client.post("/v1/quotes", json=quote_payload)
        response = await client.get("/v1/quotes")
        body = response.json()
        assert body["total"] == 1


@pytest.mark.integration
class TestHealthCheck:
    async def test_health_returns_ok(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

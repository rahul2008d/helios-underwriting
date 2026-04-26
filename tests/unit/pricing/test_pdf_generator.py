"""Unit tests for the quote PDF generator."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from services.pricing.services.pdf_generator import generate_quote_pdf
from shared.domain import (
    Address,
    Coverage,
    CoverageType,
    Currency,
    DateRange,
    Driver,
    Money,
    Quote,
    Submission,
    Vehicle,
    VehicleType,
)


@pytest.fixture
def sample_submission() -> Submission:
    return Submission(
        reference="BRK-TEST-0001",
        insured_name="Test Logistics Ltd",
        insured_address=Address(
            line_1="86-90 Paul Street",
            city="London",
            postcode="EC2A 4NE",
        ),
        business_description="Test couriers",
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


@pytest.fixture
def sample_quote(sample_submission: Submission) -> Quote:
    return Quote(
        id=uuid4(),
        submission_id=sample_submission.id,
        quote_reference="QUO-2026-0001",
        premium=Money(amount=Decimal("1750.50"), currency=Currency.GBP),
        excess=Money(amount=Decimal("500"), currency=Currency.GBP),
        coverage=sample_submission.requested_coverage,
        valid_until=date(2026, 6, 1),
        rationale="Premium reflects clean fleet and experienced drivers.",
    )


class TestGenerateQuotePdf:
    def test_returns_bytes(self, sample_quote, sample_submission):
        result = generate_quote_pdf(sample_quote, sample_submission)
        assert isinstance(result, bytes)

    def test_starts_with_pdf_header(self, sample_quote, sample_submission):
        result = generate_quote_pdf(sample_quote, sample_submission)
        assert result.startswith(b"%PDF-1.4")

    def test_ends_with_pdf_eof(self, sample_quote, sample_submission):
        result = generate_quote_pdf(sample_quote, sample_submission)
        assert result.endswith(b"%%EOF")

    def test_contains_quote_reference(self, sample_quote, sample_submission):
        result = generate_quote_pdf(sample_quote, sample_submission)
        assert b"QUO-2026-0001" in result

    def test_contains_insured_name(self, sample_quote, sample_submission):
        result = generate_quote_pdf(sample_quote, sample_submission)
        assert b"Test Logistics Ltd" in result

    def test_contains_premium_amount(self, sample_quote, sample_submission):
        result = generate_quote_pdf(sample_quote, sample_submission)
        # Money is formatted as "GBP 1,750.50"
        assert b"1,750.50" in result

    def test_handles_long_rationale(self, sample_quote, sample_submission):
        long_rationale = "Premium reflects clean fleet. " * 20
        long_quote = sample_quote.model_copy(update={"rationale": long_rationale})
        result = generate_quote_pdf(long_quote, sample_submission)
        # Just verify it doesn't crash and produces a valid-ish PDF
        assert result.startswith(b"%PDF")
        assert result.endswith(b"%%EOF")

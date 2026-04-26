"""Unit tests for the embedding service helpers."""

import math
from datetime import date
from decimal import Decimal

import pytest
from services.rag.services import cosine_similarity, submission_to_embedding_text
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


class TestCosineSimilarity:
    def test_identical_vectors_return_one(self):
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_return_zero(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors_return_minus_one(self):
        a = [1.0, 2.0]
        b = [-1.0, -2.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_normalised_vectors_match_dot_product(self):
        # OpenAI returns normalised embeddings; cosine == dot product
        a = [0.6, 0.8]  # length 1
        b = [0.8, 0.6]  # length 1
        expected = 0.6 * 0.8 + 0.8 * 0.6
        assert cosine_similarity(a, b) == pytest.approx(expected)

    def test_zero_vector_returns_zero(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, b) == 0.0

    def test_different_length_vectors_raise(self):
        with pytest.raises(ValueError, match="same length"):
            cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])

    def test_known_value(self):
        # Hand-computed: cos((1,1), (1,0)) = 1/sqrt(2)
        result = cosine_similarity([1.0, 1.0], [1.0, 0.0])
        assert result == pytest.approx(1.0 / math.sqrt(2))


class TestSubmissionToEmbeddingText:
    def test_includes_key_fields(self):
        submission = Submission(
            reference="BRK-TEST-0001",
            insured_name="Acme Logistics",
            insured_address=Address(
                line_1="86-90 Paul Street",
                city="London",
                postcode="EC2A 4NE",
            ),
            business_description="Regional courier service",
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
            claims_count_5y=2,
            claims_value_5y=Money(amount=Decimal("8500")),
            requested_coverage=Coverage(
                coverage_type=CoverageType.COMPREHENSIVE,
                period=DateRange(start=date(2026, 5, 1), end=date(2027, 4, 30)),
                excess=Money(amount=Decimal("500")),
            ),
        )

        text = submission_to_embedding_text(submission)

        assert "Acme Logistics" in text
        assert "Regional courier service" in text
        assert "1 van vehicles" in text
        assert "Annual revenue" in text
        assert "Claims in last 5 years: 2" in text

    def test_includes_driver_licence_tenure_in_text(self):
        """Embedding text should mention driver years licensed (submission requires ≥1 driver)."""
        submission = Submission(
            reference="BRK-TEST-0002",
            insured_name="Test",
            insured_address=Address(line_1="1 Test St", city="London", postcode="EC2A 4NE"),
            business_description="Test",
            annual_revenue=Money(amount=Decimal("1")),
            vehicles=[
                Vehicle(
                    registration="AB12CDE",
                    vehicle_type=VehicleType.VAN,
                    make="Ford",
                    model="Transit",
                    year=2022,
                    value=Money(amount=Decimal("1")),
                    annual_mileage=10_000,
                )
            ],
            drivers=[
                Driver(
                    full_name="Test Driver",
                    licence_number="LIC123456",
                    date_of_birth=date(1990, 1, 1),
                    years_licensed=10,
                )
            ],
            requested_coverage=Coverage(
                coverage_type=CoverageType.COMPREHENSIVE,
                period=DateRange(start=date(2026, 5, 1), end=date(2027, 4, 30)),
                excess=Money(amount=Decimal("100")),
            ),
        )
        text = submission_to_embedding_text(submission)
        assert "10.0 years" in text

"""Unit tests for the deterministic pricing logic.

Tests the base premium calculation and risk loading combination without
invoking the LLM.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from services.risk.agents.pricing_agent import PricingAgent
from shared.domain import (
    Address,
    Coverage,
    CoverageType,
    DateRange,
    Driver,
    Money,
    RiskAssessment,
    RiskBand,
    Submission,
    Vehicle,
    VehicleType,
)


@pytest.fixture
def address() -> Address:
    return Address(line_1="86-90 Paul Street", city="London", postcode="EC2A 4NE")


@pytest.fixture
def coverage() -> Coverage:
    return Coverage(
        coverage_type=CoverageType.COMPREHENSIVE,
        period=DateRange(start=date(2026, 5, 1), end=date(2027, 4, 30)),
        excess=Money(amount=Decimal("500")),
    )


def _make_van(*, mileage: int = 30_000) -> Vehicle:
    return Vehicle(
        registration="AB12CDE",
        vehicle_type=VehicleType.VAN,
        make="Ford",
        model="Transit",
        year=2022,
        value=Money(amount=Decimal("25000")),
        annual_mileage=mileage,
        gross_weight_kg=3500,
    )


def _make_driver() -> Driver:
    return Driver(
        full_name="Test Driver",
        licence_number="TEST123456",
        date_of_birth=date(1985, 6, 15),
        years_licensed=20,
    )


def _make_submission(
    address: Address,
    coverage: Coverage,
    *,
    vehicles: list[Vehicle],
) -> Submission:
    return Submission(
        reference="BRK-TEST-0001",
        insured_name="Test Logistics Ltd",
        insured_address=address,
        business_description="Test couriers",
        annual_revenue=Money(amount=Decimal("1000000")),
        vehicles=vehicles,
        drivers=[_make_driver()],
        requested_coverage=coverage,
    )


def _make_assessment(submission_id, *, band: RiskBand = RiskBand.LOW) -> RiskAssessment:
    return RiskAssessment(
        submission_id=submission_id,
        risk_band=band,
        risk_score=10.0,
        factors={},
        summary="Test summary",
        assessed_at=datetime.utcnow(),
    )


class TestBasePremium:
    def test_van_with_low_mileage(self, address, coverage):
        # Base rate for van is 1200, mileage factor = 1 + 30000/100000 = 1.3
        # Expected: 1200 * 1.3 = 1560
        submission = _make_submission(address, coverage, vehicles=[_make_van(mileage=30_000)])

        base = PricingAgent._calculate_base_premium(submission)

        assert base == Decimal("1560.00")

    def test_articulated_lorry_pricing(self, address, coverage):
        # Articulated rate = 3800, mileage factor for 50k = 1.5
        # Expected: 3800 * 1.5 = 5700
        artic = Vehicle(
            registration="HG12CDE",
            vehicle_type=VehicleType.ARTICULATED,
            make="Scania",
            model="R450",
            year=2022,
            value=Money(amount=Decimal("100000")),
            annual_mileage=50_000,
            gross_weight_kg=44_000,
        )
        submission = _make_submission(address, coverage, vehicles=[artic])

        base = PricingAgent._calculate_base_premium(submission)

        assert base == Decimal("5700.00")

    def test_multi_vehicle_fleet_sums(self, address, coverage):
        # 3 vans @ 30k miles = 1200 * 1.3 * 3 = 4680
        vehicles = [_make_van() for _ in range(3)]
        submission = _make_submission(address, coverage, vehicles=vehicles)

        base = PricingAgent._calculate_base_premium(submission)

        assert base == Decimal("4680.00")

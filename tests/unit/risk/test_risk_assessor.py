"""Unit tests for the deterministic risk assessor logic.

These tests exercise the calculation logic without invoking the LLM.
The factor calculation and score combination are pure functions, so
they're trivially testable.
"""

from datetime import date
from decimal import Decimal

import pytest
from services.risk.agents.risk_assessor import RiskAssessor
from shared.domain import (
    Address,
    Coverage,
    CoverageType,
    DateRange,
    Driver,
    Money,
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


def _make_vehicle(*, vehicle_type: VehicleType = VehicleType.VAN, mileage: int = 30_000) -> Vehicle:
    return Vehicle(
        registration="AB12CDE",
        vehicle_type=vehicle_type,
        make="Ford",
        model="Transit",
        year=2022,
        value=Money(amount=Decimal("25000")),
        annual_mileage=mileage,
        gross_weight_kg=3500,
    )


def _make_driver(
    *,
    age: int = 40,
    years_licensed: int = 20,
    points: int = 0,
    convictions: int = 0,
) -> Driver:
    today = date.today()
    dob = date(today.year - age, today.month, today.day)
    return Driver(
        full_name="Test Driver",
        licence_number="TEST123456",
        date_of_birth=dob,
        years_licensed=years_licensed,
        points=points,
        convictions_5y=convictions,
    )


def _make_submission(
    address: Address,
    coverage: Coverage,
    *,
    vehicles: list[Vehicle],
    drivers: list[Driver],
    claims_count_5y: int = 0,
    claims_value: Decimal = Decimal(0),
    operates_internationally: bool = False,
) -> Submission:
    return Submission(
        reference="BRK-TEST-0001",
        insured_name="Test Logistics Ltd",
        insured_address=address,
        business_description="Test couriers",
        annual_revenue=Money(amount=Decimal("1000000")),
        vehicles=vehicles,
        drivers=drivers,
        operates_internationally=operates_internationally,
        claims_count_5y=claims_count_5y,
        claims_value_5y=Money(amount=claims_value),
        requested_coverage=coverage,
    )


class TestRiskFactors:
    def test_low_risk_fleet_scores_low(self, address, coverage):
        assessor = RiskAssessor()
        submission = _make_submission(
            address,
            coverage,
            vehicles=[_make_vehicle() for _ in range(10)],
            drivers=[_make_driver() for _ in range(12)],
        )

        factors = assessor._calculate_factors(submission)
        score = assessor._calculate_score(factors)

        assert score < 25, f"expected low risk band but score was {score}"
        assert assessor._score_to_band(score) == RiskBand.LOW

    def test_high_claims_pushes_score_up(self, address, coverage):
        assessor = RiskAssessor()
        submission = _make_submission(
            address,
            coverage,
            vehicles=[_make_vehicle() for _ in range(5)],
            drivers=[_make_driver() for _ in range(6)],
            claims_count_5y=20,  # 0.8 claims/vehicle/year
            claims_value=Decimal("80000"),
        )

        factors = assessor._calculate_factors(submission)
        score = assessor._calculate_score(factors)

        assert factors.claims_history_factor == 80.0
        assert score >= 25

    def test_hazardous_vehicles_increase_risk(self, address, coverage):
        assessor = RiskAssessor()
        submission = _make_submission(
            address,
            coverage,
            vehicles=[_make_vehicle(vehicle_type=VehicleType.HAZARDOUS) for _ in range(5)],
            drivers=[_make_driver() for _ in range(6)],
        )

        factors = assessor._calculate_factors(submission)
        assert factors.high_risk_vehicle_factor == 50.0

    def test_young_drivers_increase_risk(self, address, coverage):
        assessor = RiskAssessor()
        submission = _make_submission(
            address,
            coverage,
            vehicles=[_make_vehicle() for _ in range(5)],
            drivers=[_make_driver(age=22, years_licensed=3) for _ in range(6)],
        )

        factors = assessor._calculate_factors(submission)

        assert factors.young_driver_factor == 60.0
        assert factors.driver_experience_factor == 60.0

    def test_inexperienced_drivers_increase_risk(self, address, coverage):
        assessor = RiskAssessor()
        submission = _make_submission(
            address,
            coverage,
            vehicles=[_make_vehicle() for _ in range(5)],
            drivers=[_make_driver(years_licensed=2) for _ in range(6)],
        )

        factors = assessor._calculate_factors(submission)
        assert factors.driver_experience_factor == 60.0

    def test_high_points_drivers_increase_risk(self, address, coverage):
        assessor = RiskAssessor()
        submission = _make_submission(
            address,
            coverage,
            vehicles=[_make_vehicle() for _ in range(5)],
            drivers=[_make_driver(points=9), *[_make_driver() for _ in range(5)]],
        )

        factors = assessor._calculate_factors(submission)
        assert factors.driver_points_factor == 70.0

    def test_international_operations_increase_risk(self, address, coverage):
        assessor = RiskAssessor()
        submission = _make_submission(
            address,
            coverage,
            vehicles=[_make_vehicle() for _ in range(5)],
            drivers=[_make_driver() for _ in range(6)],
            operates_internationally=True,
        )

        factors = assessor._calculate_factors(submission)
        assert factors.international_operations_factor == 30.0


class TestScoreBands:
    @pytest.mark.parametrize(
        ("score", "expected_band"),
        [
            (0, RiskBand.LOW),
            (24.9, RiskBand.LOW),
            (25, RiskBand.MEDIUM),
            (49.9, RiskBand.MEDIUM),
            (50, RiskBand.HIGH),
            (69.9, RiskBand.HIGH),
            (70, RiskBand.EXTREME),
            (100, RiskBand.EXTREME),
        ],
    )
    def test_score_to_band_thresholds(self, score: float, expected_band: RiskBand):
        assert RiskAssessor._score_to_band(score) == expected_band

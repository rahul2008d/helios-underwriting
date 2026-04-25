"""Unit tests for domain entities."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from shared.domain import (
    Address,
    Coverage,
    CoverageType,
    Currency,
    DateRange,
    Driver,
    Money,
    Submission,
    SubmissionStatus,
    Vehicle,
    VehicleType,
)


@pytest.fixture
def address() -> Address:
    return Address(line_1="86-90 Paul Street", city="London", postcode="EC2A 4NE")


@pytest.fixture
def vehicle() -> Vehicle:
    return Vehicle(
        registration="AB12 CDE",
        vehicle_type=VehicleType.VAN,
        make="Ford",
        model="Transit",
        year=2022,
        value=Money(amount=Decimal("25000"), currency=Currency.GBP),
        annual_mileage=30_000,
        gross_weight_kg=3500,
    )


@pytest.fixture
def driver() -> Driver:
    return Driver(
        full_name="Jane Smith",
        licence_number="SMITH901021JS9AB",
        date_of_birth=date(1990, 10, 21),
        years_licensed=15,
    )


@pytest.fixture
def coverage() -> Coverage:
    return Coverage(
        coverage_type=CoverageType.COMPREHENSIVE,
        period=DateRange(start=date(2026, 5, 1), end=date(2027, 4, 30)),
        excess=Money(amount=Decimal("500")),
    )


class TestVehicle:
    def test_normalises_registration(self):
        vehicle = Vehicle(
            registration=" ab12 cde ",
            vehicle_type=VehicleType.VAN,
            make="Ford",
            model="Transit",
            year=2022,
            value=Money(amount=Decimal("25000")),
            annual_mileage=30_000,
        )

        assert vehicle.registration == "AB12CDE"

    def test_rejects_year_below_1990(self):
        with pytest.raises(ValidationError):
            Vehicle(
                registration="AB12CDE",
                vehicle_type=VehicleType.VAN,
                make="Ford",
                model="Transit",
                year=1989,
                value=Money(amount=Decimal("1000")),
                annual_mileage=10_000,
            )


class TestDriver:
    def test_calculates_age(self, driver: Driver):
        assert driver.age >= 35  # born 1990

    def test_rejects_invalid_points(self):
        with pytest.raises(ValidationError):
            Driver(
                full_name="Test",
                licence_number="TEST123456",
                date_of_birth=date(1990, 1, 1),
                years_licensed=10,
                points=15,
            )


class TestSubmission:
    def test_creates_with_defaults(
        self,
        address: Address,
        vehicle: Vehicle,
        driver: Driver,
        coverage: Coverage,
    ):
        submission = Submission(
            reference="BRK-2026-0001",
            insured_name="Acme Logistics Ltd",
            insured_address=address,
            business_description="Regional logistics company",
            annual_revenue=Money(amount=Decimal("2500000")),
            vehicles=[vehicle],
            drivers=[driver],
            requested_coverage=coverage,
        )

        assert submission.status == SubmissionStatus.RECEIVED
        assert submission.fleet_size == 1
        assert submission.total_fleet_value == Decimal("25000")
        assert submission.countries_of_operation == ["United Kingdom"]

    def test_rejects_empty_fleet(self, address: Address, driver: Driver, coverage: Coverage):
        with pytest.raises(ValidationError):
            Submission(
                reference="BRK-2026-0001",
                insured_name="Acme Logistics Ltd",
                insured_address=address,
                business_description="Regional logistics company",
                annual_revenue=Money(amount=Decimal("2500000")),
                vehicles=[],
                drivers=[driver],
                requested_coverage=coverage,
            )

    def test_calculates_total_fleet_value(
        self,
        address: Address,
        driver: Driver,
        coverage: Coverage,
    ):
        v1 = Vehicle(
            registration="AB12CDE",
            vehicle_type=VehicleType.VAN,
            make="Ford",
            model="Transit",
            year=2022,
            value=Money(amount=Decimal("25000")),
            annual_mileage=30_000,
        )
        v2 = Vehicle(
            registration="EF34GHI",
            vehicle_type=VehicleType.LORRY,
            make="DAF",
            model="LF",
            year=2021,
            value=Money(amount=Decimal("75000")),
            annual_mileage=50_000,
        )

        submission = Submission(
            reference="BRK-2026-0001",
            insured_name="Acme Logistics Ltd",
            insured_address=address,
            business_description="Regional logistics company",
            annual_revenue=Money(amount=Decimal("2500000")),
            vehicles=[v1, v2],
            drivers=[driver],
            requested_coverage=coverage,
        )

        assert submission.fleet_size == 2
        assert submission.total_fleet_value == Decimal("100000")

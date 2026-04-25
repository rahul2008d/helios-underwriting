"""Seed the database with realistic fleet insurance submissions.

Creates 10 submissions across a range of risk profiles - small fleets,
large fleets, international operations, mixed vehicle types, and varying
claims histories.

Run with: uv run python -m scripts.seed_submissions
"""

import asyncio
from datetime import date, datetime
from decimal import Decimal

from services.submission.repositories import SubmissionRepository
from shared.database import get_session_factory
from shared.domain import (
    Address,
    Coverage,
    CoverageType,
    DateRange,
    Driver,
    Money,
    Submission,
    SubmissionStatus,
    Vehicle,
    VehicleType,
)
from shared.logging import configure_logging, logger

LONDON_ADDRESS = Address(line_1="86-90 Paul Street", city="London", postcode="EC2A 4NE")
MANCHESTER_ADDRESS = Address(line_1="Whitworth Street", city="Manchester", postcode="M1 3WW")
BIRMINGHAM_ADDRESS = Address(line_1="Hagley Road", city="Birmingham", postcode="B16 8QG")


def _coverage(start: date, days: int = 365) -> Coverage:
    """Build a comprehensive coverage starting on the given date."""
    end = date.fromordinal(start.toordinal() + days - 1)
    return Coverage(
        coverage_type=CoverageType.COMPREHENSIVE,
        period=DateRange(start=start, end=end),
        excess=Money(amount=Decimal("500")),
    )


def build_seed_submissions() -> list[Submission]:
    """Construct the full set of seed submissions."""
    start_date = date(2026, 5, 1)

    submissions: list[Submission] = []

    # 1. Small clean fleet
    submissions.append(
        Submission(
            reference="BRK-2026-0001",
            received_at=datetime(2026, 4, 1, 9, 30),
            status=SubmissionStatus.RECEIVED,
            insured_name="Riverside Couriers Ltd",
            insured_address=LONDON_ADDRESS,
            business_description="Same-day courier service across Greater London.",
            annual_revenue=Money(amount=Decimal("850000")),
            vehicles=[
                Vehicle(
                    registration=f"AB{i:02d}CDE",
                    vehicle_type=VehicleType.VAN,
                    make="Ford",
                    model="Transit Custom",
                    year=2023,
                    value=Money(amount=Decimal("28000")),
                    annual_mileage=35_000,
                    gross_weight_kg=3500,
                )
                for i in range(1, 6)
            ],
            drivers=[
                Driver(
                    full_name=f"Driver {n}",
                    licence_number=f"COURIER{n:04d}AB",
                    date_of_birth=date(1985, 6, 15),
                    years_licensed=18,
                )
                for n in range(1, 7)
            ],
            requested_coverage=_coverage(start_date),
        )
    )

    # 2. Mid-size mixed fleet
    submissions.append(
        Submission(
            reference="BRK-2026-0002",
            received_at=datetime(2026, 4, 2, 11, 15),
            status=SubmissionStatus.RECEIVED,
            insured_name="Northern Distribution Ltd",
            insured_address=MANCHESTER_ADDRESS,
            business_description="Regional distribution of consumer goods, North West UK.",
            annual_revenue=Money(amount=Decimal("4500000")),
            vehicles=(
                [
                    Vehicle(
                        registration=f"NX{i:02d}ABC",
                        vehicle_type=VehicleType.VAN,
                        make="Mercedes-Benz",
                        model="Sprinter",
                        year=2022,
                        value=Money(amount=Decimal("32000")),
                        annual_mileage=45_000,
                        gross_weight_kg=3500,
                    )
                    for i in range(1, 11)
                ]
                + [
                    Vehicle(
                        registration=f"NX{20 + i:02d}DEF",
                        vehicle_type=VehicleType.LORRY,
                        make="DAF",
                        model="LF",
                        year=2021,
                        value=Money(amount=Decimal("75000")),
                        annual_mileage=60_000,
                        gross_weight_kg=12_000,
                    )
                    for i in range(1, 6)
                ]
            ),
            drivers=[
                Driver(
                    full_name=f"Operator {n}",
                    licence_number=f"NORTH{n:04d}OP",
                    date_of_birth=date(1980, 3, 12),
                    years_licensed=22,
                )
                for n in range(1, 18)
            ],
            claims_count_5y=2,
            claims_value_5y=Money(amount=Decimal("8500")),
            requested_coverage=_coverage(start_date),
        )
    )

    # 3. International haulage with HGVs
    submissions.append(
        Submission(
            reference="BRK-2026-0003",
            received_at=datetime(2026, 4, 3, 14, 0),
            status=SubmissionStatus.RECEIVED,
            insured_name="Channel Freight Services Ltd",
            insured_address=BIRMINGHAM_ADDRESS,
            business_description="Cross-channel HGV haulage to France, Belgium, Netherlands.",
            annual_revenue=Money(amount=Decimal("12000000")),
            vehicles=[
                Vehicle(
                    registration=f"CF{i:02d}HGV",
                    vehicle_type=VehicleType.ARTICULATED,
                    make="Scania",
                    model="R450",
                    year=2022,
                    value=Money(amount=Decimal("110000")),
                    annual_mileage=120_000,
                    gross_weight_kg=44_000,
                )
                for i in range(1, 21)
            ],
            drivers=[
                Driver(
                    full_name=f"HGV Driver {n}",
                    licence_number=f"HGVDRV{n:04d}",
                    date_of_birth=date(1975, 8, 5),
                    years_licensed=28,
                )
                for n in range(1, 26)
            ],
            operates_internationally=True,
            countries_of_operation=["United Kingdom", "France", "Belgium", "Netherlands"],
            claims_count_5y=4,
            claims_value_5y=Money(amount=Decimal("32000")),
            requested_coverage=_coverage(start_date),
        )
    )

    # 4. Refrigerated transport
    submissions.append(
        Submission(
            reference="BRK-2026-0004",
            received_at=datetime(2026, 4, 4, 10, 45),
            status=SubmissionStatus.RECEIVED,
            insured_name="Cold Chain Logistics Ltd",
            insured_address=MANCHESTER_ADDRESS,
            business_description="Temperature-controlled transport for food and pharma.",
            annual_revenue=Money(amount=Decimal("6800000")),
            vehicles=[
                Vehicle(
                    registration=f"CC{i:02d}REF",
                    vehicle_type=VehicleType.REFRIGERATED,
                    make="Volvo",
                    model="FH",
                    year=2023,
                    value=Money(amount=Decimal("125000")),
                    annual_mileage=80_000,
                    gross_weight_kg=26_000,
                )
                for i in range(1, 13)
            ],
            drivers=[
                Driver(
                    full_name=f"Cold Driver {n}",
                    licence_number=f"COLD{n:04d}DR",
                    date_of_birth=date(1982, 11, 22),
                    years_licensed=20,
                )
                for n in range(1, 16)
            ],
            claims_count_5y=1,
            claims_value_5y=Money(amount=Decimal("4500")),
            requested_coverage=_coverage(start_date),
        )
    )

    # 5. High-claims fleet (referral candidate)
    submissions.append(
        Submission(
            reference="BRK-2026-0005",
            received_at=datetime(2026, 4, 5, 16, 20),
            status=SubmissionStatus.RECEIVED,
            insured_name="QuickServe Express Ltd",
            insured_address=LONDON_ADDRESS,
            business_description="High-volume parcel delivery, urban and suburban routes.",
            annual_revenue=Money(amount=Decimal("3200000")),
            vehicles=[
                Vehicle(
                    registration=f"QS{i:02d}EXP",
                    vehicle_type=VehicleType.VAN,
                    make="Vauxhall",
                    model="Vivaro",
                    year=2020,
                    value=Money(amount=Decimal("18000")),
                    annual_mileage=55_000,
                    gross_weight_kg=3100,
                )
                for i in range(1, 16)
            ],
            drivers=[
                Driver(
                    full_name=f"Express Driver {n}",
                    licence_number=f"EXPDRV{n:04d}",
                    date_of_birth=date(1995, 4, 18),
                    years_licensed=8,
                    points=3,
                )
                for n in range(1, 21)
            ],
            claims_count_5y=12,
            claims_value_5y=Money(amount=Decimal("85000")),
            requested_coverage=_coverage(start_date),
        )
    )

    # 6. Specialist plant operator
    submissions.append(
        Submission(
            reference="BRK-2026-0006",
            received_at=datetime(2026, 4, 6, 8, 30),
            status=SubmissionStatus.RECEIVED,
            insured_name="Iron Bridge Construction Ltd",
            insured_address=BIRMINGHAM_ADDRESS,
            business_description="Construction plant transport and recovery services.",
            annual_revenue=Money(amount=Decimal("5500000")),
            vehicles=[
                Vehicle(
                    registration=f"IB{i:02d}PLT",
                    vehicle_type=VehicleType.SPECIALIST,
                    make="MAN",
                    model="TGS",
                    year=2021,
                    value=Money(amount=Decimal("95000")),
                    annual_mileage=40_000,
                    gross_weight_kg=32_000,
                )
                for i in range(1, 9)
            ],
            drivers=[
                Driver(
                    full_name=f"Plant Operator {n}",
                    licence_number=f"PLANT{n:04d}OP",
                    date_of_birth=date(1978, 9, 30),
                    years_licensed=25,
                )
                for n in range(1, 12)
            ],
            claims_count_5y=2,
            claims_value_5y=Money(amount=Decimal("12000")),
            requested_coverage=_coverage(start_date),
        )
    )

    # 7. Hazardous goods carrier
    submissions.append(
        Submission(
            reference="BRK-2026-0007",
            received_at=datetime(2026, 4, 7, 13, 10),
            status=SubmissionStatus.RECEIVED,
            insured_name="ChemTrans UK Ltd",
            insured_address=MANCHESTER_ADDRESS,
            business_description="ADR-certified chemical and hazardous goods transport.",
            annual_revenue=Money(amount=Decimal("9200000")),
            vehicles=[
                Vehicle(
                    registration=f"CT{i:02d}HAZ",
                    vehicle_type=VehicleType.HAZARDOUS,
                    make="Volvo",
                    model="FM",
                    year=2022,
                    value=Money(amount=Decimal("140000")),
                    annual_mileage=70_000,
                    gross_weight_kg=44_000,
                )
                for i in range(1, 11)
            ],
            drivers=[
                Driver(
                    full_name=f"ADR Driver {n}",
                    licence_number=f"ADR{n:04d}DRV",
                    date_of_birth=date(1976, 1, 14),
                    years_licensed=30,
                )
                for n in range(1, 14)
            ],
            claims_count_5y=0,
            requested_coverage=_coverage(start_date),
        )
    )

    # 8. Tiny owner-operator
    submissions.append(
        Submission(
            reference="BRK-2026-0008",
            received_at=datetime(2026, 4, 8, 15, 45),
            status=SubmissionStatus.RECEIVED,
            insured_name="Smith & Sons Removals",
            insured_address=BIRMINGHAM_ADDRESS,
            business_description="Family-run domestic and small commercial removals.",
            annual_revenue=Money(amount=Decimal("180000")),
            vehicles=[
                Vehicle(
                    registration="SS01REM",
                    vehicle_type=VehicleType.LORRY,
                    make="Iveco",
                    model="Daily",
                    year=2020,
                    value=Money(amount=Decimal("35000")),
                    annual_mileage=25_000,
                    gross_weight_kg=7500,
                ),
                Vehicle(
                    registration="SS02REM",
                    vehicle_type=VehicleType.VAN,
                    make="Renault",
                    model="Master",
                    year=2021,
                    value=Money(amount=Decimal("22000")),
                    annual_mileage=20_000,
                    gross_weight_kg=3500,
                ),
            ],
            drivers=[
                Driver(
                    full_name="Robert Smith",
                    licence_number="SMITH7501RJ",
                    date_of_birth=date(1965, 5, 1),
                    years_licensed=40,
                ),
                Driver(
                    full_name="James Smith",
                    licence_number="SMITH9504JS",
                    date_of_birth=date(1992, 4, 20),
                    years_licensed=10,
                ),
            ],
            claims_count_5y=1,
            claims_value_5y=Money(amount=Decimal("1800")),
            requested_coverage=_coverage(start_date),
        )
    )

    # 9. Large urban delivery (Amazon-style)
    submissions.append(
        Submission(
            reference="BRK-2026-0009",
            received_at=datetime(2026, 4, 9, 10, 0),
            status=SubmissionStatus.RECEIVED,
            insured_name="MetroDelivery Solutions Ltd",
            insured_address=LONDON_ADDRESS,
            business_description="Last-mile delivery contractor for major e-commerce platforms.",
            annual_revenue=Money(amount=Decimal("18500000")),
            vehicles=[
                Vehicle(
                    registration=f"MD{i:03d}URB",
                    vehicle_type=VehicleType.VAN,
                    make="Mercedes-Benz",
                    model="eVito",
                    year=2024,
                    value=Money(amount=Decimal("42000")),
                    annual_mileage=30_000,
                    gross_weight_kg=3500,
                )
                for i in range(1, 51)
            ],
            drivers=[
                Driver(
                    full_name=f"Metro Driver {n}",
                    licence_number=f"METRO{n:04d}DR",
                    date_of_birth=date(1990, 7, 7),
                    years_licensed=12,
                )
                for n in range(1, 71)
            ],
            claims_count_5y=8,
            claims_value_5y=Money(amount=Decimal("42000")),
            requested_coverage=_coverage(start_date),
        )
    )

    # 10. Young driver heavy-points (decline candidate)
    submissions.append(
        Submission(
            reference="BRK-2026-0010",
            received_at=datetime(2026, 4, 10, 11, 30),
            status=SubmissionStatus.RECEIVED,
            insured_name="FastTrack Logistics Ltd",
            insured_address=LONDON_ADDRESS,
            business_description="Newly formed urban logistics startup, two years trading.",
            annual_revenue=Money(amount=Decimal("420000")),
            vehicles=[
                Vehicle(
                    registration=f"FT{i:02d}NEW",
                    vehicle_type=VehicleType.VAN,
                    make="Peugeot",
                    model="Boxer",
                    year=2019,
                    value=Money(amount=Decimal("14000")),
                    annual_mileage=50_000,
                    gross_weight_kg=3500,
                )
                for i in range(1, 7)
            ],
            drivers=[
                Driver(
                    full_name=f"New Driver {n}",
                    licence_number=f"NEW{n:04d}DRV",
                    date_of_birth=date(2002, 1, 1),
                    years_licensed=3,
                    points=6,
                    convictions_5y=1,
                )
                for n in range(1, 9)
            ],
            claims_count_5y=5,
            claims_value_5y=Money(amount=Decimal("28000")),
            requested_coverage=_coverage(start_date),
        )
    )

    return submissions


async def seed() -> None:
    """Run the seeding process."""
    configure_logging()
    logger.info("starting submission seeding")

    submissions = build_seed_submissions()
    factory = get_session_factory()

    async with factory() as session:
        repository = SubmissionRepository(session)
        for submission in submissions:
            existing = await repository.get_by_reference(submission.reference)
            if existing is not None:
                logger.info(
                    "submission already seeded, skipping",
                    reference=submission.reference,
                )
                continue
            await repository.add(submission)
            logger.info(
                "seeded submission",
                reference=submission.reference,
                insured=submission.insured_name,
                fleet_size=submission.fleet_size,
            )
        await session.commit()

    logger.info("seeding complete", count=len(submissions))


if __name__ == "__main__":
    asyncio.run(seed())

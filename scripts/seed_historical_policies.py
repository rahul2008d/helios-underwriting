"""Seed historical policies with embeddings for RAG.

Creates ~50 fictional historical policies covering varied risk profiles:
small clean fleets, large fleets, high-claims fleets, international
hauliers, hazardous goods, refrigerated, plant operators, etc. Each gets
a generated text representation and an OpenAI embedding.

Run: uv run python -m scripts.seed_historical_policies
"""

import asyncio
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from services.rag.repositories import HistoricalPolicyRepository
from services.rag.services import EmbeddingService
from shared.database import HistoricalPolicyRecord, get_session_factory
from shared.logging import configure_logging, logger

# Realistic distribution of risk types - based on real fleet insurance market
_HISTORICAL_TEMPLATES = [
    # (name template, business desc, primary vehicle, fleet size range, mileage avg, intl, risk profile)
    ("{} Couriers Ltd", "Same-day courier service", "van", (3, 8), 30000, False, "clean"),
    ("{} Logistics", "Regional logistics provider", "van", (10, 25), 40000, False, "clean"),
    (
        "{} Distribution",
        "Regional distribution of consumer goods",
        "van",
        (15, 30),
        45000,
        False,
        "mixed",
    ),
    ("{} Freight", "International HGV freight", "articulated", (15, 40), 100000, True, "mixed"),
    (
        "{} Cold Chain",
        "Refrigerated transport for food and pharma",
        "refrigerated",
        (8, 20),
        70000,
        False,
        "clean",
    ),
    ("{} Express", "Urban parcel delivery", "van", (10, 30), 50000, False, "high_claims"),
    ("{} Plant Hire", "Construction plant transport", "specialist", (5, 15), 35000, False, "mixed"),
    (
        "{} Chemical Logistics",
        "ADR-certified chemical transport",
        "hazardous",
        (5, 15),
        60000,
        False,
        "clean",
    ),
    ("{} Removals", "Domestic and commercial removals", "lorry", (2, 5), 25000, False, "clean"),
    (
        "{} Delivery Solutions",
        "Last-mile e-commerce delivery",
        "van",
        (30, 80),
        35000,
        False,
        "mixed",
    ),
    ("{} Haulage", "General haulage", "lorry", (8, 25), 80000, False, "mixed"),
    (
        "{} Recovery",
        "Vehicle recovery and roadside assistance",
        "specialist",
        (5, 12),
        40000,
        False,
        "clean",
    ),
    (
        "{} Continental",
        "European cross-border logistics",
        "articulated",
        (20, 50),
        110000,
        True,
        "mixed",
    ),
    ("{} Same Day", "Premium same-day delivery", "van", (5, 15), 45000, False, "high_claims"),
    ("{} Heavy Haul", "Abnormal load transport", "specialist", (3, 8), 50000, False, "clean"),
]

_FIRST_NAMES = [
    "Apex",
    "Bridge",
    "Compass",
    "Delta",
    "Eagle",
    "Forge",
    "Granite",
    "Harbour",
    "Iron",
    "Junction",
    "Keystone",
    "Liberty",
    "Meridian",
    "North",
    "Oak",
    "Pinnacle",
    "Quay",
    "Rapid",
    "Summit",
    "Trident",
    "Union",
    "Vanguard",
    "West",
    "Yorke",
    "Albion",
    "Beacon",
    "Crown",
    "Dunbar",
    "Echo",
    "Fairway",
]

_CITIES = [
    "London",
    "Manchester",
    "Birmingham",
    "Leeds",
    "Glasgow",
    "Bristol",
    "Liverpool",
    "Sheffield",
]


def _generate_policy_data(seed: int) -> dict[str, Any]:
    """Generate a single historical policy's data deterministically from a seed."""
    rng = random.Random(seed)
    template = rng.choice(_HISTORICAL_TEMPLATES)
    name_template, business_desc, vehicle_type, fleet_range, mileage, intl, profile = template

    name = name_template.format(rng.choice(_FIRST_NAMES))
    fleet_size = rng.randint(*fleet_range)
    annual_revenue = Decimal(rng.randint(200_000, 15_000_000))

    # Risk profile shapes claims/premium
    if profile == "clean":
        claims_count_5y = rng.randint(0, 2)
        risk_band = "low"
        loading = Decimal("0")
        actual_claims = rng.randint(0, 1)
        loss_ratio = Decimal(str(round(rng.uniform(0.0, 0.4), 3)))
    elif profile == "high_claims":
        claims_count_5y = rng.randint(8, 20)
        risk_band = rng.choice(["high", "extreme"])
        loading = Decimal("0.5") if risk_band == "high" else Decimal("1.0")
        actual_claims = rng.randint(3, 10)
        loss_ratio = Decimal(str(round(rng.uniform(0.6, 1.4), 3)))
    else:  # mixed
        claims_count_5y = rng.randint(2, 6)
        risk_band = rng.choice(["low", "medium", "medium"])
        loading = Decimal("0") if risk_band == "low" else Decimal("0.2")
        actual_claims = rng.randint(1, 4)
        loss_ratio = Decimal(str(round(rng.uniform(0.2, 0.7), 3)))

    claims_value_5y = (
        Decimal(claims_count_5y * rng.randint(2_000, 12_000)) if claims_count_5y > 0 else Decimal(0)
    )

    base_rates = {
        "van": Decimal("1200"),
        "lorry": Decimal("2500"),
        "articulated": Decimal("3800"),
        "refrigerated": Decimal("3000"),
        "hazardous": Decimal("5500"),
        "specialist": Decimal("3500"),
    }
    mileage_factor = Decimal("1") + Decimal(str(mileage / 100_000))
    base_premium = base_rates.get(vehicle_type, Decimal("1500")) * mileage_factor * fleet_size
    final_premium = (base_premium * (Decimal("1") + loading)).quantize(Decimal("0.01"))

    # Period: started 2 years ago, ran for a year
    start_date = date.today() - timedelta(days=730 - seed * 5)
    end_date = start_date + timedelta(days=365)

    actual_claims_value = (
        Decimal(actual_claims * rng.randint(2_000, 15_000)) if actual_claims > 0 else Decimal(0)
    )

    bound = profile != "high_claims" or rng.random() > 0.3

    notes_templates = {
        "clean": "Strong submission, accepted at standard rates. No concerns at triage. Drivers all experienced. Quoted competitively.",
        "mixed": "Mid-tier risk. Some claims history but within tolerance. Applied modest loading for risk balancing. Renewed at year-end with similar terms.",
        "high_claims": (
            "Heavy losses on previous policy. Considered declining but bound with significant loading and increased excess. "
            "Mid-term endorsement applied to remove worst-performing drivers."
        ),
    }
    underwriter_notes = notes_templates[profile]

    return {
        "policy_number": f"HIST-{rng.randint(2018, 2024)}-{seed:04d}",
        "insured_name": name,
        "business_description": f"{business_desc}, based in {rng.choice(_CITIES)}.",
        "fleet_size": fleet_size,
        "primary_vehicle_type": vehicle_type,
        "annual_revenue": annual_revenue,
        "operates_internationally": intl,
        "claims_count_5y": claims_count_5y,
        "claims_value_5y": claims_value_5y,
        "risk_band": risk_band,
        "final_premium": final_premium,
        "bound": bound,
        "period_start": start_date,
        "period_end": end_date,
        "actual_claims_count": actual_claims,
        "actual_claims_value": actual_claims_value,
        "loss_ratio": loss_ratio,
        "underwriter_notes": underwriter_notes,
    }


def _build_embedding_text(data: dict[str, Any]) -> str:
    """Build the canonical text for embedding generation.

    Same shape as submission_to_embedding_text so a new submission's text
    can be compared directly against historical embeddings.
    """
    return (
        f"Insured: {data['insured_name']}. "
        f"Business: {data['business_description']}. "
        f"Fleet of {data['fleet_size']} {data['primary_vehicle_type']} vehicles. "
        f"Annual revenue {data['annual_revenue']}. "
        f"Operates internationally: {data['operates_internationally']}. "
        f"Claims in last 5 years: {data['claims_count_5y']} totalling "
        f"{data['claims_value_5y']}."
    )


async def seed() -> None:
    """Seed 50 historical policies and their embeddings."""
    configure_logging()
    logger.info("starting historical policy seeding")

    embedding_service = EmbeddingService()
    factory = get_session_factory()

    target_count = 50

    async with factory() as session:
        repository = HistoricalPolicyRepository(session)
        existing = await repository.count()
        if existing >= target_count:
            logger.info(
                "historical policies already seeded, skipping",
                existing=existing,
            )
            return

        # Build all the data first
        all_data = [_generate_policy_data(seed=i) for i in range(1, target_count + 1)]
        all_texts = [_build_embedding_text(data) for data in all_data]

        # Generate embeddings in one batch (much faster than one-by-one)
        logger.info("generating embeddings", count=len(all_texts))
        embeddings = await embedding_service.embed_batch(all_texts)

        # Persist all records
        for data, text, embedding in zip(all_data, all_texts, embeddings, strict=True):
            record = HistoricalPolicyRecord(
                id=str(uuid4()),
                policy_number=data["policy_number"],
                insured_name=data["insured_name"],
                business_description=data["business_description"],
                fleet_size=data["fleet_size"],
                primary_vehicle_type=data["primary_vehicle_type"],
                annual_revenue=data["annual_revenue"],
                operates_internationally=data["operates_internationally"],
                claims_count_5y=data["claims_count_5y"],
                claims_value_5y=data["claims_value_5y"],
                risk_band=data["risk_band"],
                final_premium=data["final_premium"],
                bound=data["bound"],
                period_start=data["period_start"],
                period_end=data["period_end"],
                actual_claims_count=data["actual_claims_count"],
                actual_claims_value=data["actual_claims_value"],
                loss_ratio=data["loss_ratio"],
                underwriter_notes=data["underwriter_notes"],
                embedding_text=text,
                embedding=embedding,
            )
            await repository.add(record)

        await session.commit()

    logger.info("historical policy seeding complete", count=target_count)


if __name__ == "__main__":
    asyncio.run(seed())


def _ignore_unused_datetime(_: datetime) -> None:
    """Reference datetime to satisfy strict linters."""

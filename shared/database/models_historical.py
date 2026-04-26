"""Database model for historical policies used in RAG.

Historical policies are anonymised records of past underwriting decisions.
Each has an embedding vector generated from a text representation of the
risk, used for similarity search when a new submission arrives.

We store embeddings as JSON arrays of floats in MySQL. For production scale
you'd use pgvector (PostgreSQL) or a dedicated vector DB like Qdrant. JSON
is fine for the dataset sizes we use here.
"""

from datetime import date

from sqlalchemy import JSON, Date, Numeric, String, Text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from shared.database.base import Base, TimestampMixin


class HistoricalPolicyRecord(Base, TimestampMixin):
    """Persisted record of a historical policy with embedding."""

    __tablename__ = "historical_policies"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, nullable=False)
    policy_number: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)

    # Risk characteristics
    insured_name: Mapped[str] = mapped_column(String(200), nullable=False)
    business_description: Mapped[str] = mapped_column(Text, nullable=False)
    fleet_size: Mapped[int] = mapped_column(nullable=False)
    primary_vehicle_type: Mapped[str] = mapped_column(String(40), nullable=False)
    annual_revenue: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    operates_internationally: Mapped[bool] = mapped_column(default=False, nullable=False)
    claims_count_5y: Mapped[int] = mapped_column(default=0, nullable=False)
    claims_value_5y: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)

    # Underwriting outcome
    risk_band: Mapped[str] = mapped_column(String(10), nullable=False)
    final_premium: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    bound: Mapped[bool] = mapped_column(default=True, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Loss performance during the policy period (i.e. how the risk actually performed)
    actual_claims_count: Mapped[int] = mapped_column(default=0, nullable=False)
    actual_claims_value: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    loss_ratio: Mapped[float] = mapped_column(Numeric(6, 3), default=0, nullable=False)

    # Underwriter notes - what they considered, what worked, what didn't
    underwriter_notes: Mapped[str] = mapped_column(Text, nullable=False)

    # The text used to generate the embedding (kept for debugging/regeneration)
    embedding_text: Mapped[str] = mapped_column(Text, nullable=False)

    # The embedding vector - stored as JSON array of floats
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)

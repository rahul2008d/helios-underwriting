"""SQLAlchemy ORM models for the persistence layer.

The models use JSON columns for nested structures (vehicles, drivers) for
simplicity at this stage. In a real production system you'd normalise these
into separate tables. For our purposes the JSON approach lets us iterate
quickly while keeping the domain model rich.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database.base import Base, TimestampMixin
from shared.domain.enums import (
    CoverageType,
    Currency,
    PolicyStatus,
    RiskBand,
    SubmissionStatus,
    TriageDecision,
)


def _uuid_column(*, primary_key: bool = False, foreign_key: str | None = None) -> Mapped[UUID]:
    """Return a CHAR(36) column for storing UUIDs in MySQL."""
    if foreign_key:
        return mapped_column(
            CHAR(36),
            ForeignKey(foreign_key),
            primary_key=primary_key,
            nullable=False,
        )
    return mapped_column(CHAR(36), primary_key=primary_key, nullable=not primary_key)


class SubmissionRecord(Base, TimestampMixin):
    """Persisted record of a submission and its full risk details."""

    __tablename__ = "submissions"

    id: Mapped[UUID] = _uuid_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(String(20), nullable=False, index=True)

    # Risk details (denormalised for now)
    insured_name: Mapped[str] = mapped_column(String(200), nullable=False)
    insured_address: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    business_description: Mapped[str] = mapped_column(Text, nullable=False)
    annual_revenue_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    annual_revenue_currency: Mapped[Currency] = mapped_column(String(3), nullable=False)

    # Fleet (JSON arrays of Vehicle and Driver)
    vehicles: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    drivers: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    operates_internationally: Mapped[bool] = mapped_column(default=False, nullable=False)
    countries_of_operation: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    # Loss history
    claims_count_5y: Mapped[int] = mapped_column(default=0, nullable=False)
    claims_value_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    claims_value_currency: Mapped[Currency] = mapped_column(String(3), default=Currency.GBP)

    # Requested coverage
    coverage_type: Mapped[CoverageType] = mapped_column(String(30), nullable=False)
    coverage_start: Mapped[date] = mapped_column(Date, nullable=False)
    coverage_end: Mapped[date] = mapped_column(Date, nullable=False)
    coverage_excess_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    coverage_excess_currency: Mapped[Currency] = mapped_column(String(3), nullable=False)

    # Relationships
    triage_results: Mapped[list["TriageResultRecord"]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
    )
    risk_assessments: Mapped[list["RiskAssessmentRecord"]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
    )
    quotes: Mapped[list["QuoteRecord"]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
    )


class TriageResultRecord(Base, TimestampMixin):
    """Persisted output from the triage agent for a submission."""

    __tablename__ = "triage_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    submission_id: Mapped[UUID] = _uuid_column(foreign_key="submissions.id")

    decision: Mapped[TriageDecision] = mapped_column(String(20), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    appetite_matches: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    appetite_concerns: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    triaged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    submission: Mapped[SubmissionRecord] = relationship(back_populates="triage_results")


class RiskAssessmentRecord(Base, TimestampMixin):
    """Persisted risk assessment output."""

    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    submission_id: Mapped[UUID] = _uuid_column(foreign_key="submissions.id")

    risk_band: Mapped[RiskBand] = mapped_column(String(10), nullable=False, index=True)
    risk_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    factors: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    submission: Mapped[SubmissionRecord] = relationship(back_populates="risk_assessments")


class QuoteRecord(Base, TimestampMixin):
    """Persisted quote generated for a submission."""

    __tablename__ = "quotes"

    id: Mapped[UUID] = _uuid_column(primary_key=True)
    submission_id: Mapped[UUID] = _uuid_column(foreign_key="submissions.id")
    quote_reference: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    premium_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    premium_currency: Mapped[Currency] = mapped_column(String(3), nullable=False)
    excess_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    excess_currency: Mapped[Currency] = mapped_column(String(3), nullable=False)

    coverage_type: Mapped[CoverageType] = mapped_column(String(30), nullable=False)
    coverage_start: Mapped[date] = mapped_column(Date, nullable=False)
    coverage_end: Mapped[date] = mapped_column(Date, nullable=False)

    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    submission: Mapped[SubmissionRecord] = relationship(back_populates="quotes")
    policy: Mapped["PolicyRecord | None"] = relationship(back_populates="quote", uselist=False)


class PolicyRecord(Base, TimestampMixin):
    """Persisted bound policy."""

    __tablename__ = "policies"

    id: Mapped[UUID] = _uuid_column(primary_key=True)
    policy_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    quote_id: Mapped[UUID] = _uuid_column(foreign_key="quotes.id")
    submission_id: Mapped[UUID] = _uuid_column(foreign_key="submissions.id")

    insured_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[PolicyStatus] = mapped_column(String(20), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    premium_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    premium_currency: Mapped[Currency] = mapped_column(String(3), nullable=False)
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bound_by: Mapped[str] = mapped_column(String(100), nullable=False)

    quote: Mapped[QuoteRecord] = relationship(back_populates="policy")

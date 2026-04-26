"""Database model for policy endorsements."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from shared.database.base import Base, TimestampMixin
from shared.domain.endorsement import EndorsementStatus, EndorsementType
from shared.domain.enums import Currency


class EndorsementRecord(Base, TimestampMixin):
    """Persisted record of a policy endorsement."""

    __tablename__ = "endorsements"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, nullable=False)
    policy_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("policies.id"), nullable=False, index=True
    )
    endorsement_number: Mapped[str] = mapped_column(
        String(60), unique=True, index=True, nullable=False
    )
    endorsement_type: Mapped[EndorsementType] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    premium_adjustment_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    premium_adjustment_currency: Mapped[Currency] = mapped_column(String(3), nullable=False)
    status: Mapped[EndorsementStatus] = mapped_column(String(20), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# Helper to allow consistent UUID column use across models
def _uuid_str(value: UUID | str | Any) -> str:
    """Normalise a value to a UUID string."""
    if isinstance(value, UUID):
        return str(value)
    return str(value)

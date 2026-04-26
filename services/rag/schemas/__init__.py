"""Schemas for the RAG API."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field
from shared.database import HistoricalPolicyRecord


class HistoricalPolicySummary(BaseModel):
    """Lightweight summary of a historical policy."""

    id: UUID
    policy_number: str
    insured_name: str
    business_description: str
    fleet_size: int
    primary_vehicle_type: str
    annual_revenue: float
    operates_internationally: bool
    risk_band: str
    final_premium: float
    bound: bool
    claims_count_5y: int
    actual_claims_count: int
    actual_claims_value: float
    loss_ratio: float
    period_start: date
    period_end: date
    underwriter_notes: str

    @classmethod
    def from_record(cls, record: HistoricalPolicyRecord) -> "HistoricalPolicySummary":
        """Build summary from a database record."""
        return cls(
            id=UUID(record.id) if isinstance(record.id, str) else record.id,
            policy_number=record.policy_number,
            insured_name=record.insured_name,
            business_description=record.business_description,
            fleet_size=record.fleet_size,
            primary_vehicle_type=record.primary_vehicle_type,
            annual_revenue=float(record.annual_revenue),
            operates_internationally=record.operates_internationally,
            risk_band=record.risk_band,
            final_premium=float(record.final_premium),
            bound=record.bound,
            claims_count_5y=record.claims_count_5y,
            actual_claims_count=record.actual_claims_count,
            actual_claims_value=float(record.actual_claims_value),
            loss_ratio=float(record.loss_ratio),
            period_start=record.period_start,
            period_end=record.period_end,
            underwriter_notes=record.underwriter_notes,
        )


class SimilarPolicyResponse(BaseModel):
    """A historical policy match with similarity score."""

    similarity: float = Field(
        ..., ge=-1.0, le=1.0, description="Cosine similarity, higher is more similar."
    )
    policy: HistoricalPolicySummary


class SimilarityResponse(BaseModel):
    """Response containing similar historical policies for a submission."""

    submission_id: UUID
    matches: list[SimilarPolicyResponse]

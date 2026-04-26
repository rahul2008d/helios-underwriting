"""Response schemas for the risk service."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from shared.domain import Money, RiskBand, TriageDecision


class TriageResultResponse(BaseModel):
    """Triage outcome for a submission."""

    submission_id: UUID
    decision: TriageDecision
    confidence: float
    reasoning: str
    appetite_matches: list[str]
    appetite_concerns: list[str]
    triaged_at: datetime


class RiskAssessmentResponse(BaseModel):
    """Risk assessment outcome."""

    submission_id: UUID
    risk_band: RiskBand
    risk_score: float
    factors: dict[str, float]
    summary: str
    assessed_at: datetime


class PricingSuggestionResponse(BaseModel):
    """Pricing suggestion."""

    submission_id: UUID
    premium: Money
    base_premium: Money
    risk_loading_pct: float
    rationale: str


class UnderwritingDecisionResponse(BaseModel):
    """Combined output of the full underwriting workflow."""

    submission_id: UUID
    triage: TriageResultResponse
    assessment: RiskAssessmentResponse | None = None
    pricing: PricingSuggestionResponse | None = None

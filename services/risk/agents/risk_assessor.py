"""Risk assessor: deterministic risk scoring with optional LLM-generated summary.

Risk scoring is deterministic (calculated from submission data using documented
rules) so it's reproducible and auditable. The narrative summary is generated
by the LLM, framed by the deterministic factors.

This hybrid approach is exactly how production insurance systems work - the
numbers are reliable, the prose is helpful, and the LLM is constrained by
the calculated facts.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from shared.config import get_settings
from shared.domain import RiskAssessment, RiskBand, Submission
from shared.logging import logger


class RiskFactors(BaseModel):
    """Calculated risk factors and their contributions."""

    fleet_size_factor: float
    driver_experience_factor: float
    driver_points_factor: float
    claims_history_factor: float
    international_operations_factor: float
    high_risk_vehicle_factor: float
    young_driver_factor: float


class _RiskSummaryOutput(BaseModel):
    """Schema for the LLM-generated narrative summary."""

    summary: str = Field(
        description="2-4 sentence underwriter-facing risk summary explaining the score.",
        min_length=50,
        max_length=1000,
    )


_SYSTEM_PROMPT = """
You write concise, factual risk summaries for commercial fleet insurance
underwriters. Given the calculated risk factors, produce a 2-4 sentence
narrative explaining what is driving the risk.

Be specific. Mention the actual figures (claims, points, fleet size) where
relevant. Do not speculate beyond the data provided. Focus on what an
underwriter would want to know first.
""".strip()


class RiskAssessor:
    """Deterministic risk scoring + LLM-generated narrative summary."""

    def __init__(self, model: str | None = None) -> None:
        """Create an assessor; the LLM client is only built when a summary is generated."""
        settings = get_settings()
        self._model_name = model or f"openai:{settings.openai_model}"
        # Lazy-init so unit tests of deterministic logic need no OpenAI key.
        self._summary_agent: Agent[None, _RiskSummaryOutput] | None = None

    def _get_summary_agent(self) -> Agent[None, _RiskSummaryOutput]:
        if self._summary_agent is None:
            self._summary_agent = Agent(
                self._model_name,
                output_type=_RiskSummaryOutput,
                system_prompt=_SYSTEM_PROMPT,
                retries=2,
            )
        return self._summary_agent

    async def assess(self, submission: Submission) -> RiskAssessment:
        """Calculate risk factors, total score, and narrative summary."""
        factors = self._calculate_factors(submission)
        risk_score = self._calculate_score(factors)
        risk_band = self._score_to_band(risk_score)

        logger.info(
            "calculated risk score",
            submission_id=str(submission.id),
            score=risk_score,
            band=risk_band.value,
        )

        summary = await self._generate_summary(submission, factors, risk_score, risk_band)

        return RiskAssessment(
            submission_id=submission.id,
            risk_band=risk_band,
            risk_score=risk_score,
            factors=factors.model_dump(),
            summary=summary,
            assessed_at=datetime.utcnow(),
        )

    def _calculate_factors(self, submission: Submission) -> RiskFactors:
        """Compute individual risk factor scores between 0 and 100.

        Higher means riskier. Each factor isolates one risk dimension.
        """
        # Fleet size: small (under 5) and very large (over 80) are higher risk
        fleet_size = submission.fleet_size
        if fleet_size < 5:
            fleet_size_factor = 30.0
        elif fleet_size > 80:
            fleet_size_factor = 50.0
        elif fleet_size > 50:
            fleet_size_factor = 30.0
        else:
            fleet_size_factor = 10.0

        # Average driver experience
        avg_experience = (
            sum(d.years_licensed for d in submission.drivers) / len(submission.drivers)
            if submission.drivers
            else 0
        )
        if avg_experience < 5:
            driver_experience_factor = 60.0
        elif avg_experience < 10:
            driver_experience_factor = 30.0
        else:
            driver_experience_factor = 5.0

        # Drivers with high points
        max_points = max((d.points for d in submission.drivers), default=0)
        if max_points >= 9:
            driver_points_factor = 70.0
        elif max_points >= 6:
            driver_points_factor = 40.0
        elif max_points >= 3:
            driver_points_factor = 20.0
        else:
            driver_points_factor = 5.0

        # Claims history (frequency per vehicle per year)
        claims_per_vehicle_year = (
            submission.claims_count_5y / (submission.fleet_size * 5)
            if submission.fleet_size > 0
            else 0
        )
        if claims_per_vehicle_year > 0.5:
            claims_history_factor = 80.0
        elif claims_per_vehicle_year > 0.2:
            claims_history_factor = 40.0
        elif claims_per_vehicle_year > 0.1:
            claims_history_factor = 20.0
        else:
            claims_history_factor = 5.0

        # International operations
        international_operations_factor = 30.0 if submission.operates_internationally else 5.0

        # High-risk vehicle types
        high_risk_types = {"hazardous", "specialist"}
        high_risk_count = sum(
            1 for v in submission.vehicles if v.vehicle_type.value in high_risk_types
        )
        high_risk_vehicle_factor = 50.0 if high_risk_count > 0 else 5.0

        # Young drivers
        young_driver_count = sum(1 for d in submission.drivers if d.age < 25)
        young_driver_ratio = (
            young_driver_count / len(submission.drivers) if submission.drivers else 0
        )
        if young_driver_ratio > 0.5:
            young_driver_factor = 60.0
        elif young_driver_ratio > 0.2:
            young_driver_factor = 30.0
        else:
            young_driver_factor = 5.0

        return RiskFactors(
            fleet_size_factor=fleet_size_factor,
            driver_experience_factor=driver_experience_factor,
            driver_points_factor=driver_points_factor,
            claims_history_factor=claims_history_factor,
            international_operations_factor=international_operations_factor,
            high_risk_vehicle_factor=high_risk_vehicle_factor,
            young_driver_factor=young_driver_factor,
        )

    @staticmethod
    def _calculate_score(factors: RiskFactors) -> float:
        """Combine factors into a single 0-100 risk score.

        Weighted average that emphasises claims history and driver risk,
        which historically correlate most strongly with future losses.
        """
        weights = {
            "fleet_size_factor": 0.10,
            "driver_experience_factor": 0.20,
            "driver_points_factor": 0.15,
            "claims_history_factor": 0.30,
            "international_operations_factor": 0.05,
            "high_risk_vehicle_factor": 0.10,
            "young_driver_factor": 0.10,
        }
        score = sum(getattr(factors, name) * weight for name, weight in weights.items())
        return float(round(min(100.0, max(0.0, score)), 2))

    @staticmethod
    def _score_to_band(score: float) -> RiskBand:
        """Convert a numeric risk score into a discrete band."""
        if score >= 70:
            return RiskBand.EXTREME
        if score >= 50:
            return RiskBand.HIGH
        if score >= 25:
            return RiskBand.MEDIUM
        return RiskBand.LOW

    async def _generate_summary(
        self,
        submission: Submission,
        factors: RiskFactors,
        score: float,
        band: RiskBand,
    ) -> str:
        """Use the LLM to write a short underwriter-facing summary."""
        max_driver_points = max((d.points for d in submission.drivers), default=0)
        drivers_under_25 = sum(1 for d in submission.drivers if d.age < 25)
        prompt = f"""
Write a risk summary for this submission.

Insured: {submission.insured_name}
Business: {submission.business_description}
Risk score: {score:.1f} / 100 (band: {band.value})

# Calculated factors (higher = riskier)
- Fleet size factor: {factors.fleet_size_factor:.0f} (fleet of {submission.fleet_size})
- Driver experience factor: {factors.driver_experience_factor:.0f}
- Driver points factor: {factors.driver_points_factor:.0f} (max points: {max_driver_points})
- Claims history factor: {factors.claims_history_factor:.0f} (
  {submission.claims_count_5y} claims, {submission.claims_value_5y} total
)
- International operations factor: {factors.international_operations_factor:.0f} (
  operates internationally: {submission.operates_internationally}
)
- High-risk vehicle factor: {factors.high_risk_vehicle_factor:.0f}
- Young driver factor: {factors.young_driver_factor:.0f} (
  {drivers_under_25} drivers under 25
)

Write a 2-4 sentence summary explaining what is driving this risk score.
""".strip()

        result = await self._get_summary_agent().run(prompt)
        return str(result.output.summary)

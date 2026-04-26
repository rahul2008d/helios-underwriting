"""Pricing agent: suggests a premium based on risk and fleet characteristics.

Like the risk assessor, this is a hybrid: a deterministic base premium
calculation plus an LLM-generated rationale. Production pricing engines work
this way - the maths is reliable, the prose is helpful.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from shared.config import get_settings
from shared.domain import Currency, Money, RiskAssessment, RiskBand, Submission
from shared.logging import logger


class PricingSuggestion(BaseModel):
    """Output of the pricing agent."""

    premium: Money
    base_premium: Money = Field(description="Premium before risk loading.")
    risk_loading_pct: float = Field(description="Risk loading applied, e.g. 0.25 for 25%.")
    rationale: str = Field(description="Underwriter-facing explanation of the price.")


class _PricingRationaleOutput(BaseModel):
    """Schema for the LLM-generated pricing rationale."""

    rationale: str = Field(
        description="2-3 sentence explanation of the suggested premium.",
        min_length=50,
        max_length=800,
    )


_RISK_LOADINGS = {
    RiskBand.LOW: 0.00,
    RiskBand.MEDIUM: 0.20,
    RiskBand.HIGH: 0.50,
    RiskBand.EXTREME: 1.00,
}

_BASE_RATE_PER_VEHICLE = {
    "van": Decimal("1200"),
    "lorry": Decimal("2500"),
    "articulated": Decimal("3800"),
    "refrigerated": Decimal("3000"),
    "hazardous": Decimal("5500"),
    "specialist": Decimal("3500"),
}

_SYSTEM_PROMPT = """
You write concise pricing rationales for fleet insurance underwriters. Given
the calculated base premium, risk loading, and final price, explain in 2-3
sentences what is driving the price.

Be specific. Reference the risk band, the loading percentage, and the key
fleet characteristics. Do not speculate beyond the data provided.
""".strip()


class PricingAgent:
    """Hybrid deterministic + LLM pricing agent."""

    def __init__(self, model: str | None = None) -> None:
        """Create an agent; the LLM client is only built when a rationale is generated."""
        settings = get_settings()
        self._model_name = model or f"openai:{settings.openai_model}"
        self._rationale_agent: Agent[None, _PricingRationaleOutput] | None = None

    def _get_rationale_agent(self) -> Agent[None, _PricingRationaleOutput]:
        if self._rationale_agent is None:
            self._rationale_agent = Agent(
                self._model_name,
                output_type=_PricingRationaleOutput,
                system_prompt=_SYSTEM_PROMPT,
                retries=2,
            )
        return self._rationale_agent

    async def suggest(
        self,
        submission: Submission,
        risk_assessment: RiskAssessment,
    ) -> PricingSuggestion:
        """Calculate a premium suggestion and generate a rationale."""
        base_premium = self._calculate_base_premium(submission)
        risk_loading = _RISK_LOADINGS[risk_assessment.risk_band]
        final_premium = base_premium * (Decimal("1") + Decimal(str(risk_loading)))
        final_premium = final_premium.quantize(Decimal("0.01"))

        currency = submission.annual_revenue.currency

        logger.info(
            "calculated premium",
            submission_id=str(submission.id),
            base_premium=str(base_premium),
            risk_loading=risk_loading,
            final_premium=str(final_premium),
        )

        rationale = await self._generate_rationale(
            submission=submission,
            risk_assessment=risk_assessment,
            base_premium=base_premium,
            risk_loading=risk_loading,
            final_premium=final_premium,
            currency=currency,
        )

        return PricingSuggestion(
            premium=Money(amount=final_premium, currency=currency),
            base_premium=Money(amount=base_premium, currency=currency),
            risk_loading_pct=risk_loading,
            rationale=rationale,
        )

    @staticmethod
    def _calculate_base_premium(submission: Submission) -> Decimal:
        """Sum the base rate for each vehicle in the fleet."""
        total = Decimal(0)
        for vehicle in submission.vehicles:
            rate = _BASE_RATE_PER_VEHICLE.get(vehicle.vehicle_type.value, Decimal("1500"))
            mileage_factor = Decimal("1") + (
                Decimal(str(vehicle.annual_mileage)) / Decimal("100000")
            )
            total += rate * mileage_factor
        return total.quantize(Decimal("0.01"))

    async def _generate_rationale(
        self,
        *,
        submission: Submission,
        risk_assessment: RiskAssessment,
        base_premium: Decimal,
        risk_loading: float,
        final_premium: Decimal,
        currency: Currency,
    ) -> str:
        """Call the LLM to write a pricing rationale."""
        prompt = f"""
Write a pricing rationale for this submission.

Insured: {submission.insured_name}
Fleet size: {submission.fleet_size}
Risk band: {risk_assessment.risk_band.value} (score: {risk_assessment.risk_score:.1f})

Base premium: {currency.value} {base_premium:,.2f}
Risk loading: {risk_loading * 100:.0f}%
Final premium: {currency.value} {final_premium:,.2f}

Risk summary: {risk_assessment.summary}

Explain the price in 2-3 sentences.
""".strip()

        result = await self._get_rationale_agent().run(prompt)
        return str(result.output.rationale)

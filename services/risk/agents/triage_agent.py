"""Triage agent: classifies submissions against appetite using an LLM.

The agent takes a Submission and returns a TriageResult with a structured
decision (ACCEPT / REFER / DECLINE), confidence, reasoning, and the
specific appetite criteria that matched or raised concerns.

Pydantic AI handles schema enforcement: even though the LLM returns text,
its output is validated against the TriageOutput schema before being
returned. If validation fails, PydanticAI retries automatically.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from shared.config import get_settings
from shared.domain import Submission, TriageDecision, TriageResult
from shared.logging import logger

from services.risk.agents.appetite import APPETITE_GUIDELINES


class TriageOutput(BaseModel):
    """Schema the LLM is required to produce."""

    decision: TriageDecision = Field(
        description="The triage decision: accept, refer, or decline.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="How confident the agent is in this decision, 0 to 1.",
    )
    reasoning: str = Field(
        description="Concise explanation of the decision, suitable for an underwriter.",
        max_length=2000,
    )
    appetite_matches: list[str] = Field(
        default_factory=list,
        description="Bullet points of appetite criteria that this submission satisfies.",
    )
    appetite_concerns: list[str] = Field(
        default_factory=list,
        description="Bullet points of appetite criteria that raise concerns.",
    )


_SYSTEM_PROMPT = f"""
You are an experienced commercial fleet insurance triage underwriter at Helios
Underwriting. Your job is to classify each submission against our appetite
guidelines and decide whether to ACCEPT it for full assessment, REFER it to a
senior underwriter, or DECLINE it.

Be precise. Cite specific facts from the submission. Do not invent details.
If the submission falls outside the listed appetite categories, prefer REFER
over DECLINE unless it clearly violates a hard rule.

# Helios appetite guidelines
{APPETITE_GUIDELINES}

# Decision rules
- ACCEPT: clearly within appetite, no material concerns.
- REFER: matches an edge case, or has notable risk factors needing human judgement.
- DECLINE: clearly outside appetite, hard rule violated.
""".strip()


class TriageAgent:
    """Wraps a PydanticAI agent for submission triage."""

    def __init__(self, model: str | None = None) -> None:
        """Create an agent; the LLM client is only built on first triage."""
        settings = get_settings()
        self._model_name = model or f"openai:{settings.openai_model}"
        self._agent: Agent[None, TriageOutput] | None = None

    def _get_agent(self) -> Agent[None, TriageOutput]:
        if self._agent is None:
            self._agent = Agent(
                self._model_name,
                output_type=TriageOutput,
                system_prompt=_SYSTEM_PROMPT,
                retries=2,
            )
        return self._agent

    async def triage(self, submission: Submission) -> TriageResult:
        """Run triage on a submission and return a TriageResult."""
        prompt = self._build_prompt(submission)

        logger.info(
            "running triage agent",
            submission_id=str(submission.id),
            reference=submission.reference,
            model=self._model_name,
        )

        result = await self._get_agent().run(prompt)
        output = result.output

        logger.info(
            "triage agent decision",
            submission_id=str(submission.id),
            decision=output.decision.value,
            confidence=output.confidence,
        )

        return TriageResult(
            submission_id=submission.id,
            decision=output.decision,
            confidence=output.confidence,
            reasoning=output.reasoning,
            appetite_matches=output.appetite_matches,
            appetite_concerns=output.appetite_concerns,
            triaged_at=datetime.utcnow(),
        )

    @staticmethod
    def _build_prompt(submission: Submission) -> str:
        """Build the user prompt summarising the submission for the LLM."""
        vehicle_summary = ", ".join(
            f"{v.vehicle_type.value} ({v.make} {v.model}, {v.year})"
            for v in submission.vehicles[:10]
        )
        if len(submission.vehicles) > 10:
            vehicle_summary += f", and {len(submission.vehicles) - 10} more"

        avg_driver_experience = (
            sum(d.years_licensed for d in submission.drivers) / len(submission.drivers)
            if submission.drivers
            else 0
        )

        return f"""
Triage this fleet insurance submission and classify it.

# Submission summary
Reference: {submission.reference}
Insured: {submission.insured_name}
Business: {submission.business_description}
Annual revenue: {submission.annual_revenue}
Operates internationally: {submission.operates_internationally}
Countries of operation: {", ".join(submission.countries_of_operation)}

# Fleet
Fleet size: {submission.fleet_size}
Total fleet value: {submission.annual_revenue.currency.value} {submission.total_fleet_value:,.2f}
Vehicles: {vehicle_summary}

# Drivers
Driver count: {len(submission.drivers)}
Average driver experience: {avg_driver_experience:.1f} years
Drivers with points > 6: {sum(1 for d in submission.drivers if d.points > 6)}
Drivers under 25: {sum(1 for d in submission.drivers if d.age < 25)}
Drivers with convictions in last 5y: {sum(1 for d in submission.drivers if d.convictions_5y > 0)}

# Loss history (last 5 years)
Claims count: {submission.claims_count_5y}
Claims value: {submission.claims_value_5y}

Provide your triage decision in the required structured format.
""".strip()

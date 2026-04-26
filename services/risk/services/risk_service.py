"""Risk service: orchestrates triage, assessment, and pricing for submissions."""

from uuid import UUID

from shared.domain import (
    RiskAssessment,
    Submission,
    SubmissionStatus,
    TriageDecision,
    TriageResult,
)
from shared.logging import logger

from services.risk.agents import (
    PricingAgent,
    PricingSuggestion,
    RiskAssessor,
    TriageAgent,
)
from services.risk.repositories import AssessmentRepository, TriageRepository
from services.risk.services.exceptions import SubmissionNotFoundError
from services.submission.repositories import SubmissionRepository
from services.submission.services import SubmissionService


class RiskService:
    """Coordinates AI agents to process a submission end-to-end."""

    def __init__(
        self,
        *,
        submission_repository: SubmissionRepository,
        triage_repository: TriageRepository,
        assessment_repository: AssessmentRepository,
        triage_agent: TriageAgent | None = None,
        risk_assessor: RiskAssessor | None = None,
        pricing_agent: PricingAgent | None = None,
    ) -> None:
        """Wire persistence and agents; inject agents in tests to supply mocks."""
        self._submission_repository = submission_repository
        self._submission_service = SubmissionService(submission_repository)
        self._triage_repository = triage_repository
        self._assessment_repository = assessment_repository
        self._triage_agent = triage_agent or TriageAgent()
        self._risk_assessor = risk_assessor or RiskAssessor()
        self._pricing_agent = pricing_agent or PricingAgent()

    async def triage(self, submission_id: UUID) -> TriageResult:
        """Run the triage agent on a submission and persist the result."""
        submission = await self._load_submission(submission_id)

        triage_result = await self._triage_agent.triage(submission)
        await self._triage_repository.add(triage_result)

        # Update submission status based on triage outcome
        new_status = (
            SubmissionStatus.DECLINED
            if triage_result.decision == TriageDecision.DECLINE
            else SubmissionStatus.TRIAGED
        )
        await self._submission_service.transition_status(submission_id, new_status)

        return triage_result

    async def assess(self, submission_id: UUID) -> RiskAssessment:
        """Run risk assessment on a submission and persist the result."""
        submission = await self._load_submission(submission_id)

        assessment = await self._risk_assessor.assess(submission)
        await self._assessment_repository.add(assessment)

        await self._submission_service.transition_status(submission_id, SubmissionStatus.ASSESSED)

        return assessment

    async def suggest_pricing(self, submission_id: UUID) -> PricingSuggestion:
        """Generate a pricing suggestion using the latest risk assessment."""
        submission = await self._load_submission(submission_id)
        assessment = await self._assessment_repository.latest_for_submission(submission_id)

        if assessment is None:
            logger.info("running assessment before pricing", submission_id=str(submission_id))
            assessment = await self._risk_assessor.assess(submission)
            await self._assessment_repository.add(assessment)

        return await self._pricing_agent.suggest(submission, assessment)

    async def process_full_workflow(
        self, submission_id: UUID
    ) -> tuple[TriageResult, RiskAssessment | None, PricingSuggestion | None]:
        """Run the full pipeline: triage -> (assess -> price) if not declined."""
        triage_result = await self.triage(submission_id)

        if triage_result.decision == TriageDecision.DECLINE:
            logger.info(
                "submission declined at triage, skipping assessment and pricing",
                submission_id=str(submission_id),
            )
            return triage_result, None, None

        assessment = await self.assess(submission_id)
        pricing = await self.suggest_pricing(submission_id)

        return triage_result, assessment, pricing

    async def _load_submission(self, submission_id: UUID) -> Submission:
        """Load a submission or raise SubmissionNotFoundError."""
        submission = await self._submission_repository.get_by_id(submission_id)
        if submission is None:
            raise SubmissionNotFoundError(str(submission_id))
        return submission

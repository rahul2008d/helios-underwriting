"""Async tasks for running underwriting workflows.

These tasks let the API return immediately with a job_id while the actual
AI work (which can take 10-30 seconds) happens in a background worker.

Pattern: The API enqueues a task, gets back a Celery AsyncResult, and
returns the task id. The client polls a status endpoint that uses the
same task id to check progress.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from shared.celery.app import celery_app
from shared.database import get_session_factory
from shared.logging import configure_logging, logger

from services.risk.repositories import AssessmentRepository, TriageRepository
from services.risk.services import RiskService
from services.submission.repositories import SubmissionRepository


@celery_app.task(name="risk.process_underwriting", bind=True, max_retries=2)
def process_underwriting_task(self: Any, submission_id: str) -> dict[str, Any]:
    """Run the full underwriting workflow on a submission asynchronously.

    Returns a dict with the triage decision, risk assessment, and pricing
    suggestion (or just triage if the submission was declined).
    """
    configure_logging()
    logger.info(
        "starting async underwriting workflow",
        task_id=self.request.id,
        submission_id=submission_id,
    )

    # Each Celery task uses `asyncio.run()`, which creates a new event loop. A
    # process-global AsyncEngine is bound to the loop it was first used on, so
    # we must drop the cache before each run or the next task fails with
    # "Future attached to a different loop".
    from shared.database.session import reset_async_engine_cache

    reset_async_engine_cache()

    try:
        result = asyncio.run(_run_workflow(UUID(submission_id)))
        logger.info(
            "async underwriting workflow complete",
            task_id=self.request.id,
            submission_id=submission_id,
            decision=result.get("triage", {}).get("decision"),
        )
        return result
    except Exception as exc:
        logger.error(
            "async underwriting workflow failed",
            task_id=self.request.id,
            submission_id=submission_id,
            error=str(exc),
        )
        raise


async def _run_workflow(submission_id: UUID) -> dict[str, Any]:
    """Run the full underwriting workflow inside an async context."""
    factory = get_session_factory()

    async with factory() as session:
        risk_service = RiskService(
            submission_repository=SubmissionRepository(session),
            triage_repository=TriageRepository(session),
            assessment_repository=AssessmentRepository(session),
        )

        triage, assessment, pricing = await risk_service.process_full_workflow(submission_id)
        await session.commit()

        result: dict[str, Any] = {
            "submission_id": str(submission_id),
            "triage": {
                "decision": triage.decision.value,
                "confidence": triage.confidence,
                "reasoning": triage.reasoning,
                "appetite_matches": triage.appetite_matches,
                "appetite_concerns": triage.appetite_concerns,
            },
        }

        if assessment is not None:
            result["assessment"] = {
                "risk_band": assessment.risk_band.value,
                "risk_score": assessment.risk_score,
                "factors": assessment.factors,
                "summary": assessment.summary,
            }

        if pricing is not None:
            result["pricing"] = {
                "premium_amount": str(pricing.premium.amount),
                "premium_currency": pricing.premium.currency.value,
                "base_premium_amount": str(pricing.base_premium.amount),
                "risk_loading_pct": pricing.risk_loading_pct,
                "rationale": pricing.rationale,
            }

        return result

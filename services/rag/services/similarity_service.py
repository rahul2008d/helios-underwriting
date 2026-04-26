"""Similarity search over historical policies.

Given a new submission, return the top-N most similar historical policies
based on cosine similarity of their embeddings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from shared.logging import logger

from services.rag.services.embedding_service import EmbeddingService, cosine_similarity

if TYPE_CHECKING:
    from shared.database import HistoricalPolicyRecord
    from shared.domain import Submission

    from services.rag.repositories import HistoricalPolicyRepository


@dataclass(frozen=True)
class SimilarPolicyResult:
    """A historical policy match with its similarity score."""

    policy: HistoricalPolicyRecord
    similarity: float


def submission_to_embedding_text(submission: Submission) -> str:
    """Convert a submission to the text used for embedding.

    Same format as the historical seed text so embeddings are comparable.
    """
    primary_vehicle_type = (
        submission.vehicles[0].vehicle_type.value if submission.vehicles else "unknown"
    )
    avg_experience = (
        sum(d.years_licensed for d in submission.drivers) / len(submission.drivers)
        if submission.drivers
        else 0
    )
    return (
        f"Insured: {submission.insured_name}. "
        f"Business: {submission.business_description}. "
        f"Fleet of {submission.fleet_size} {primary_vehicle_type} vehicles. "
        f"Annual revenue {submission.annual_revenue}. "
        f"Operates internationally: {submission.operates_internationally}. "
        f"Average driver experience: {avg_experience:.1f} years. "
        f"Claims in last 5 years: {submission.claims_count_5y} totalling "
        f"{submission.claims_value_5y}."
    )


class SimilarityService:
    """Service for finding similar historical policies."""

    def __init__(
        self,
        *,
        repository: HistoricalPolicyRepository,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        """Initialise with a repository and optional embedding service."""
        self._repository = repository
        self._embedding_service = embedding_service or EmbeddingService()

    async def find_similar(
        self,
        submission: Submission,
        *,
        top_n: int = 5,
    ) -> list[SimilarPolicyResult]:
        """Return the top-N most similar historical policies to a submission."""
        text = submission_to_embedding_text(submission)
        logger.info(
            "finding similar policies",
            submission_id=str(submission.id),
            top_n=top_n,
        )

        query_embedding = await self._embedding_service.embed(text)
        all_policies = await self._repository.list_all()

        if not all_policies:
            logger.warning("no historical policies in database")
            return []

        scored: list[SimilarPolicyResult] = []
        for policy in all_policies:
            score = cosine_similarity(query_embedding, policy.embedding)
            scored.append(SimilarPolicyResult(policy=policy, similarity=score))

        scored.sort(key=lambda item: item.similarity, reverse=True)
        return scored[:top_n]

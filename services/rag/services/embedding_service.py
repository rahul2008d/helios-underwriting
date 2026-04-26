"""Embedding generation using OpenAI's embedding models.

We use text-embedding-3-small (1536 dimensions) - cheap and fast, good
enough for similarity over short business descriptions.
"""

from __future__ import annotations

from openai import AsyncOpenAI
from shared.config import get_settings
from shared.logging import logger

# 1536-dimensional embeddings, ~$0.02 per million tokens
_EMBEDDING_MODEL = "text-embedding-3-small"


class EmbeddingService:
    """Wraps the OpenAI embeddings API for synchronous and batch use."""

    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        """Initialise with an optional pre-configured OpenAI client."""
        settings = get_settings()
        self._client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = _EMBEDDING_MODEL

    async def embed(self, text: str) -> list[float]:
        """Return the embedding for a single text."""
        response = await self._client.embeddings.create(
            model=self._model,
            input=text,
        )
        return list(response.data[0].embedding)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single API call. More efficient for bulk work."""
        if not texts:
            return []
        logger.info("generating batch embeddings", count=len(texts), model=self._model)
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [list(item.embedding) for item in response.data]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two equal-length vectors.

    Returns a value between -1 and 1, where 1 means identical direction.
    For OpenAI embeddings (which are normalised), this is equivalent to
    dot product.
    """
    if len(a) != len(b):
        raise ValueError(f"vectors must have same length, got {len(a)} and {len(b)}")

    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot / (norm_a * norm_b))

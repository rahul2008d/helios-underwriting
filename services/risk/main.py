"""FastAPI application for the risk service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from shared.config import get_settings
from shared.logging import configure_logging, logger

from services.risk.api.v1 import router as v1_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: configure logging on startup."""
    configure_logging()
    settings = get_settings()
    logger.info(
        "risk service starting",
        environment=settings.environment,
        model=settings.openai_model,
    )
    yield
    logger.info("risk service stopping")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Helios Risk Service",
        description=(
            "AI-driven triage, assessment, and pricing for fleet insurance submissions. "
            "Part of the Helios underwriting platform."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(v1_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok", "service": "risk"}

    FastAPIInstrumentor.instrument_app(app)

    return app


app = create_app()

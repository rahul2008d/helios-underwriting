"""FastAPI application for the submission service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from shared.config import get_settings
from shared.logging import configure_logging, logger

from services.submission.api.v1 import router as v1_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: configure logging on startup."""
    configure_logging()
    logger.info("submission service starting", environment=get_settings().environment)
    yield
    logger.info("submission service stopping")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Helios Submission Service",
        description=(
            "Ingestion and management of risk submissions from brokers. "
            "Part of the Helios underwriting platform."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok", "service": "submission"}

    FastAPIInstrumentor.instrument_app(app)

    return app


app = create_app()

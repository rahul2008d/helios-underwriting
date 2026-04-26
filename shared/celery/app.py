"""Celery application configuration."""

from celery import Celery
from shared.config import get_settings

_settings = get_settings()


def make_celery() -> Celery:
    """Build and configure the Celery application.

    Uses Redis as both the broker (task queue) and result backend (where
    task results are stored). In production you'd often split these.
    """
    app = Celery(
        "helios",
        broker=_settings.redis_url,
        backend=_settings.redis_url,
        include=["services.risk.tasks.underwriting_tasks"],
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,
        task_soft_time_limit=270,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        result_expires=3600,
    )

    return app


celery_app = make_celery()

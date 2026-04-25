"""Structured logging configuration using loguru."""

import sys

from loguru import logger

from shared.config import get_settings


def configure_logging() -> None:
    """Configure loguru for the application.

    Removes the default handler and adds a structured one. In production
    environments this would log JSON; in development it logs a readable format.
    """
    settings = get_settings()
    logger.remove()

    if settings.environment == "production":
        logger.add(
            sys.stdout,
            level=settings.log_level,
            format="{message}",
            serialize=True,
        )
    else:
        logger.add(
            sys.stdout,
            level=settings.log_level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            colorize=True,
        )


__all__ = ["configure_logging", "logger"]

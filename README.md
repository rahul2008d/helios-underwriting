# Helios Underwriting Platform

A production-grade insurance underwriting platform built with Python, FastAPI, and PydanticAI.

This project implements the full underwriting workflow for commercial fleet insurance:
submission ingestion, AI-driven triage, risk assessment, pricing, and policy binding.

## Architecture

Microservices-based, with each service handling a specific stage of the underwriting lifecycle:

- **submission**: Ingests and stores risk submissions from brokers
- **risk**: Runs triage and risk assessment using AI agents
- **pricing**: Generates quotes based on portfolio data and risk scores
- **policy**: Manages policy binding, documents, and renewals

All services share a common data layer (`shared/`) and communicate via FastAPI HTTP APIs.

## Tech Stack

- **Language**: Python 3.12
- **Web Framework**: FastAPI
- **Data**: Pydantic v2 + SQLAlchemy 2 + Alembic
- **Database**: MySQL 8 (matching Send Technology's stack)
- **Cache & Queues**: Redis + Celery
- **AI**: PydanticAI with OpenAI
- **Package Management**: uv
- **Quality**: Ruff, mypy (strict), pytest, pre-commit

## Quick Start

```bash
# Install dependencies
uv sync --all-groups

# Set up environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Start infrastructure
docker compose up -d

# Run migrations
uv run alembic upgrade head

# Seed data
uv run python -m shared.seed

# Run a service
uv run uvicorn services.submission.main:app --reload --port 8001
```

## Development

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run all checks
uv run ruff check .
uv run ruff format .
uv run mypy services shared
uv run pytest
```

## Project Status

Built as a learning project to understand insurance underwriting platform architecture.

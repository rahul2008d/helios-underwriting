.PHONY: help install dev-up dev-down test test-unit test-integration lint format type-check check seed seed-historical run-submission run-risk run-pricing run-policy run-rag run-celery-worker run-webapp migrate

help:
	@echo "Available commands:"
	@echo "  install              Install all dependencies"
	@echo "  dev-up               Start MySQL + Redis via docker-compose"
	@echo "  dev-down             Stop MySQL + Redis"
	@echo "  test                 Run all tests"
	@echo "  test-unit            Run unit tests only"
	@echo "  test-integration     Run integration tests only"
	@echo "  lint                 Run ruff linter"
	@echo "  format               Format code with ruff"
	@echo "  type-check           Run mypy type checker"
	@echo "  check                Run lint + format check + type-check + tests"
	@echo "  migrate              Apply database migrations"
	@echo "  seed                 Seed the database with sample submissions"
	@echo "  seed-historical      Seed 50 historical policies (for RAG)"
	@echo "  run-submission       Run the submission service on port 8001"
	@echo "  run-risk             Run the risk service on port 8002"
	@echo "  run-pricing          Run the pricing service on port 8003"
	@echo "  run-policy           Run the policy service on port 8004"
	@echo "  run-rag              Run the RAG service on port 8005"
	@echo "  run-celery-worker    Run a Celery worker for async tasks"
	@echo "  run-webapp           Serve the underwriting workbench UI on port 3000"

install:
	uv sync --all-groups

dev-up:
	docker compose up -d

dev-down:
	docker compose down

test:
	uv run pytest

test-unit:
	uv run pytest tests/unit -v

test-integration:
	uv run pytest tests/integration -v -m integration

lint:
	uv run ruff check .

format:
	uv run ruff format .

type-check:
	uv run mypy services shared

check: lint
	uv run ruff format --check .
	uv run mypy services shared
	uv run pytest

migrate:
	uv run alembic upgrade head

seed:
	uv run python -m scripts.seed_submissions

seed-historical:
	uv run python -m scripts.seed_historical_policies

run-submission:
	uv run uvicorn services.submission.main:app --reload --port 8001 --host 0.0.0.0

run-risk:
	uv run uvicorn services.risk.main:app --reload --port 8002 --host 0.0.0.0

run-pricing:
	uv run uvicorn services.pricing.main:app --reload --port 8003 --host 0.0.0.0

run-policy:
	uv run uvicorn services.policy.main:app --reload --port 8004 --host 0.0.0.0

run-rag:
	uv run uvicorn services.rag.main:app --reload --port 8005 --host 0.0.0.0

run-celery-worker:
	uv run celery -A shared.celery.app worker --loglevel=info --concurrency=2

run-webapp:
	uv run python -m scripts.serve_webapp

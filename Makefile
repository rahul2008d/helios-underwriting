.PHONY: help install dev-up dev-down test test-unit test-integration lint format type-check check seed run-submission run-risk migrate

help:
	@echo "Available commands:"
	@echo "  install           Install all dependencies"
	@echo "  dev-up            Start MySQL + Redis via docker-compose"
	@echo "  dev-down          Stop MySQL + Redis"
	@echo "  test              Run all tests"
	@echo "  test-unit         Run unit tests only"
	@echo "  test-integration  Run integration tests only"
	@echo "  lint              Run ruff linter"
	@echo "  format            Format code with ruff"
	@echo "  type-check        Run mypy type checker"
	@echo "  check             Run lint + format check + type-check + tests"
	@echo "  migrate           Apply database migrations"
	@echo "  seed              Seed the database with sample submissions"
	@echo "  run-submission    Run the submission service on port 8001"
	@echo "  run-risk          Run the risk service on port 8002"

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

run-submission:
	uv run uvicorn services.submission.main:app --reload --port 8001 --host 0.0.0.0

run-risk:
	uv run uvicorn services.risk.main:app --reload --port 8002 --host 0.0.0.0

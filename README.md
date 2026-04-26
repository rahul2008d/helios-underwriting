# Helios Underwriting Platform

A production-grade insurance underwriting platform with AI agents for triage,
risk assessment, and pricing of commercial fleet insurance submissions.

Built as a learning project to demonstrate the architectural patterns used by
modern insurtech platforms: microservices, AI agents with structured outputs,
RAG over historical underwriting decisions, async task processing, and a
clean separation between data, AI, and business logic.

## Architecture

Six services, each running independently:

```
:8001  Submission service   – ingests and stores broker submissions
:8002  Risk service          – AI agents for triage, assessment, pricing
:8003  Pricing service       – formal quote generation with PDF output
:8004  Policy service        – binding, lifecycle, endorsements
:8005  RAG service           – similarity search over historical policies
:3000  Underwriting workbench UI

       Celery worker         – async processing of long-running AI workflows
```

## Tech stack

- **Language**: Python 3.12
- **Web framework**: FastAPI
- **Data validation**: Pydantic v2
- **AI agents**: PydanticAI with OpenAI
- **Embeddings**: text-embedding-3-small for RAG
- **Database**: MySQL 8 with SQLAlchemy 2 async + Alembic
- **Async tasks**: Celery + Redis
- **Package management**: uv
- **Quality**: Ruff, mypy strict, pytest, pre-commit, GitHub Actions

## Quick start

```bash
# 1. Install dependencies
uv sync --all-groups

# 2. Set up environment
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# 3. Start infrastructure
docker compose up -d

# 4. Run migrations
make migrate

# 5. Seed data (10 fictional submissions + 50 historical policies)
make seed
make seed-historical

# 6. Start all services in separate terminals
make run-submission     # Terminal 1
make run-risk           # Terminal 2
make run-pricing        # Terminal 3
make run-policy         # Terminal 4
make run-rag            # Terminal 5
make run-celery-worker  # Terminal 6

# 7. Start the UI
make run-webapp         # Terminal 7

# 8. Open the browser
open http://localhost:3000
```

## What it does

The platform implements the full underwriting lifecycle:

1. **Ingestion** — A broker submits a fleet insurance request with details
   about the company, vehicles, drivers, and claims history.
2. **Triage** — An AI agent classifies the submission against appetite
   guidelines as ACCEPT, REFER, or DECLINE with confidence and reasoning.
3. **Risk assessment** — A hybrid agent calculates a 0–100 risk score
   from 7 weighted factors (claims history, driver experience, etc.) and
   the LLM writes a narrative summary.
4. **Pricing** — Another hybrid agent calculates a base premium per vehicle,
   applies risk-based loading, and the LLM writes a rationale.
5. **Quote** — The pricing suggestion is turned into a formal quote with
   a PDF document the broker can share with the insured.
6. **Bind** — The quote is bound into a policy with a state machine
   enforcing legal transitions (active → cancelled / lapsed / renewed).
7. **Endorsements** — Modifications to live policies (add vehicle, change
   coverage) follow their own lifecycle (proposed → approved → applied).

The RAG layer surfaces the 5 most semantically similar past policies for
each new submission, with their actual loss ratios and underwriter notes —
giving the underwriter context about how similar risks performed.

## Development

```bash
# Run all checks
make check

# Lint and format
make lint
make format

# Type check
make type-check

# Tests
make test
make test-unit
make test-integration
```

Pre-commit hooks enforce Ruff, mypy strict, and detect-secrets on every commit.
The CI pipeline runs lint, type-check, and test as parallel jobs.

## Project structure

```
helios-underwriting/
├── services/
│   ├── submission/    # Risk submission CRUD
│   ├── risk/          # AI agents (triage, assessment, pricing)
│   ├── pricing/       # Quote generation with PDF
│   ├── policy/        # Policy binding and state machine
│   └── rag/           # Similarity search
├── shared/
│   ├── domain/        # Pydantic domain models
│   ├── database/      # SQLAlchemy ORM
│   ├── celery/        # Async task config
│   ├── config/        # Application settings
│   └── logging/       # Structured logging
├── alembic/           # Database migrations
├── tests/
│   ├── unit/          # Unit tests (no DB, no LLM)
│   └── integration/   # Integration tests (real MySQL)
├── webapp/            # Underwriting workbench UI
└── scripts/           # Operational scripts
```

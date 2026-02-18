# Setup Guide

## Prerequisites

- Python `3.12.x`
- `uv`
- Docker + Docker Compose (optional but recommended for local stack)

## 1. Install dependencies

```bash
uv sync
```

## 2. Create local environment file

```bash
cp .env.example .env
```

Core variables for Matrix-only decision runtime:

- `ROOM1_ID`
- `ROOM2_ID`
- `ROOM3_ID`
- `MATRIX_HOMESERVER_URL`
- `DATABASE_URL`
- `LLM_RUNTIME_MODE`
- `LOG_LEVEL`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

For the complete environment contract, review `.env.example`.

Provider mode optional variables:

- `OPENAI_API_KEY`
- `OPENAI_MODEL_LLM1`
- `OPENAI_MODEL_LLM2`

Optional first-admin bootstrap variables:

- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_PASSWORD` or `BOOTSTRAP_ADMIN_PASSWORD_FILE` (set only one)

Bootstrap behavior:

- Executed by `bot-api` on startup
- Creates initial `admin` user only when `users` table is empty
- If users already exist, bootstrap is skipped
- `BOOTSTRAP_ADMIN_PASSWORD_FILE` is recommended in production-like environments

## 3. Run database migrations

```bash
uv run alembic upgrade head
```

## 4. Run test and quality gates

```bash
uv run ruff check .
uv run mypy src apps
uv run pytest -q
```

## 5. Run local stack (optional)

```bash
docker compose up --build
```

## 6. Runtime smoke validation (recommended before manual E2E)

Follow `docs/runtime-smoke.md` to validate:

- local `uv` runtime process startup
- Matrix structured reply readiness for Room-2 decisions
- deterministic LLM runtime mode for provider-unavailable testing

## Common commands

- Create migration:

```bash
uv run alembic revision -m "describe-change"
```

- Apply latest migration:

```bash
uv run alembic upgrade head
```

- Roll back one migration:

```bash
uv run alembic downgrade -1
```

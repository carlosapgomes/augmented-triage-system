# Augmented Triage System (ATS)

Language: [Portugues (BR)](README.md) | **English**

![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Lint](https://img.shields.io/badge/lint-ruff-orange.svg)
![Type Check](https://img.shields.io/badge/types-mypy-blue.svg)
![Tests](https://img.shields.io/badge/tests-pytest-brightgreen.svg)

Augmented Triage System (ATS) is a backend service designed to support real-world clinical triage workflows while keeping healthcare professionals fully in control of decisions and patient care.

ATS does not replace clinical judgment or automate medical decision-making.
The system is designed to assist communication, organization, and information flow during triage, allowing professionals to work more safely and efficiently in high-demand environments.

The primary goal of ATS is to improve coordination, traceability, and situational awareness during triage processes.

ATS is intended as a support tool for healthcare teams and must always be used under professional supervision within established clinical protocols.

Backend services for an event-driven triage workflow over Matrix rooms.

> **Final supported surface:** Django (`django-ops`) is the final human and administrative surface for this project. FastAPI and Matrix are backend runtime components. References to legacy human/admin surfaces in this README are kept only for cutover and retirement troubleshooting.

Core services:

- `bot-api` (FastAPI API — backend runtime, internal endpoints)
- `bot-matrix` (Matrix event ingestion wiring)
- `worker` (job execution runtime)
- `django-ops` (Django web app — official human and administrative surface, port 8001)

This repo is implemented with strict TDD and OpenSpec slice history under `openspec/changes/archive/`.

## Why This Project

- Automates multi-step triage flow across Matrix rooms.
- Preserves auditability with append-only event records.
- Uses deterministic state transitions and queued background jobs.
- Adds admin backend foundations (roles/auth/prompt templates) without introducing UI behavior.

## Current Scope

- Triage workflow foundation is implemented and covered by automated tests.
- The human and administrative surface is consolidated in `django-ops` (port 8001):
  - web session flow (`GET /login/`, `POST /login/`, `POST /logout/`)
  - dashboard and case detail (`/manager/`, `/manager/cases/<uuid>/`)
  - operational web flow (NIR, doctor, scheduler)
  - prompt admin (`/admin/prompts/`) and user admin (`/admin/users/`)
- `bot-api` (port 8000) remains as backend runtime:
  - opaque token authentication (`POST /auth/login`)
  - internal runtime support endpoints
  - Room-2 widget callback (HMAC signature)

## Runtime Topology

```text
Matrix Rooms ---> bot-matrix ----\
                                  \
Web Operators -------> django-ops ----> PostgreSQL <---- worker
                           |
Login/Auth (token) -> bot-api (backend)
```

### Access paths

| Path | Port | Use |
| --- | --- | --- |
| `django-ops` | 8001 | Human/admin surface (all roles) |
| `bot-api` | 8000 | Backend runtime (token auth, widget callback) |
| `postgres` | 5432 | Loopback only |

For the complete publication topology (internal vs external, Cloudflare Tunnel, zone access matrix), see `docs/en/publication-topology.md`.

## Public Surface (Current)

### Human surface — Django (`django-ops`, port 8001)

Web pages and session routes:

- `GET /login/`
- `POST /login/`
- `POST /logout/`
- `GET /nir/`, `GET /nir/upload/` (NIR)
- `GET /doctor/`, `GET /doctor/cases/{id}/decision/` (doctor)
- `GET /scheduler/`, `GET /scheduler/cases/{id}/confirm/` (scheduler)
- `GET /manager/`, `GET /manager/cases/{id}/` (manager — dashboard and case detail)
- `GET /admin/`, `GET /admin/prompts/`, `GET /admin/users/` (admin)

### Backend surface — FastAPI (`bot-api`, port 8000)

Internal/support routes:

- `POST /auth/login` (opaque token issuance)
- `POST /widget/room2/submit` (Room-2 HMAC callback)
- `GET /openapi.json` (internal schema)

## Web Access and Roles

Browser-first access flow (Django, port 8001):

1. Open `http://127.0.0.1:8001/` in a browser.
1. Anonymous access is redirected to `/login/`.
1. Submit email and password in the login form.
1. On success, the app redirects according to role:
   - `nir` → `/nir/`
   - `doctor` → `/doctor/`
   - `scheduler` → `/scheduler/`
   - `manager` → `/manager/`
   - `admin` → `/admin/`
1. Use `Sair` (`POST /logout/`) to end the session.

Role matrix:

| Role | Dashboard | Operational flow | Prompt admin | User admin |
| --- | --- | --- | --- | --- |
| `nir` | — | PDF upload, final acknowledgment | — | — |
| `doctor` | — | web medical decision | — | — |
| `scheduler` | — | scheduling confirmation | — | — |
| `manager` | read-only | — | — | — |
| `admin` | read-only | — | allowed | allowed |

## Project Docs

- Setup: `docs/en/setup.md`
- Admin operations (bootstrap + password reset): `docs/en/setup.md#8-admin-operations`
- Ansible operations runbook (initial installation): `docs/en/ansible_ops_runbook.md`
- Runtime smoke runbook: `docs/en/runtime-smoke.md`
- Manual E2E runbook: `docs/en/manual_e2e_runbook.md`
- Architecture: `docs/en/architecture.md`
- Publication topology: `docs/en/publication-topology.md`
- Zone hardening checklist: `docs/en/zone-hardening-checklist.md`
- Decision engine and rulebook: `docs/en/decision-engine-and-rulebook.md`
- Security: `docs/en/security.md`
- Internal implementation context: `PROJECT_CONTEXT.md`

## Bilingual Documentation Contribution Checklist

1. Changed `README.md`? Update `README.en.md` in the same PR.
1. Changed `docs/<file>.md`? Update `docs/en/<file>.md` in the same PR.
1. Keep language selector links at the top of both mirrored files.
1. Run:

```bash
uv run pytest tests/unit/test_readme_bilingual_baseline.py tests/unit/test_docs_bilingual_mirror.py -q
markdownlint-cli2 "README.md" "README.en.md" "docs/*.md" "docs/en/*.md"
```

## Repository Layout

```text
apps/                         # Runtime entrypoints (bot-api, bot-matrix, worker)
src/triage_automation/        # Application/domain/infrastructure code
alembic/                      # DB migrations
tests/                        # Unit, integration, and e2e tests
docs/                         # Public project docs
openspec/                     # Change/spec workflow artifacts
```

## Quick Start

1. Install dependencies:

```bash
uv sync
```

1. Create local env file:

```bash
cp .env.example .env
```

1. Run database migrations:

```bash
uv run alembic upgrade head
```

1. Optional: bootstrap first admin at startup (one-time when `users` is empty):

```bash
export BOOTSTRAP_ADMIN_EMAIL=admin@example.org
export BOOTSTRAP_ADMIN_PASSWORD='change-me-now'
```

For production-like environments, prefer `BOOTSTRAP_ADMIN_PASSWORD_FILE`.

1. Run local quality gates:

```bash
uv run ruff check .
uv run mypy src apps
uv run pytest -q
```

## Local Services (Docker Compose)

```bash
docker compose up --build
```

Compose expects `.env` to be present and starts:

- `postgres`
- `bot-api`
- `bot-matrix`
- `worker`
- `django-ops`

## Deployment Note

This repository is currently optimized for local/dev deployment with Docker Compose.
For production deployment, add environment-specific hardening (secret manager integration,
network policy, TLS termination, and observability).

## CI

Quality gates are enforced in `.github/workflows/quality-gates.yml`.

## License

MIT. See `LICENSE`.

## Attribution

This project was developed with assistance from large language models (LLMs).

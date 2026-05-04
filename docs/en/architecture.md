# Architecture

Language: [Portugues (BR)](../architecture.md) | **English**

## Overview

> **Final supported surface:** Django (`django-ops`) is the final supported human and administrative surface for this program. FastAPI and Matrix are backend runtime components — **their human and administrative surfaces have been retired and must not be treated as a compatibility baseline.** References to those surfaces in the code and artifacts of this repository are exclusively legacy/back-end.

The system is split into four deployable apps plus PostgreSQL:

- `bot-api`: HTTP ingress for login/auth foundation and runtime support endpoints.
- `bot-matrix`: Matrix integration wiring for intake/reaction events.
- `worker`: async queue consumer for extraction, LLM jobs, posting, and cleanup.
- `django-ops`: Django web app for the human interface (dashboard, login, prompt management, web triage workflow).
- `postgres`: source of truth for cases, jobs, message mapping, and audit trail.

## Layering and dependency direction

Code follows this dependency direction:

- adapters (`apps`, `infrastructure/http`, `infrastructure/matrix`)
- application services and ports (`src/triage_automation/application`)
- domain (`src/triage_automation/domain`)
- infrastructure implementations (`src/triage_automation/infrastructure`)

Rules:

- business logic belongs in `application` and `domain`
- adapters should stay thin
- infrastructure details are consumed through ports

## Key modules

- Settings: `src/triage_automation/config/settings.py`
- DB metadata: `src/triage_automation/infrastructure/db/metadata.py`
- Job queue: `src/triage_automation/infrastructure/db/job_queue_repository.py`
- Auth/login route: `src/triage_automation/infrastructure/http/auth_router.py`
- Bot API runtime assembly: `apps/bot_api/main.py`
- Django web app (dashboard, login, management): `apps/django_ops/`

## Final human and administrative surface

- **Django (`django-ops`) is the only supported human and administrative surface.**
  All human interactions (NIR, doctor, scheduler, manager, admin) are consolidated
  exclusively in the Django app on port 8001.
- FastAPI (`bot-api`) and Matrix (`bot-matrix`) are **backend runtime components**
  and no longer expose human/administrative surfaces. Their HTML routes, user
  management endpoints, and prompt management surfaces have been retired.
- **There is no legacy compatibility requirement** with the old FastAPI or Matrix
  human/admin surfaces after cutover.

### Consolidated roles

- `manager`: read-only only (operational dashboard, case detail, auditable timeline).
- `admin`: the only role with mutation powers over users, prompts, and system.

### Conscious architectural exception: `prompt_templates` table

The `prompt_templates` table is a **shared backend component** managed by
Alembic/SQLAlchemy. It is read and written by LLM services, the extraction
pipeline, and the Matrix bot — all of which use SQLAlchemy/asyncpg. The
`DjangoOrmPromptStoreAdapter` (`apps/django_ops/django_prompt_store_adapter.py`)
uses the shared SQLAlchemy infrastructure for prompt persistence.

**This exception is exclusively backend:**

- It is a shared runtime detail between backend components.
- **It does not reintroduce a dependency on the legacy FastAPI/Matrix admin surface.**
- The prompt administrative surface is 100% Django (views, templates,
  session-based authorization).
- The domain contract (`DjangoPromptStorePort`, `DjangoPromptManagementService`)
  remains infrastructure-independent.

## Workflow notes

- The triage lifecycle is state-machine driven (see `PROJECT_CONTEXT.md` for canonical states).
- Cleanup is triggered by the first Room-1 thumbs-up reaction on the final reply, unless an approved web change explicitly moves that checkpoint to an equivalent web action.
- The canonical human closure checkpoint is now the `NIR_FINAL_ACKNOWLEDGMENT` web action (NIR confirms receipt via Django), replacing the Room-1 Matrix thumbs-up reaction as the human trigger.
- The final monitoring and administrative surface in this program converges on Django.
- Prompt management remains admin-only on the Django administrative surface.

## Persistence model (high level)

- `cases`: case lifecycle and artifacts
- `case_events`: append-only audit entries
- `case_messages`: Matrix room/event mappings
- `jobs`: queue records with retries/scheduling
- `prompt_templates`: versioned prompts with single active version per prompt name
- `users` and `auth_tokens`: auth and access-control foundation

## Publication notes

The official publication topology — internal and external paths, role/zone
access matrix, and validation criteria — is documented in
`docs/en/publication-topology.md`.

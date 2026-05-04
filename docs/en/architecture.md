# Architecture

Language: [Portugues (BR)](../architecture.md) | **English**

## Overview

> **Current web-refactor direction:** for the human and administrative surfaces covered by the active web changes, Django is the target implementation. FastAPI and Matrix should be treated as legacy reference points for behavior, audit expectations, and remaining integrations, not as a required structural compatibility baseline.

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

## Workflow notes

- The triage lifecycle is state-machine driven (see `PROJECT_CONTEXT.md` for canonical states).
- During the web refactor, the consolidated human operational and administrative interface should move to `django-ops`; references to human-facing FastAPI/Matrix surfaces are legacy guidance for consultation and controlled retirement.
- Cleanup is triggered by the first Room-1 thumbs-up reaction on the final reply, unless an approved web change explicitly moves that checkpoint to an equivalent web action.
- The final monitoring and administrative surface in this program should converge on Django.
- Prompt management remains admin-only on the administrative surface.

## Persistence model (high level)

- `cases`: case lifecycle and artifacts
- `case_events`: append-only audit entries
- `case_messages`: Matrix room/event mappings
- `jobs`: queue records with retries/scheduling
- `prompt_templates`: versioned prompts with single active version per prompt name
- `users` and `auth_tokens`: auth and access-control foundation

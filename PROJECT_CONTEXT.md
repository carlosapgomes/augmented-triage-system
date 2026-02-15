# Triage Automation Project Context

## Purpose
This file is the implementation pre-read for every slice. It summarizes the authoritative handoff contract, architecture boundaries, and non-negotiable constraints so execution remains deterministic when context is reset.

## Authoritative Sources
- Primary contract: `prompts/first-prompt.md` (embedded `<handoff>` specification).
- Planning artifacts: `openspec/changes/implement-triage-automation/tasks.md` and `openspec/changes/implement-triage-automation/tasks/*.md`.

If this file conflicts with the handoff spec, follow the handoff spec.

## Project Goal
Implement an event-driven triage automation across 3 unencrypted Matrix rooms with full auditability and cleanup-by-reaction semantics:
- Room-1 intake of human PDF messages.
- PDF extraction, watermark record-number handling, LLM structured outputs and suggestion.
- Room-2 doctor decision via webhook callback.
- Room-3 scheduling request/reply parsing with strict template handling.
- Room-1 final reply always as reply-to original intake.
- Cleanup triggered exactly once by first 👍 on Room-1 final reply.

## Extended Goal (Admin Foundation, No UI)
Add foundational backend infrastructure for a future admin interface without changing triage business behavior:
- Prompt template storage with versioning and single active version per prompt name.
- User + role model (`admin`, `reader`) stored in DB.
- Authentication foundation with secure password hashing and role guard utilities.
- Minimal backend login capability only (no UI).

## Architecture and Service Boundaries
- `bot-api` (FastAPI): webhook callback ingress + auth + persistence/enqueue.
- `bot-matrix` (matrix-nio): Matrix event ingestion and reaction routing.
- `worker`: async job execution for extraction/LLM/posting/cleanup.
- `postgres`: source of truth (cases, audit, message map, queue).

Dependency direction:
- adapters -> application/services -> domain -> infrastructure details isolated behind ports.

## Technical Constraints
- Python 3.12
- SQLAlchemy 2.x async + `asyncpg`
- Alembic migrations
- Pydantic for settings/contracts (webhook + LLM schemas)
- `uv` for dependency lock/install
- TDD strictly with pytest
- Deterministic behavior; no hidden side effects

## Non-Negotiable Domain Rules
- Do not redesign state machine or transitions.
- Do not change cleanup semantics: first Room-1 👍 on final reply wins.
- Do not change idempotency contract: unique Room-1 origin event id prevents duplicate case creation.
- Do not change strict Room-3 reply templates.
- Do not change webhook payload contract except confirmed clarifications below.
- Do not change LLM schema intent and validation strictness.
- Room-2 and Room-3 👍 on ack messages are audit-only and never trigger cleanup.
- Do not implement admin UI in this phase.
- Do not change triage workflow behavior while introducing admin foundations.

## Clarifications Locked In (2026-02-15)
- `support_flag` enum: `none | anesthesist | anesthesist_icu`
- Final reply jobs transition directly to `WAIT_R1_CLEANUP_THUMBS` after posting.
- Invalid Room-3 scheduler reply always gets strict re-prompt and remains in `WAIT_APPT`.
- Webhook auth mode for now: HMAC only.
- On startup reconciliation, stale `jobs.status='running'` must be reset to `queued` with unchanged `attempts`.
- Auth foundation token strategy: opaque tokens (not JWT).
- Prompt bootstrap strategy: seed default active prompt templates in migration.

## Core Data Model (Authoritative)
- `cases`: case lifecycle, decisions, appointment fields, final-reply and cleanup timestamps, artifacts.
- `case_events`: append-only audit log.
- `case_messages`: room/event mapping for cleanup targeting.
- `jobs`: Postgres queue with `queued|running|done|failed|dead`, `run_after`, retries.

## State Machine (Status Set)
`NEW`, `R1_ACK_PROCESSING`, `EXTRACTING`, `LLM_STRUCT`, `LLM_SUGGEST`, `R2_POST_WIDGET`, `WAIT_DOCTOR`, `DOCTOR_DENIED`, `DOCTOR_ACCEPTED`, `R3_POST_REQUEST`, `WAIT_APPT`, `APPT_CONFIRMED`, `APPT_DENIED`, `FAILED`, `R1_FINAL_REPLY_POSTED`, `WAIT_R1_CLEANUP_THUMBS`, `CLEANUP_RUNNING`, `CLEANED`.

Implementation note: although the enum includes `R1_FINAL_REPLY_POSTED`, current execution transitions directly to `WAIT_R1_CLEANUP_THUMBS` after final post.

## Execution Quality Bar Per Slice
- Write failing tests first (RED).
- Implement minimal behavior (GREEN).
- Refactor only after passing tests (CLEAN).
- Run verification for each slice:
  - `uv run pytest ...`
  - `uv run ruff check .`
  - `uv run mypy src apps`
- Commit after each completed slice with a meaningful message before moving to the next slice.
- Stop after the slice completes. Do not pre-implement future slices.

## Progressive Docstring/Type Ratchet Context
Active hardening change: `openspec/changes/progressive-docstring-type-hardening/`.

Baseline policy:
- Public-surface-first enforcement: prioritize docstrings and type annotations on public modules/classes/functions.
- Ratchet incrementally by package group; never enable broad strictness in one step.
- Keep behavior unchanged: no workflow/state-machine/business logic changes as part of quality hardening.

Closeout status (2026-02-15):
- Ratchet rollout is complete for `src/triage_automation/application`, `src/triage_automation/domain`, `src/triage_automation/infrastructure`, and `apps/`.
- CI/local gates are active (`ruff`, `mypy`, `pytest`) and required for every slice.

Residual exceptions with rationale:
- `tests/**/*.py`: docstring/type lint rules are intentionally excluded to preserve readability and avoid low-value boilerplate; correctness remains enforced by pytest plus core lint rules.
- `alembic/**/*.py`: docstring/type lint rules are intentionally excluded for migration scripts.
- `src/triage_automation/config/**/*.py`: docstring/type lint rules remain excluded in this phase and require a dedicated follow-up slice to ratchet.

Maintenance rules for future slices:
- New or modified public modules/classes/functions in ratcheted areas must keep docstring and public-signature typing compliance.
- Do not broaden existing lint/type exclusions without an explicit OpenSpec slice and rationale.
- Keep `uv run ruff check .`, `uv run mypy src apps`, and `uv run pytest -q` green before each slice commit.

Ratchet rollout order (authoritative for this change):
1. Baseline policy and scope
2. Initial tooling ratchet config
3. `src/triage_automation/application`
4. `src/triage_automation/domain`
5. `src/triage_automation/infrastructure`
6. `apps/`
7. Tests policy alignment
8. CI/local gate enforcement
9. Final repo verification
10. Closeout and maintenance rules

Acceptance criteria per hardening slice:
- Scope boundaries respected for that slice only.
- `uv run ruff check .` passes.
- `uv run mypy src apps` passes.
- Required scoped tests pass (unit/integration/full as defined by slice).

## Pre-Slice Read Sequence
1. `PROJECT_CONTEXT.md`
2. active change task index (`openspec/changes/<change>/tasks.md`)
3. current slice/task file under `openspec/changes/<change>/tasks/`
4. only then implement

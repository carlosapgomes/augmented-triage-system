# Slice 03 - Worker Handler Map Composition

## Goal
Replace empty runtime handler map with explicit handler registration for existing job types.

## Scope boundaries
Included: handler map construction and startup composition.
Excluded: changing job semantics or adding new job types.

## Files to create/modify
- `apps/worker/main.py`
- optional composition helpers under `src/triage_automation/config/` or `src/triage_automation/application/services/`
- worker runtime wiring tests

## Tests to write FIRST (TDD)
- Add failing test that runtime handler map contains all required existing job types.
- Add failing test that unknown job behavior remains unchanged.

## Implementation steps
1. Build explicit runtime handler map in worker startup.
2. Keep queue runtime and retry/dead-letter flow unchanged.
3. Ensure startup remains deterministic and typed.

## Refactor steps
- Extract `build_worker_handlers()` helper if needed for readability/testing.

## Verification commands
- `uv run pytest tests/unit/test_worker_runtime.py -q`
- `uv run ruff check .`
- `uv run mypy src apps`

## Mandatory checklist
- [x] failing tests written first
- [x] required job types are wired explicitly
- [x] no retry/dead-letter behavior change
- [x] public docstrings and typed signatures preserved
- [x] verification commands pass

## STOP RULE
- [x] stop here and do not start next slice

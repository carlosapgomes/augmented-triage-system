# Slice 04 - Worker Service Wiring

## Goal
Wire runtime handlers to existing application services for full queue execution path.

## Scope boundaries
Included: composition of repositories/adapters/services used by worker handlers.
Excluded: business-rule changes inside services.

## Files to create/modify
- `apps/worker/main.py`
- composition helpers and adapter factories as needed
- integration tests for handler-to-service execution path

## Tests to write FIRST (TDD)
- Add failing integration test that a queued job of each supported type executes through the wired runtime path.
- Add failing test that job completion/failure status transitions remain correct.

## Implementation steps
1. Compose existing services for each handler using runtime dependencies.
2. Wire final-reply and cleanup job handlers using existing service APIs.
3. Keep audit and queue contracts unchanged.

## Refactor steps
- Consolidate repeated composition code while maintaining explicit dependency direction.

## Verification commands
- `uv run pytest tests/integration/test_max_retries_failure_path.py tests/integration/test_room1_final_reply_jobs.py -q`
- `uv run ruff check .`
- `uv run mypy src apps`

## Mandatory checklist
- [ ] failing tests written first
- [ ] handler wiring executes existing services end-to-end
- [ ] no triage workflow/state-machine changes
- [ ] public docstrings and typed signatures preserved
- [ ] verification commands pass

## STOP RULE
- [ ] stop here and do not start next slice

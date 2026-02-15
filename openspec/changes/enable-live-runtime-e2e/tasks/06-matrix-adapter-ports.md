# Slice 06 - Matrix Adapter Port Implementation

## Goal
Implement concrete Matrix runtime adapters for send/reply/redact/media-download operations.

## Scope boundaries
Included: infrastructure adapter code and focused tests.
Excluded: event loop routing logic (next slices).

## Files to create/modify
- `src/triage_automation/infrastructure/matrix/**`
- adapter tests under `tests/unit/` and/or `tests/integration/`

## Tests to write FIRST (TDD)
- Add failing tests for `send_text`, `reply_text`, `redact_event`, and `download_mxc` adapter behavior.
- Add failing tests for normalized error mapping on adapter failures.

## Implementation steps
1. Implement concrete adapter class(es) satisfying service port contracts.
2. Preserve normalized errors expected by application services.
3. Keep adapter logic free of business decisions.

## Refactor steps
- Split transport helpers from adapter surface methods if needed for clarity.

## Verification commands
- `uv run pytest tests/unit -q`
- `uv run ruff check .`
- `uv run mypy src apps`

## Mandatory checklist
- [ ] failing tests written first
- [ ] all required Matrix ports have concrete implementations
- [ ] adapters contain no business logic
- [ ] public docstrings and typed signatures preserved
- [ ] verification commands pass

## STOP RULE
- [ ] stop here and do not start next slice

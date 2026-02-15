# Slice 06 - Ratchet Apps Entrypoints

## Goal
Bring `apps/` entrypoints and top-level wiring modules into compliance.

## Scope boundaries
Included: app entrypoint modules.
Excluded: broad refactors across core packages.

## Files to create/modify
- `apps/**/*.py`

## Tests to write FIRST (TDD)
- Add/update tests when entrypoint typing changes expose missing coverage.

## Implementation steps
1. Add missing public docstrings and annotations.
2. Resolve entrypoint-specific lint/type violations.

## Refactor steps
- Keep startup/runtime behavior unchanged.

## Verification commands
- `uv run pytest tests/integration -q`
- `uv run ruff check .`
- `uv run mypy src apps`

## Mandatory checklist
- [ ] apps scope clean under ratchet rules
- [ ] integration tests pass
- [ ] no runtime behavior changes

## STOP RULE
- [ ] stop here and do not start next slice

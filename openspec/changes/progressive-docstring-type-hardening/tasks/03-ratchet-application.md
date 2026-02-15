# Slice 03 - Ratchet Application Package

## Goal
Bring `src/triage_automation/application` into compliance with configured docstring and typing policy.

## Scope boundaries
Included: application package remediation.
Excluded: domain/infrastructure/apps.

## Files to create/modify
- `src/triage_automation/application/**/*.py`
- `tests/unit/**/*.py` (only if needed for typing compatibility)

## Tests to write FIRST (TDD)
- Update/add tests only when behavior-preserving signature updates require it.

## Implementation steps
1. Add missing public docstrings.
2. Add/repair type annotations for public interfaces.
3. Resolve package-specific lint/type violations.

## Refactor steps
- Keep behavior unchanged; avoid business-logic rewrites.

## Verification commands
- `uv run pytest tests/unit -q`
- `uv run ruff check .`
- `uv run mypy src apps`

## Mandatory checklist
- [ ] application package clean under ratchet rules
- [ ] unit tests pass
- [ ] no workflow behavior change

## STOP RULE
- [ ] stop here and do not start next slice

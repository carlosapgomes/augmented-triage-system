# Slice 04 - Ratchet Domain Package

## Goal
Bring `src/triage_automation/domain` into compliance with configured docstring and typing policy.

## Scope boundaries
Included: domain package remediation.
Excluded: application/infrastructure/apps.

## Files to create/modify
- `src/triage_automation/domain/**/*.py`
- `tests/unit/**/*.py` (only if needed)

## Tests to write FIRST (TDD)
- Add/update tests only where annotation refactors affect test doubles or interfaces.

## Implementation steps
1. Add missing public docstrings in domain modules.
2. Tighten type annotations and fix mypy issues.

## Refactor steps
- Preserve domain behavior and transition rules exactly.

## Verification commands
- `uv run pytest tests/unit -q`
- `uv run ruff check .`
- `uv run mypy src apps`

## Mandatory checklist
- [ ] domain package clean under ratchet rules
- [ ] unit tests pass
- [ ] no behavior regressions

## STOP RULE
- [ ] stop here and do not start next slice

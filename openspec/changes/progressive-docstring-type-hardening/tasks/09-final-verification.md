# Slice 09 - Final Verification and Cleanup

## Goal
Run full-project validation and resolve remaining violations within defined policy scope.

## Scope boundaries
Included: cleanup of remaining lint/type/docstring issues.
Excluded: feature development.

## Files to create/modify
- any files required to clear remaining policy violations

## Tests to write FIRST (TDD)
- Add tests only when necessary to prove behavior remains unchanged.

## Implementation steps
1. Run full quality suite.
2. Fix residual violations.

## Refactor steps
- Keep diffs minimal and behavior-neutral.

## Verification commands
- `uv run pytest -q`
- `uv run ruff check .`
- `uv run mypy src apps`

## Mandatory checklist
- [ ] full suite green
- [ ] no unresolved policy violations in scoped areas
- [ ] no business behavior change

## STOP RULE
- [ ] stop here and do not start next slice

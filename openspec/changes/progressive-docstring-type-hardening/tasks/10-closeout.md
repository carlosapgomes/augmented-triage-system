# Slice 10 - Closeout and Maintenance Rules

## Goal
Document completed ratchet scope and maintenance rules for future contributions.

## Scope boundaries
Included: closeout notes and residual exception registry.
Excluded: further remediation beyond agreed scope.

## Files to create/modify
- `PROJECT_CONTEXT.md`
- change docs under `openspec/changes/progressive-docstring-type-hardening/`

## Tests to write FIRST (TDD)
- N/A (documentation slice)

## Implementation steps
1. Record completed scopes and remaining intentional exceptions.
2. Define maintenance rule: new code in ratcheted areas must comply.

## Refactor steps
- Keep closeout concise and enforceable.

## Verification commands
- `uv run ruff check .`
- `uv run mypy src apps`
- `uv run pytest -q`

## Mandatory checklist
- [ ] closeout notes complete
- [ ] exceptions documented with rationale
- [ ] quality suite remains green

## STOP RULE
- [ ] stop here and do not start next slice

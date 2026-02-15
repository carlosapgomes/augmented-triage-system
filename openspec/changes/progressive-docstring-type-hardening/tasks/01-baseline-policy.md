# Slice 01 - Baseline Policy and Scope

## Goal
Define the initial policy boundaries for docstrings and type annotations so enforcement is explicit and deterministic.

## Scope boundaries
Included: policy scope notes in project context/docs and config comments.
Excluded: broad code remediation.

## Files to create/modify
- `PROJECT_CONTEXT.md`
- `ruff.toml`
- `mypy.ini`

## Tests to write FIRST (TDD)
- N/A (policy/config slice)

## Implementation steps
1. Document public-surface-first policy and package rollout order.
2. Clarify temporary exclusions and acceptance criteria.

## Refactor steps
- Keep policy concise and aligned with enforceable tooling rules.

## Verification commands
- `uv run ruff check .`
- `uv run mypy src apps`

## Mandatory checklist
- [x] policy documented
- [x] rollout order explicit
- [x] validation commands pass

## STOP RULE
- [x] stop here and do not start next slice

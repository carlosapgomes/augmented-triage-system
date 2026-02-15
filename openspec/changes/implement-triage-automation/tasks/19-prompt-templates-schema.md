# Slice 19 - Prompt Templates Schema and Constraints

## Goal
Add `prompt_templates` DB schema with strict versioning and single-active-version rule per prompt name.

## Scope boundaries
Included: migration + metadata + tests for constraints/indexes.
Excluded: repositories, worker integration.

## Files to create/modify
- `alembic/versions/0002_prompt_templates.py`
- `src/triage_automation/infrastructure/db/metadata.py`
- `tests/integration/test_migration_prompt_templates.py`

## Tests to write FIRST (TDD)
- Table exists with required columns.
- `UNIQUE(name, version)` enforced.
- Partial unique index enforces single active row per name.
- `version > 0` check enforced.

## Implementation steps
1. Add migration for `prompt_templates`.
2. Add metadata model definitions.
3. Add integration tests asserting constraints/indexes.

## Refactor steps
- Extract reusable migration assertion helpers.

## Verification commands
- `uv run pytest tests/integration/test_migration_prompt_templates.py -q`
- `uv run ruff check .`
- `uv run mypy src apps`

## Mandatory checklist
- [ ] spec section referenced
- [ ] failing tests written
- [ ] edge cases included
- [ ] minimal implementation
- [ ] tests pass
- [ ] lint passes
- [ ] type checks pass
- [ ] no triage workflow behavior change

## STOP RULE
- [ ] stop here and do not start next slice

# Slice 20 - Prompt Template Repository and Active Version Service

## Goal
Provide application/infrastructure path to retrieve active prompt content and version by prompt name.

## Scope boundaries
Included: repository port, DB adapter, domain/application errors for missing active prompt.
Excluded: worker usage.

## Files to create/modify
- `src/triage_automation/application/ports/prompt_template_repository_port.py`
- `src/triage_automation/infrastructure/db/prompt_template_repository.py`
- `src/triage_automation/application/services/prompt_template_service.py`
- `tests/integration/test_prompt_template_repository.py`
- `tests/unit/test_prompt_template_service.py`

## Tests to write FIRST (TDD)
- Retrieves active prompt row by name.
- Returns prompt `content` and `version` deterministically.
- Missing active prompt raises explicit domain/application error.
- Multiple versions for same name resolve only active one.

## Implementation steps
1. Add repository interface and adapter query methods.
2. Add service-level helper for worker use.
3. Add explicit error type for missing active prompt.

## Refactor steps
- Centralize prompt-name constants used by services.

## Verification commands
- `uv run pytest tests/unit/test_prompt_template_service.py -q`
- `uv run pytest tests/integration/test_prompt_template_repository.py -q`
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

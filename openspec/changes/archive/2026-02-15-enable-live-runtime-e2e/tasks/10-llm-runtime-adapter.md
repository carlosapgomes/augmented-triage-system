# Slice 10 - LLM Runtime Adapter Wiring

## Goal
Add runtime LLM adapter composition path for live execution while keeping service contracts unchanged.

## Scope boundaries
Included: infrastructure adapter wiring and runtime composition.
Excluded: LLM schema changes or policy behavior changes.

## Files to create/modify
- `src/triage_automation/infrastructure/llm/**`
- runtime composition in `apps/worker/main.py` (or dedicated composition module)
- tests for LLM runtime adapter path

## Tests to write FIRST (TDD)
- Add failing tests for runtime composition selecting a configured LLM adapter.
- Add failing tests proving LLM1/LLM2 services keep existing validation behavior with runtime adapter.

## Implementation steps
1. Introduce provider-backed runtime adapter interface implementation path.
2. Wire adapter into worker service composition.
3. Keep existing retriable error mapping semantics unchanged.

## Refactor steps
- Keep provider-specific concerns isolated to infrastructure adapter modules.

## Verification commands
- `uv run pytest tests/integration/test_process_pdf_case_llm2.py -q`
- `uv run ruff check .`
- `uv run mypy src apps`

## Mandatory checklist
- [x] failing tests written first
- [x] runtime LLM adapter path is wired and typed
- [x] no LLM schema/policy behavior change
- [x] public docstrings and typed signatures preserved
- [x] verification commands pass

## STOP RULE
- [x] stop here and do not start next slice

# Slice 11 - Deterministic LLM Manual-Test Mode

## Goal
Provide deterministic runtime mode for manual smoke testing when external LLM provider is unavailable.

## Scope boundaries
Included: config-controlled deterministic mode and runtime smoke tests.
Excluded: changes to core workflow semantics.

## Files to create/modify
- runtime settings/config modules
- LLM runtime composition modules
- smoke/integration tests and docs references

## Tests to write FIRST (TDD)
- Add failing test for deterministic mode selection via runtime config.
- Add failing smoke/integration test proving workflow can progress through LLM-dependent stages in deterministic mode.

## Implementation steps
1. Add config flag for deterministic LLM runtime mode.
2. Route composition to deterministic adapter when enabled.
3. Ensure audit/prompt-version behavior remains deterministic and explicit.

## Refactor steps
- Keep mode-selection logic in a single composition boundary.

## Verification commands
- `uv run pytest tests/integration/test_llm_prompt_loading_runtime.py tests/integration/test_process_pdf_case_llm2.py -q`
- `uv run ruff check .`
- `uv run mypy src apps`

## Mandatory checklist
- [x] failing tests written first
- [x] deterministic mode is explicit and testable
- [x] workflow semantics remain unchanged
- [x] public docstrings and typed signatures preserved
- [x] verification commands pass

## STOP RULE
- [x] stop here and do not start next slice

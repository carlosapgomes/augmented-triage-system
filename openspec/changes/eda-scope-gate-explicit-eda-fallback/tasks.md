# Tasks

## 1. Fallback determinístico para EDA explícita quando LLM1 retorna unknown

- [x] 1.1 Adicionar teste de regressão (red) e implementar fallback determinístico `unknown -> eda` para evidência textual explícita de solicitação EDA, com precedência das exclusões non-EDA.
- [ ] 1.2 Ampliar cobertura de variações textuais de EDA (sinônimos/abreviações) mantendo explicabilidade de evidência.

## 2. Validação e registro

- [ ] 2.1 Executar validações obrigatórias (`pytest` alvo, `ruff`, `mypy`, `markdownlint`) para os caminhos alterados.
- [ ] 2.2 Registrar evidências de execução e observações neste `tasks.md`.

## Notes

- Slice 1.1 (red -> green) executado com:
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -k "unknown_scope_with_explicit_eda_request_continues_to_llm2" -q` -> 1 falha esperada antes da implementação (`manual_review_required` indevido).
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -k "unknown_scope_with_explicit_eda_request_continues_to_llm2" -q` -> 1 passed após implementar fallback determinístico `unknown -> eda`.
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -q` -> 8 passed.
  - `uv run ruff check src/triage_automation/application/services/process_pdf_case_service.py tests/integration/test_process_pdf_case_llm2.py` -> sem erros.
  - `uv run mypy src/triage_automation/application/services/process_pdf_case_service.py tests/integration/test_process_pdf_case_llm2.py` -> sem erros.
  - `markdownlint-cli2 "openspec/changes/eda-scope-gate-explicit-eda-fallback/**/*.md"` -> sem erros.

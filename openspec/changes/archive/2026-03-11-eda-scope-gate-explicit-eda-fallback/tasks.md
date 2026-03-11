# Tasks

## 1. Fallback determinístico para EDA explícita quando LLM1 retorna unknown

- [x] 1.1 Adicionar teste de regressão (red) e implementar fallback determinístico `unknown -> eda` para evidência textual explícita de solicitação EDA, com precedência das exclusões non-EDA.
- [x] 1.2 Ampliar cobertura de variações textuais de EDA (sinônimos/abreviações) mantendo explicabilidade de evidência.

## 2. Validação e registro

- [x] 2.1 Executar validações obrigatórias (`pytest` alvo, `ruff`, `mypy`, `markdownlint`) para os caminhos alterados.
- [x] 2.2 Registrar evidências de execução e observações neste `tasks.md`.

## Notes

- Slice 1.1 (red -> green) executado com:
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -k "unknown_scope_with_explicit_eda_request_continues_to_llm2" -q` -> 1 falha esperada antes da implementação (`manual_review_required` indevido).
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -k "unknown_scope_with_explicit_eda_request_continues_to_llm2" -q` -> 1 passed após implementar fallback determinístico `unknown -> eda`.
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -q` -> 8 passed.
  - `uv run ruff check src/triage_automation/application/services/process_pdf_case_service.py tests/integration/test_process_pdf_case_llm2.py` -> sem erros.
  - `uv run mypy src/triage_automation/application/services/process_pdf_case_service.py tests/integration/test_process_pdf_case_llm2.py` -> sem erros.
  - `markdownlint-cli2 "openspec/changes/eda-scope-gate-explicit-eda-fallback/**/*.md"` -> sem erros.
- Slice 1.2 (red -> green) executado com:
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -k "dotted_eda_abbreviation or videoendoscopia_evidence_span" -q` -> 1 falha esperada antes da implementação (abreviação pontuada `E.D.A` ainda não reconhecida).
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -k "dotted_eda_abbreviation or videoendoscopia_evidence_span" -q` -> 2 passed após ampliar detecção de abreviação e sinônimos de EDA.
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -q` -> 10 passed.
  - `uv run ruff check src/triage_automation/application/services/process_pdf_case_service.py tests/integration/test_process_pdf_case_llm2.py` -> sem erros.
  - `uv run mypy src/triage_automation/application/services/process_pdf_case_service.py tests/integration/test_process_pdf_case_llm2.py` -> sem erros.
- Slice 2.1 (validação obrigatória) executado com:
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -q` -> 10 passed.
  - `uv run ruff check src/triage_automation/application/services/process_pdf_case_service.py tests/integration/test_process_pdf_case_llm2.py` -> sem erros.
  - `uv run mypy src/triage_automation/application/services/process_pdf_case_service.py tests/integration/test_process_pdf_case_llm2.py` -> sem erros.
  - `markdownlint-cli2 "openspec/changes/eda-scope-gate-explicit-eda-fallback/**/*.md"` -> sem erros.
- Slice 2.2 (registro de evidências) concluído com observação operacional:
  - simulação offline com o PDF de exemplo (`/Users/carlosgomes/Downloads/MARIGLORIA MORAIS DOS SANTOS -EDA.pdf`) confirma que, para `exam_type=unknown`, o gate não retorna mais `manual_review_required` quando há evidência textual explícita de solicitação EDA e ausência de termos de exclusão non-EDA.
- Pós-conclusão (monitoramento de CI remoto) executado com:
  - `quality-gates` para os commits do change confirmados em `completed/success`:
    - `6ae1471` -> run `22930153046`
    - `59e1ad3` -> run `22930263683`
    - `d1a96aa` -> run `22930451472`
    - `7ed43ad` -> run `22930573947`
    - `f51c5a1` -> run `22930636423`
- Pós-conclusão (monitoramento do commit de registro final) executado com:
  - `83e358c` -> run `22930716629` em `completed/success`.

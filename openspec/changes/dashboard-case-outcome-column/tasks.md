# Tasks

## 1. Cobertura de teste (TDD) para coluna de desfecho no dashboard

- [x] 1.1 Adicionar/ajustar teste de integração em `tests/integration/test_dashboard_pages.py` para falhar (red) quando a tabela não exibir a nova coluna de desfecho.
- [x] 1.2 Cobrir em teste os três rótulos esperados da coluna (`ACEITO`, `NEGADO`, `EM_ANDAMENTO`) com dados persistidos em `doctor_decision` e `appointment_status`.

## 2. Projeção e contrato de dados da listagem

- [x] 2.1 Atualizar `CaseMonitoringListItem` em `src/triage_automation/application/ports/case_repository_port.py` para incluir campo explícito de desfecho (`case_outcome`).
- [x] 2.2 Atualizar `SqlAlchemyCaseRepository.list_cases_for_monitoring` em `src/triage_automation/infrastructure/db/case_repository.py` para selecionar `doctor_decision`/`appointment_status` e derivar desfecho com precedência definida no design.

## 3. Renderização da nova coluna na tabela de casos

- [x] 3.1 Atualizar `src/triage_automation/infrastructure/http/templates/dashboard/partials/cases_list_fragment.html` para incluir a coluna de desfecho na listagem.
- [x] 3.2 Garantir que a página continue exibindo identificador, status e atividade mais recente sem regressões de paginação/filtros.

## 4. Verificação de qualidade do slice

- [x] 4.1 Executar testes alvo: `uv run pytest tests/integration/test_dashboard_pages.py -k outcome -q` (ou seleção equivalente que cubra os cenários novos).
- [x] 4.2 Executar lint/type-check dos paths alterados: `uv run ruff check src/triage_automation/application/ports/case_repository_port.py src/triage_automation/infrastructure/db/case_repository.py tests/integration/test_dashboard_pages.py` e `uv run mypy src/triage_automation/application/ports/case_repository_port.py src/triage_automation/infrastructure/db/case_repository.py tests/integration/test_dashboard_pages.py`.
- [x] 4.3 Executar `markdownlint-cli2 "openspec/changes/dashboard-case-outcome-column/*.md" "openspec/changes/dashboard-case-outcome-column/specs/**/*.md"`.

## Notes

- Evidência de TDD (red) para 1.1:
  - `uv run pytest tests/integration/test_dashboard_pages.py -k outcome_column_header -q`
  - Falha esperada confirmada: ausência de `<th scope="col">Desfecho</th>` no HTML da listagem atual.
- Evidência de TDD (red) para 1.2:
  - `uv run pytest tests/integration/test_dashboard_pages.py -k outcome_labels -q`
  - Falha esperada confirmada: ausência dos rótulos `ACEITO`, `NEGADO` e `EM_ANDAMENTO` na listagem atual.
- Evidência de TDD para 2.2 (repositório):
  - Red: `uv run pytest tests/integration/test_case_repositories.py -k derives_operational_outcome -q`
    - Falha esperada: casos com `appointment_status`/`doctor_decision` ainda retornavam `EM_ANDAMENTO`.
  - Green: `uv run pytest tests/integration/test_case_repositories.py -k derives_operational_outcome -q`
    - Passou após derivação de `case_outcome` em `list_cases_for_monitoring`.
- Evidência para 3.1 (template):
  - Green: `uv run pytest tests/integration/test_dashboard_pages.py -k outcome -q`
    - Passou após renderização da coluna `Desfecho` com `item.case_outcome` na tabela.
- Evidência para 3.2 (não regressão de listagem/paginação/filtros):
  - `uv run pytest tests/integration/test_dashboard_pages.py -k outcome_column_header -q`
  - `uv run pytest tests/integration/test_dashboard_pages.py -k "case_list_page_renders_filters_and_paginated_rows_with_unpoly or case_list_fragment_update_respects_filters_and_pagination or outcome" -q`
  - Ambos passaram, confirmando presença contínua de `Status`, `Atividade mais recente`, identificadores de caso e comportamento de filtros/paginação.
- Evidência para 4.1 (testes alvo do change):
  - `uv run pytest tests/integration/test_dashboard_pages.py -k outcome -q`
  - Resultado: `2 passed, 19 deselected`.
- Evidência para 4.2 (lint + type-check dos paths alterados):
  - `uv run ruff check src/triage_automation/application/ports/case_repository_port.py src/triage_automation/infrastructure/db/case_repository.py tests/integration/test_dashboard_pages.py`
  - `uv run mypy src/triage_automation/application/ports/case_repository_port.py src/triage_automation/infrastructure/db/case_repository.py tests/integration/test_dashboard_pages.py`
  - Ambos passaram sem issues.
- Evidência para 4.3 (markdownlint dos artefatos OpenSpec):
  - `markdownlint-cli2 "openspec/changes/dashboard-case-outcome-column/*.md" "openspec/changes/dashboard-case-outcome-column/specs/**/*.md"`
  - Resultado: `0 error(s)`.

# Tasks

## 1. Cobertura de testes (TDD) para totalização do dashboard

- [x] 1.1 Adicionar/ajustar teste de integração em `tests/integration/test_dashboard_pages.py` para validar que a totalização abaixo da tabela exibe `total`, `ACEITO`, `NEGADO` e `EM_ANDAMENTO`.
- [x] 1.2 Cobrir em teste que os totais representam o universo completo da busca filtrada (não apenas os itens da página atual).
- [x] 1.3 Cobrir cenário de busca inicial (`GET /dashboard/cases` sem filtros explícitos) com totalização renderizada para o dia atual.
- [x] 1.4 Cobrir cenário sem resultados com bloco de totalização visível e contadores zerados.

## 2. Contrato interno e agregação de dados

- [x] 2.1 Atualizar o contrato de listagem em `src/triage_automation/application/ports/case_repository_port.py` para incluir estrutura explícita de totais agregados por desfecho.
- [x] 2.2 Ajustar `src/triage_automation/application/services/case_monitoring_service.py` para propagar os totais agregados sem alterar o comportamento dos filtros padrão existentes.
- [x] 2.3 Implementar em `src/triage_automation/infrastructure/db/case_repository.py` a agregação SQL de totais por desfecho usando os mesmos filtros do conjunto listado.
- [x] 2.4 Adicionar/ajustar teste em `tests/integration/test_case_repositories.py` para validar precedência de classificação e consistência dos totais agregados.

## 3. Renderização da totalização no dashboard

- [x] 3.1 Atualizar `src/triage_automation/infrastructure/http/dashboard_router.py` para incluir os totais agregados no contexto da página/fragmento.
- [x] 3.2 Atualizar `src/triage_automation/infrastructure/http/templates/dashboard/partials/cases_list_fragment.html` para renderizar, abaixo da tabela, o bloco de totalização operacional.
- [x] 3.3 Garantir que paginação e atualizações por Unpoly mantenham a totalização coerente com os filtros ativos.

## 4. Verificação final do slice

- [ ] 4.1 Executar testes alvo do dashboard e repositório:
  - `uv run pytest tests/integration/test_dashboard_pages.py -k totals -q`
  - `uv run pytest tests/integration/test_case_repositories.py -k monitoring -q`
- [ ] 4.2 Executar lint/type-check dos arquivos alterados:
  - `uv run ruff check <paths-alterados>`
  - `uv run mypy <paths-alterados>`
- [ ] 4.3 Executar lint dos artefatos OpenSpec alterados:
  - `markdownlint-cli2 "openspec/changes/dashboard-search-result-totals/*.md" "openspec/changes/dashboard-search-result-totals/specs/**/*.md"`

## Notes

- Evidência TDD da task 1.1:
  - Red: `uv run pytest tests/integration/test_dashboard_pages.py -k search_totals_summary -q` (falhou por ausência da totalização no HTML).
  - Green: `uv run pytest tests/integration/test_dashboard_pages.py -k search_totals_summary -q` (passou após renderização do bloco com total/aceitos/negados/em processamento).
- Evidência da task 1.2:
  - `uv run pytest tests/integration/test_dashboard_pages.py -k full_filtered_result_not_current_page -q`
  - Resultado: `1 passed`, cobrindo que a página (com `page_size=1`) mostra apenas um caso, mas a totalização mantém o universo filtrado completo (`3`, `1`, `1`, `1`).
- Evidência da task 1.3:
  - `uv run pytest tests/integration/test_dashboard_pages.py -k initial_load_renders_totals_for_default_current_day -q`
  - Resultado: `1 passed`, cobrindo que o `GET /dashboard/cases` sem filtros explícitos aplica período padrão do dia atual e renderiza totalização coerente.
- Evidência da task 1.4:
  - `uv run pytest tests/integration/test_dashboard_pages.py -k no_results_renders_zeroed_totals -q`
  - Resultado: `1 passed`, cobrindo cenário sem resultados com bloco de totalização visível e contadores zerados (`0`, `0`, `0`, `0`).
- Evidência da task 2.1:
  - Contrato interno atualizado com `CaseMonitoringOutcomeTotals` e campo `totals` em `CaseMonitoringListPage` no arquivo `src/triage_automation/application/ports/case_repository_port.py`.
  - Verificação de qualidade: `uv run ruff check src/triage_automation/application/ports/case_repository_port.py` e `uv run mypy src/triage_automation/application/ports/case_repository_port.py`.
- Evidência da task 2.2:
  - Teste unitário adicionado: `tests/unit/test_case_monitoring_service.py`.
  - Execução: `uv run pytest tests/unit/test_case_monitoring_service.py -q`.
  - Verifica que `CaseMonitoringService` preserva filtros (incluindo janela com `tz_offset`) e propaga o objeto de totais agregado do repositório sem alterar comportamento padrão.
  - Qualidade: `uv run ruff check src/triage_automation/application/services/case_monitoring_service.py tests/unit/test_case_monitoring_service.py` e `uv run mypy src/triage_automation/application/services/case_monitoring_service.py tests/unit/test_case_monitoring_service.py`.
- Evidência da task 2.3:
  - Implementação presente em `src/triage_automation/infrastructure/db/case_repository.py` com `aggregate_statement` baseado no mesmo `from_clause` e `where_clauses` da listagem paginada, garantindo coerência de filtros.
  - Execução de cobertura funcional (via dashboard): `uv run pytest tests/integration/test_dashboard_pages.py -k "search_totals_summary or full_filtered_result_not_current_page or no_results_renders_zeroed_totals" -q`.
  - Qualidade: `uv run ruff check src/triage_automation/infrastructure/db/case_repository.py` e `uv run mypy src/triage_automation/infrastructure/db/case_repository.py`.
- Evidência da task 2.4:
  - Teste de integração ajustado: `tests/integration/test_case_repositories.py::test_case_monitoring_list_derives_operational_outcome_from_decision_fields`.
  - Execução: `uv run pytest tests/integration/test_case_repositories.py -k derives_operational_outcome -q`.
  - Valida precedência (`confirmed > denied por agendamento > denied por médico > em andamento`) e consistência dos totais agregados independentemente da paginação (`page_size=10` e `page_size=1`).
  - Qualidade: `uv run ruff check tests/integration/test_case_repositories.py` e `uv run mypy tests/integration/test_case_repositories.py`.
- Evidência da task 3.1:
  - Contexto do router atualizado com chave `totals` e mapeamento de `result.totals` em `src/triage_automation/infrastructure/http/dashboard_router.py` (linhas com `"totals"`, `total`, `accepted`, `denied`, `in_progress`).
  - Execução de regressão: `uv run pytest tests/integration/test_dashboard_pages.py -k search_totals_summary -q`.
- Evidência da task 3.2:
  - Fragmento atualizado em `src/triage_automation/infrastructure/http/templates/dashboard/partials/cases_list_fragment.html` com bloco `id="cases-search-totals"` e rótulos de totalização abaixo da tabela.
  - Verificação estática: `rg "cases-search-totals|Totalizacao da busca|Em processamento" -n src/triage_automation/infrastructure/http/templates/dashboard/partials/cases_list_fragment.html`.
  - Regressão funcional: `uv run pytest tests/integration/test_dashboard_pages.py -k "search_totals_summary or no_results_renders_zeroed_totals" -q`.
- Evidência da task 3.3:
  - Teste de integração fortalecido: `tests/integration/test_dashboard_pages.py::test_dashboard_case_list_fragment_update_respects_filters_and_pagination`.
  - Execução: `uv run pytest tests/integration/test_dashboard_pages.py -k fragment_update_respects_filters_and_pagination -q`.
  - Valida fragment updates via `X-Up-Target` em páginas 1 e 2 (`page_size=1`) com filtro `status=WAIT_DOCTOR`, mantendo totalização coerente com filtros (`Total de casos: 2`, `Em processamento: 2`) em ambas as páginas e excluindo casos fora do filtro.
  - Qualidade: `uv run ruff check tests/integration/test_dashboard_pages.py` e `uv run mypy tests/integration/test_dashboard_pages.py`.
- Verificações executadas neste slice:
  - `uv run pytest tests/integration/test_dashboard_pages.py -k "search_totals_summary or outcome" -q`
  - `uv run pytest tests/integration/test_case_repositories.py -k operational_outcome -q`
  - `uv run ruff check src/triage_automation/application/ports/case_repository_port.py src/triage_automation/infrastructure/db/case_repository.py src/triage_automation/infrastructure/http/dashboard_router.py tests/integration/test_dashboard_pages.py`
  - `uv run mypy src/triage_automation/application/ports/case_repository_port.py src/triage_automation/infrastructure/db/case_repository.py src/triage_automation/infrastructure/http/dashboard_router.py tests/integration/test_dashboard_pages.py`

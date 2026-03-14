# Dashboard Search Result Totals

## Why

No dashboard de casos, a busca mostra apenas a tabela paginada e o total geral de registros, sem um resumo operacional imediato dos resultados encontrados. Isso dificulta a leitura rápida da operação no dia e exige contagem manual para entender quantos casos foram aceitos, negados ou ainda estão em processamento.

## What Changes

- Adicionar uma seção de totalização abaixo da tabela da busca no dashboard, exibindo:
  - número total de casos encontrados;
  - número de casos `ACEITO`;
  - número de casos `NEGADO`;
  - número de casos `EM_ANDAMENTO` (rotulado como “em processamento”).
- Garantir que a totalização seja calculada sobre todo o universo da busca filtrada (não apenas a página atual).
- Exibir a totalização também na busca inicial padrão do dashboard (dia atual).
- Exibir totalização zerada (`0`) para todas as métricas quando não houver casos encontrados.
- Manter o endpoint JSON `/monitoring/cases` inalterado neste change, restringindo o escopo à experiência do dashboard HTML.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `case-thread-monitoring-dashboard`: a lista de casos do dashboard passa a incluir totalização operacional agregada por desfecho (`ACEITO`, `NEGADO`, `EM_ANDAMENTO`) para o conjunto completo da busca.

## Impact

- Código potencialmente afetado:
  - `src/triage_automation/application/ports/case_repository_port.py`
  - `src/triage_automation/application/services/case_monitoring_service.py`
  - `src/triage_automation/infrastructure/db/case_repository.py`
  - `src/triage_automation/infrastructure/http/dashboard_router.py`
  - `src/triage_automation/infrastructure/http/templates/dashboard/partials/cases_list_fragment.html`
- Testes potencialmente afetados:
  - `tests/integration/test_dashboard_pages.py`
  - `tests/integration/test_case_repositories.py`
- Sem necessidade de migração de banco; reuso dos campos já existentes de decisão (`doctor_decision`, `appointment_status`) e da classificação operacional atual (`case_outcome`).

# Dashboard Case Outcome Column

## Why

No dashboard, a listagem de casos mostra o status técnico do workflow, mas não explicita de forma direta o desfecho operacional (aceito ou negado). Para a operação diária, isso exige abrir o detalhe de cada caso para confirmar o resultado, aumentando tempo de triagem e risco de leitura incorreta.

## What Changes

- Adicionar uma nova coluna na listagem de casos do dashboard para exibir o desfecho operacional do caso.
- Exibir desfecho com rótulo amigável (`ACEITO`, `NEGADO` ou `EM_ANDAMENTO`) a partir dos campos já persistidos no caso.
- Atualizar projeção de dados da listagem para incluir o desfecho sem alterar o workflow clínico existente.
- Adicionar/ajustar testes de integração da página de dashboard cobrindo renderização da nova coluna.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `case-thread-monitoring-dashboard`: a lista de casos passa a incluir, além de identificador/status/última atividade, uma coluna de desfecho operacional aceito/negado (com fallback para em andamento quando ainda não decidido).

## Impact

- Código potencialmente afetado:
  - `src/triage_automation/application/ports/case_repository_port.py`
  - `src/triage_automation/infrastructure/db/case_repository.py`
  - `src/triage_automation/infrastructure/http/templates/dashboard/partials/cases_list_fragment.html`
  - `src/triage_automation/infrastructure/http/dashboard_router.py`
- Testes potencialmente afetados:
  - `tests/integration/test_dashboard_pages.py`
- Sem necessidade de nova migração de banco (reuso de colunas já existentes como `doctor_decision` e `appointment_status`).

# Dashboard Reader Full Content and PDF Toggle

## Why

No detalhe de caso do dashboard, usuários `reader` hoje não conseguem acessar conteúdo completo dos eventos, incluindo o texto extraído do PDF. Além disso, no modo "Fluxo por Etapas" não existe acesso rápido ao relatório extraído no card superior, o que força troca de visualização e aumenta atrito operacional.

## What Changes

- Permitir que usuários `reader` também visualizem conteúdo completo dos eventos no modo "Histórico Completo" (mesmo comportamento hoje disponível para `admin`).
- Adicionar no modo "Fluxo por Etapas" um botão no card superior "Detalhe do Caso" para exibir/ocultar o texto do "relatório pdf extraído".
- Reaproveitar o texto já persistido no banco (evento `pdf_report_extracted`), sem reextração do arquivo PDF.
- Manter o relatório oculto por padrão e expandir/recolher o conteúdo no mesmo card ao clicar no botão.
- Ajustar testes de integração do dashboard para cobrir a nova autorização de leitura completa para `reader` e a renderização do botão colapsável no fluxo por etapas.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `case-thread-monitoring-dashboard`: o detalhe de caso passa a permitir conteúdo completo também para `reader` no modo "Histórico Completo" e passa a expor, no modo "Fluxo por Etapas", um controle de exibir/ocultar relatório PDF extraído no card superior.

## Impact

- Código potencialmente afetado:
  - `src/triage_automation/infrastructure/http/dashboard_router.py`
  - `src/triage_automation/infrastructure/http/templates/dashboard/case_detail.html`
- Testes potencialmente afetados:
  - `tests/integration/test_dashboard_pages.py`
- Sem mudança de API pública externa e sem necessidade de migração de banco de dados.

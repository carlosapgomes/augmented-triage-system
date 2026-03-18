# Room-4 window-only summary metrics

## Why

A mensagem periódica da Room-4 exibe um cabeçalho explícito de `Período`, mas hoje mistura métricas que respeitam a janela com contadores de backlog global atual. Isso induz leitura incorreta, porque o operador tende a interpretar todos os números como pertencentes ao mesmo intervalo.

## What Changes

- Fazer a mensagem periódica da Room-4 exibir apenas métricas coerentes com a janela resumida.
- Remover do corpo da mensagem os contadores de backlog global (`Casos em andamento`, `Aguardando Sala 2/3/1`, `Pendentes no ramo vinda imediata`).
- Preservar o dashboard como superfície de exploração para backlog e filtros amplos.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `room4-supervisor-periodic-summary`: o resumo publicado na Room-4 passa a conter somente métricas da janela periódica informada no cabeçalho.

## Impact

- Código afetado:
  - `src/triage_automation/application/services/post_room4_summary_service.py`
- Testes afetados:
  - `tests/unit/test_post_room4_summary_service.py`
- Comportamento afetado:
  - a Room-4 deixa de exibir backlog global em uma mensagem que representa um período delimitado.

# Room-4 summary period copy

## Why

A mensagem periódica da Room-4 hoje repete a referência temporal em duas linhas, incluindo UTC e o nome explícito do timezone. Para o uso operacional local isso gera ruído e reduz clareza, porque a equipe precisa apenas do período exibido no horário local já adotado pela operação.

## What Changes

- Simplificar o cabeçalho temporal da mensagem de resumo da Room-4 para uma única linha com o rótulo `Período`.
- Remover da mensagem publicada a linha em UTC e a exibição textual do nome do timezone.
- Preservar a conversão da janela para o horário local configurado e manter todas as métricas atuais sem alteração.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `room4-supervisor-periodic-summary`: o resumo publicado na Room-4 passa a exibir uma única referência temporal local, sem espelho UTC nem menção textual ao timezone.

## Impact

- Código afetado:
  - `src/triage_automation/application/services/post_room4_summary_service.py`
- Testes afetados:
  - `tests/unit/test_post_room4_summary_service.py`
- Comportamento afetado:
  - a mensagem publicada na Room-4 passa a mostrar apenas `Período: <início> → <fim>` em horário local.

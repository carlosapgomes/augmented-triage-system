# Room-3 pediatric request context

## Why

Casos pediátricos já carregam a sinalização `pediatric_flag` no payload estruturado e essa informação aparece corretamente na Room-2 e na mensagem final da Room-1. No entanto, a primeira mensagem enviada para a Room-3 (`room3_request`) não expõe esse contexto, o que faz a equipe de agendamento perder um dado operacional importante.

## What Changes

- Propagar a sinalização pediátrica para a mensagem `room3_request`.
- Preservar o template puro de resposta da Room-3 sem mudanças de parsing.
- Cobrir o comportamento com testes unitários e de integração.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `room3-scheduling-request-context`: a primeira mensagem enviada para a Room-3 passa a exibir `paciente pediátrico: sim` quando o caso for pediátrico.

## Impact

- Código afetado:
  - `src/triage_automation/application/services/post_room3_request_service.py`
  - `src/triage_automation/infrastructure/matrix/message_templates.py`
- Testes afetados:
  - `tests/unit/test_room1_room3_message_templates.py`
  - `tests/integration/test_post_room3_request.py`
- Comportamento afetado:
  - a Room-3 recebe o mesmo contexto pediátrico já exibido nos outros pontos do fluxo.

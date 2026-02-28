# Room-3 Threaded Bot Messages

## Why

No fluxo atual, o bot publica a mensagem de solicitação e a mensagem de template do Room-3 como eventos soltos. Isso quebra o contexto operacional porque o time de agendamento perde a referência encadeada em uma única thread.

## What Changes

- Encadear as mensagens automáticas iniciais de Room-3 na mesma thread.
- Manter a solicitação de Room-3 como mensagem raiz.
- Publicar o template de resposta do agendamento como reply da solicitação raiz.
- Persistir `reply_to_event_id` do template no transcript para refletir o encadeamento real.
- Atualizar testes de integração do post de Room-3 e fakes de Matrix usados nesse fluxo.

## Capabilities

### New Capabilities

- `room3-threaded-bot-messages`: Garante que as mensagens iniciais do bot em Room-3 (`room3_request` e `room3_template`) sejam publicadas de forma encadeada na mesma thread.

### Modified Capabilities

- Nenhuma.

## Impact

- Código afetado: `PostRoom3RequestService` e o contrato de porta Matrix desse serviço.
- Persistência afetada: campo `reply_to_event_id` no transcript de `room3_template`.
- Testes afetados: integração de `post_room3_request` e eventuais fakes que assumem apenas `send_text`.

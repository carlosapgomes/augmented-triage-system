# Room-3 Threaded Bot Messages Design

## Context

O serviço `PostRoom3RequestService` publica duas mensagens no Room-3: a solicitação (`room3_request`) e o template (`room3_template`). Hoje ambas são publicadas com `send_text`, resultando em mensagens soltas, sem vínculo de thread.

A infraestrutura Matrix já suporta replies via `reply_text` com `m.relates_to.m.in_reply_to`, e o Room-2 já usa esse padrão. Portanto, a mudança necessária é de orquestração no serviço de aplicação do Room-3, mantendo a arquitetura `adapters -> application -> domain -> infrastructure`.

## Goals / Non-Goals

**Goals:**

- Garantir que as mensagens iniciais do bot no Room-3 fiquem encadeadas na mesma thread.
- Manter `room3_request` como evento raiz e publicar `room3_template` como reply desse evento.
- Persistir `reply_to_event_id` do `room3_template` no transcript para refletir o encadeamento real.
- Preservar o comportamento atual de parsing de replies do agendamento para `room3_request` e `room3_template`.

**Non-Goals:**

- Não alterar o parser de resposta do agendamento (`scheduler_parser`).
- Não alterar o conteúdo textual dos templates de Room-3.
- Não alterar transições de status (`DOCTOR_ACCEPTED` -> `R3_POST_REQUEST` -> `WAIT_APPT`).

## Decisions

### Decision 1: Expandir porta do serviço para suportar reply explícito

- Escolha: adicionar `reply_text` no `MatrixRoomPosterPort` de `PostRoom3RequestService`.
- Racional: mantém a decisão de threading no nível de aplicação, sem inserir regra de negócio no adapter.
- Alternativa considerada: manter só `send_text` e encadear no adapter automaticamente para Room-3.
- Motivo da rejeição: criaria acoplamento implícito por sala dentro da infraestrutura e pioraria previsibilidade dos testes.

### Decision 2: Encadear apenas o template ao request raiz

- Escolha: `room3_request` permanece `send_text`; `room3_template` vira `reply_text(event_id=request_event_id)`.
- Racional: preserva um único root claro e resolve o problema operacional de thread fragmentada com a menor mudança possível.
- Alternativa considerada: responder ao último evento da thread de forma encadeada progressiva.
- Motivo da rejeição: não traz benefício prático nesse fluxo de duas mensagens e aumenta chance de regressão.

### Decision 3: Atualizar persistência observável no transcript

- Escolha: registrar `reply_to_event_id=request_event_id` na linha de transcript de `room3_template`.
- Racional: mantém consistência entre evento Matrix enviado e dados de observabilidade/auditoria no banco.
- Alternativa considerada: manter `reply_to_event_id` nulo no transcript.
- Motivo da rejeição: perderia rastreabilidade de thread, justamente o problema a ser corrigido.

## Risks / Trade-offs

- [Risco] Fakes de testes que implementam somente `send_text` podem quebrar ao adicionar `reply_text` na porta do serviço.
  - Mitigação: atualizar fakes e asserts em testes de integração diretamente impactados (`test_post_room3_request.py`).
- [Risco] Regressão em contratos de transcript esperados por testes.
  - Mitigação: ajustar asserts para `reply_to_event_id` do `room3_template` e executar suíte alvo de Room-3.
- [Trade-off] Maior rigidez no contrato de porta Matrix do serviço.
  - Mitigação: manter assinatura alinhada ao `MatrixRuntimeClientPort` já existente no runtime.

## Migration Plan

1. Atualizar testes de integração de Room-3 para refletir threading esperado (red).
2. Implementar mudança no serviço e na porta para usar `reply_text` no template (green).
3. Validar `pytest`, `ruff`, `mypy` nos caminhos alterados.
4. Não requer migração de banco nem rollout gradual; mudança é compatível e idempotente.

## Open Questions

- Não há questões abertas para este slice.

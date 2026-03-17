# Design

## Context

O serviço `PostRoom4SummaryService` renderiza hoje duas linhas de referência temporal no corpo da mensagem: uma linha local com `Janela (<timezone>)` e outra linha `Janela UTC`. O ajuste pedido altera apenas a cópia apresentada ao usuário final da Room-4, sem mudar cálculo de janela, scheduler, persistência de dispatch ou agregação de métricas.

## Goals / Non-Goals

**Goals:**

- Renderizar uma única linha temporal no resumo da Room-4 com o rótulo `Período`.
- Manter o horário exibido convertido para o timezone operacional configurado.
- Preservar todas as métricas e a estrutura restante da mensagem.

**Non-Goals:**

- Alterar cálculo de cutoff, timezone configurado ou payload UTC interno.
- Mudar regras de métricas, idempotência ou agendamento.
- Atualizar documentação operacional, já que o comportamento interno de timezone não muda.

## Decisions

### Decision 1: Ajustar apenas o renderer da mensagem

- Escolha: concentrar a mudança em `render_room4_summary_message`, que já é o ponto responsável pela cópia final do resumo.
- Racional: o pedido é puramente de apresentação; manter a mudança nesse ponto reduz risco e evita impacto na arquitetura `application -> domain -> infrastructure`.
- Alternativas consideradas:
  - alterar payloads de scheduler/worker para carregar texto pronto.
    - Rejeitada por misturar apresentação com orquestração.
  - manter a linha local atual e apenas remover UTC.
    - Rejeitada porque o termo `Janela` e a menção textual ao timezone continuam desalinhados com a linguagem desejada.

### Decision 2: Preservar a conversão local e ocultar a referência textual ao timezone

- Escolha: continuar convertendo `window_start` e `window_end` para o timezone configurado antes de formatar a linha `Período`, sem expor o nome do timezone no corpo.
- Racional: atende ao pedido de usar o horário local operacional sem poluir a mensagem com detalhes técnicos desnecessários.

## Risks / Trade-offs

- [Risk] A mensagem deixa de expor a referência UTC usada internamente para troubleshooting manual.
  - Mitigação: a identidade da janela continua preservada no job payload, no dispatch auditável e nos testes; apenas a cópia visível ao usuário é simplificada.

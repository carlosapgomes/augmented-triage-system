# Design

## Context

`render_room4_summary_message` é o ponto que decide a cópia final publicada na Room-4. O aggregate atual ainda fornece tanto métricas temporais quanto backlog global, mas a confusão reportada vem da mensagem publicada, que apresenta todas as linhas sob um cabeçalho de período único.

## Goals / Non-Goals

**Goals:**

- Garantir que a mensagem visível da Room-4 contenha apenas métricas compatíveis com a janela exibida.
- Corrigir a semântica do resumo sem alterar o papel do dashboard.
- Fazer a mudança por TDD, com risco baixo e escopo mínimo.

**Non-Goals:**

- Redesenhar o dashboard ou seus filtros.
- Alterar o cálculo interno do backlog usado por outras superfícies.
- Reestruturar o scheduler da Room-4.

## Decisions

### Decision 1: Corrigir primeiro a cópia publicada

- Escolha: remover da renderização da Room-4 as linhas que representam snapshot/backlog global.
- Racional: resolve a confusão operacional imediatamente, com mudança localizada e reversível.

### Decision 2: Preservar o aggregate interno neste slice

- Escolha: neste primeiro slice, não remover campos do DTO nem do query adapter; apenas deixar de renderizá-los na mensagem.
- Racional: reduz risco de regressão e mantém o slice pequeno, focado no comportamento visível que motivou o ajuste.

## Risks / Trade-offs

- [Risk] O aggregate interno continuará calculando métricas não exibidas.
  - Mitigação: aceitar esse custo temporariamente neste slice e avaliar limpeza posterior apenas se houver ganho real.

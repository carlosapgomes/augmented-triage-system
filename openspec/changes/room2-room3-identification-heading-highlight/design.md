# Design: Room-2 e Room-3 Identification Heading Highlight

## Context

O fluxo já publica identificação humana (`no. ocorrência` e `paciente`) nas mensagens operacionais, mas sem destaque explícito no primeiro post textual de cada sala. Em cenários com alto volume, isso dificulta a localização rápida do caso no histórico.

A Sala 2 possui mensagem com `formatted_body` HTML (resumo técnico), enquanto a Sala 3 usa texto puro no primeiro post de solicitação de agendamento. A solução deve manter a arquitetura atual e não alterar semântica de negócio.

## Goals / Non-Goals

**Goals:**

- Evidenciar visualmente as duas linhas de identificação no primeiro post textual da Sala 2 e da Sala 3.
- Manter o conteúdo textual existente, alterando apenas a apresentação (Markdown/HTML).
- Preservar compatibilidade com testes e contratos de parser das mensagens estruturadas.

**Non-Goals:**

- Não alterar templates de resposta estruturada (copiar/colar) usados para parsing de decisão/agendamento.
- Não alterar workflow, status de caso ou regras clínicas.
- Não introduzir novas dependências de renderização Markdown.

## Decisions

### Decision 1: Introduzir helper dedicado para identificação destacada em Markdown

- Escolha: criar um builder específico para renderizar identificação como headings Markdown (`##`) e aplicá-lo apenas nos primeiros posts da Sala 2 (resumo técnico) e Sala 3 (solicitação de agendamento).
- Racional: evita impacto global em templates que dependem de formato estrito sem heading.
- Alternativa considerada: alterar `build_human_identification_block` globalmente.
- Motivo da rejeição: poderia quebrar contratos em mensagens de ack/template e alterar comportamento não solicitado.

### Decision 2: Criar versão HTML destacada para o resumo da Sala 2

- Escolha: no `formatted_body` da Sala 2, renderizar identificação em `<h2>` para refletir destaque equivalente ao Markdown.
- Racional: clientes que priorizam HTML devem perceber o mesmo destaque.
- Alternativa considerada: manter `<p>` no HTML e destacar apenas no body Markdown.
- Motivo da rejeição: criaria inconsistência visual entre renderizações.

## Risks / Trade-offs

- [Risco] Diferença de renderização entre clientes Matrix para headings Markdown no body puro.
  - Mitigação: aplicar também destaque em HTML no caso da Sala 2 e validar presença textual nos testes.

- [Trade-off] Headings adicionam maior proeminência visual e ocupam mais espaço vertical.
  - Mitigação: limitar mudança somente às duas linhas de identificação solicitadas.

## Migration Plan

1. Escrever/ajustar testes unitários para exigir prefixo de heading nas linhas de identificação da Sala 2 (resumo) e Sala 3 (request).
2. Implementar helper de identificação destacada em Markdown e HTML.
3. Aplicar helper apenas nos templates alvo.
4. Atualizar testes de integração que validam conteúdo das mensagens geradas.
5. Rodar `pytest` alvo, `ruff`, `mypy` e `markdownlint` dos artefatos OpenSpec alterados.

Rollback:

- Reverter alterações em `message_templates.py` e testes associados, retornando ao bloco de identificação sem heading.

## Open Questions

- Nenhuma no momento.

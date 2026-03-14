# Room-2 e Room-3 Identification Heading Highlight

## Why

Nos primeiros posts automáticos da Sala 2 e da Sala 3, as linhas de identificação (`no. ocorrência` e `paciente`) ficam visualmente misturadas com o restante do conteúdo quando há muitas mensagens no histórico. Isso reduz a leitura rápida do contexto do caso no cliente Matrix.

## What Changes

- Destacar visualmente, em Markdown, as duas primeiras linhas de identificação (`no. ocorrência` e `paciente`) no primeiro post textual da Sala 2 e da Sala 3.
- Garantir o mesmo destaque no `formatted_body` HTML da mensagem de resumo da Sala 2, para manter consistência entre clientes que preferem HTML formatado.
- Preservar contratos existentes de parser e conteúdo obrigatório das mensagens (sem alterar campos nem semântica).

## Capabilities

### New Capabilities

- `room2-room3-identification-visual-emphasis`: padroniza destaque visual da identificação humana no primeiro post das Salas 2 e 3.

### Modified Capabilities

- Nenhuma.

## Impact

- Código potencialmente afetado:
  - `src/triage_automation/infrastructure/matrix/message_templates.py`
- Testes potencialmente afetados:
  - `tests/unit/test_room2_message_templates.py`
  - `tests/unit/test_room1_room3_message_templates.py`
  - `tests/integration/test_post_room2_widget.py`
  - `tests/integration/test_post_room3_request.py`
- Sem impacto em migração de banco, estado de workflow, ou contratos de API externos.

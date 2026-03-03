# Sala 2: remover conduta e expandir motivo objetivo no resumo técnico

## Why

O resumo técnico enviado pelo bot na Sala 2 está incluindo o bloco `Conduta sugerida`, que extrapola o posicionamento esperado do bot para esta etapa (sugerir `aceitar` ou `negar` com justificativa). Ao mesmo tempo, o bloco `Motivo objetivo` está sendo truncado por limites muito curtos, reduzindo clareza para a decisão médica.

## What Changes

- Remover o bloco `Conduta sugerida` da mensagem de resumo técnico (mensagem II) publicada na Sala 2, em texto Markdown e em `formatted_body` HTML.
- Rebalancear o layout da mensagem para usar o espaço vertical liberado no `Motivo objetivo`.
- Ajustar regras de truncamento/limite de `Motivo objetivo` para permitir justificativa mais completa, mantendo objetividade e coerência com a decisão sugerida.
- Atualizar testes unitários e de integração que validam estrutura, ordem de seções e limites de conteúdo da mensagem da Sala 2.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `room2-concise-medical-opinion-message`: altera layout obrigatório do resumo da Sala 2 ao remover `Conduta sugerida` e atualizar restrições de extensão para `Motivo objetivo`.
- `room2-structured-reply-decision`: atualiza o contrato da mensagem II do combo de decisão para refletir o novo conjunto de blocos exibidos na Sala 2.

## Impact

- Código potencialmente afetado:
  - `src/triage_automation/infrastructure/matrix/message_templates.py`
- Testes potencialmente afetados:
  - `tests/unit/test_room2_message_templates.py`
  - `tests/integration/test_post_room2_widget.py`
- Sem impacto esperado em workflow de estados, persistência de banco, parser de resposta médica estruturada ou APIs externas.

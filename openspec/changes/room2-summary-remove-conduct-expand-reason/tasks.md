# Tasks

## 1. Ajustar contrato e testes do resumo técnico da Sala 2

- [x] 1.1 Atualizar testes unitários de `tests/unit/test_room2_message_templates.py` para falhar (red) quando `Conduta sugerida` ainda aparecer no body Markdown e no `formatted_body` HTML.
- [x] 1.2 Atualizar testes unitários para exigir novo conjunto/ordem de blocos obrigatórios da mensagem II sem `Conduta sugerida`.
- [x] 1.3 Atualizar testes unitários para validar expansão de `Motivo objetivo` (sem truncamento agressivo para motivos dentro do novo limite).
- [x] 1.4 Atualizar testes de integração em `tests/integration/test_post_room2_widget.py` para refletir o novo contrato textual da mensagem II.

## 2. Implementar remoção de conduta e expansão do motivo

- [x] 2.1 Remover renderização da seção `Conduta sugerida` dos builders de resumo da Sala 2 em `src/triage_automation/infrastructure/matrix/message_templates.py` (Markdown e HTML).
- [x] 2.2 Ajustar helper de `Motivo objetivo` para priorizar justificativa completa e objetiva, reduzindo truncamento em relação ao limite atual.
- [x] 2.3 Preservar coerência entre `Decisão sugerida`, `Suporte recomendado` e `Motivo objetivo`, mantendo comportamento determinístico.
- [x] 2.4 Garantir que a frase de prioridade emergente (quando aplicável) continue coberta no `Motivo objetivo` após remoção da conduta.

## 3. Validar qualidade e registrar evidências

- [x] 3.1 Executar testes alvo do slice (red/green) com `uv run pytest tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py -q`.
- [x] 3.2 Executar `uv run ruff check src/triage_automation/infrastructure/matrix/message_templates.py tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py`.
- [x] 3.3 Executar `uv run mypy src/triage_automation/infrastructure/matrix/message_templates.py tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py`.
- [x] 3.4 Executar `markdownlint-cli2 "openspec/changes/room2-summary-remove-conduct-expand-reason/**/*.md"` e registrar eventuais observações.

## Notes

- Evidência TDD (red):
  - `uv run pytest tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py -q`
  - Resultado: `7 failed, 25 passed` (falhas esperadas antes da implementação da remoção de conduta e expansão do motivo).
- Evidência TDD (green):
  - `uv run pytest tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py -q`
  - Resultado: `32 passed`.
- Qualidade estática:
  - `uv run ruff check src/triage_automation/infrastructure/matrix/message_templates.py tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py`
  - `uv run mypy src/triage_automation/infrastructure/matrix/message_templates.py tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py`
  - Resultado: sem erros.
- Lint de Markdown OpenSpec:
  - `markdownlint-cli2 "openspec/changes/room2-summary-remove-conduct-expand-reason/**/*.md"`
  - Resultado: `0 error(s)`.

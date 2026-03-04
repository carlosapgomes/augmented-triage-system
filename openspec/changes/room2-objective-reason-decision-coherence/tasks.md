# Tasks

## 1. Atualizar contrato por testes (TDD red)

- [x] 1.1 Ajustar testes unitários de `tests/unit/test_room2_message_templates.py` para falhar quando `Motivo objetivo` de `deny` contiver frase de aceite ou menção de suporte.
- [x] 1.2 Adicionar/ajustar testes unitários para validar derivação determinística das causas de negativa na ordem: exclusão EDA, pendência laboratorial obrigatória, ECG obrigatório ausente, fallback de segurança.
- [x] 1.3 Adicionar/ajustar testes unitários para validar limite de até 2 causas no `Motivo objetivo` de `deny`, com marcador equivalente a `e outras pendências críticas` quando houver causas adicionais.
- [x] 1.4 Ajustar testes unitários para validar que, em `accept`, `Motivo objetivo` usa apenas frase curta de aceite com suporte e não adiciona linhas explicativas extras.
- [x] 1.5 Ajustar testes unitários para garantir que `rationale.short_reason` conflitante não vaze contradição no resumo renderizado.
- [x] 1.6 Ajustar testes de integração em `tests/integration/test_post_room2_widget.py` para refletir o novo contrato textual de coerência entre `Decisão sugerida` e `Motivo objetivo`.
- [x] 1.7 Executar `uv run pytest tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py -q` e registrar evidência de falha inicial (red).

## 2. Implementar regras determinísticas do motivo objetivo na Sala 2

- [x] 2.1 Refatorar `src/triage_automation/infrastructure/matrix/message_templates.py` para bifurcar construção de `Motivo objetivo` por decisão final (`deny` vs `accept`).
- [ ] 2.2 Implementar composição de negativa com causas explícitas e auditáveis, priorizando sinais clínicos/precheck definidos no spec.
- [ ] 2.3 Garantir que, em `deny`, o `Motivo objetivo` não inclua texto de suporte e não reutilize texto livre contraditório de `rationale.short_reason`.
- [ ] 2.4 Garantir que, em `accept`, o `Motivo objetivo` seja frase curta com suporte (ou sem suporte) e sem explicações adicionais.
- [ ] 2.5 Ajustar regra de prioridade emergente para aparecer somente quando o caso for de sangramento instável com sugestão final `accept`.
- [ ] 2.6 Preservar renderização consistente entre Markdown e HTML (`formatted_body`) para todas as novas regras de `Motivo objetivo`.

## 3. Validar qualidade, registrar evidências e preparar handoff

- [ ] 3.1 Executar suíte alvo green: `uv run pytest tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py -q`.
- [ ] 3.2 Executar `uv run ruff check src/triage_automation/infrastructure/matrix/message_templates.py tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py`.
- [ ] 3.3 Executar `uv run mypy src/triage_automation/infrastructure/matrix/message_templates.py tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py`.
- [ ] 3.4 Executar `markdownlint-cli2 "openspec/changes/room2-objective-reason-decision-coherence/**/*.md"`.
- [ ] 3.5 Registrar resultados, observações e eventuais desvios na seção `Notes` do próprio `tasks.md`.

## Notes

- Decisão de produto confirmada: quando a decisão final for `deny`, o texto do `Motivo objetivo` deve focar exclusivamente no motivo objetivo da recusa.
- Decisão de produto confirmada: em negativas com múltiplas pendências, listar até 2 causas explícitas e resumir excedentes com marcador curto.
- Decisão de produto confirmada: frase de prioridade emergente não deve coexistir com mensagem final de negativa.
- Evidência TDD (red) consolidada do bloco 1:
  - `uv run pytest tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py -q`
  - Resultado: `10 failed, 29 passed` (falhas esperadas antes da implementação das regras determinísticas de `Motivo objetivo`).

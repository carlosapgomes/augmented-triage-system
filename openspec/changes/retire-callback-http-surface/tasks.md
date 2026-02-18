# Tasks

## 1. Remove HTTP Decision Surface

- [x] 1.1 Remover a rota `POST /callbacks/triage-decision` de `apps/bot_api/main.py` e limpar imports/dependências de callback HMAC vinculadas a decisão médica.
- [x] 1.2 Remover o `build_widget_router` do wiring do `bot-api` e eliminar dependências exclusivas do fluxo widget HTTP de decisão.
- [x] 1.3 Remover endpoints e assets estáticos legados de widget Room-2 (`/widget/room2*`) que não fazem mais parte da superfície operacional.

## 2. Align Runtime Documentation

- [x] 2.1 Atualizar `docs/runtime-smoke.md` para remover validações de callback/túnel e manter apenas fluxo Matrix structured reply.
- [x] 2.2 Atualizar `docs/setup.md`, `docs/architecture.md` e `README.md` para refletir runtime Matrix-only sem fallback HTTP de decisão.
- [x] 2.3 Revisar variáveis/configs documentadas e remover referências legadas de callback/widget público para decisão médica.

## 3. Update Tests and Contracts

- [x] 3.1 Ajustar/criar testes de integração do `bot-api` validando ausência de endpoints legados (`/callbacks/triage-decision` e `/widget/room2*`).
- [x] 3.2 Atualizar testes que dependiam do caminho callback/widget para validar o comportamento equivalente no fluxo Matrix-only.
- [x] 3.3 Garantir que os testes do fluxo Room-2 structured reply permaneçam verdes sem regressão de estado/idempotência.

## 4. Verify and Closeout

- [x] 4.1 Executar quality gates do slice (`uv run pytest <targeted>`, `uv run ruff check <changed-paths>`, `uv run mypy <changed-paths>`).
- [x] 4.2 Executar validação de Markdown (`markdownlint-cli2 "<changed-markdown-paths>"`) nos artefatos alterados.
- [x] 4.3 Validar bootstrap do runtime (`bot-api` + `bot-matrix` + `worker`) com checklist Matrix-only e registrar notas de rollback/impacto no fechamento da change.

### 4.3 Closeout Notes

- Runtime bootstrap checklist (Matrix-only) executado com:
  `uv run pytest tests/integration/test_bot_api_runtime.py tests/integration/test_bot_matrix_room1_listener_runtime.py tests/integration/test_worker_runtime_service_wiring.py tests/integration/test_worker_boot_reconciliation.py -q`
  (`9 passed`).
- Room-2 structured reply readiness revalidado com:
  `uv run pytest tests/integration/test_room2_reply_flow.py -q` (`16 passed`).
- Impacto operacional confirmado: decisão médica via HTTP callback/widget não existe mais na superfície runtime; apenas resposta estruturada Matrix permanece suportada.
- Rollback definido: reverter commits da change `retire-callback-http-surface` restaura rota callback/widget e contratos legados sem migração de dados (rollback apenas de código/docs).

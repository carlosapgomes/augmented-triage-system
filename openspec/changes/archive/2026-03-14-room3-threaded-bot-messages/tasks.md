# Tasks

## 1. Room-3 Thread Chaining

- [x] 1.1 Atualizar testes de integração de `post_room3_request` para exigir `room3_template` como reply do `room3_request` e `reply_to_event_id` persistido no transcript.
- [x] 1.2 Alterar `PostRoom3RequestService` para publicar `room3_template` com `reply_text(event_id=request_event_id)` e registrar o vínculo no transcript/auditoria.
- [x] 1.3 Executar validações do slice (`uv run pytest` alvo, `uv run ruff check` caminhos alterados, `uv run mypy` caminhos alterados, `markdownlint-cli2` nos artefatos OpenSpec alterados) e registrar limitações, se houver.

## Notes

- Validações executadas com sucesso:
  - `uv run pytest tests/integration/test_post_room3_request.py -q`
  - `uv run pytest tests/integration/test_room3_scheduler_reply_flow.py -q`
  - `uv run ruff check src/triage_automation/application/services/post_room3_request_service.py tests/integration/test_post_room3_request.py`
  - `uv run mypy src/triage_automation/application/services/post_room3_request_service.py`
  - `markdownlint-cli2 \"openspec/changes/room3-threaded-bot-messages/proposal.md\" \"openspec/changes/room3-threaded-bot-messages/design.md\" \"openspec/changes/room3-threaded-bot-messages/specs/**/*.md\" \"openspec/changes/room3-threaded-bot-messages/tasks.md\"`

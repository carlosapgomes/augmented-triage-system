# Tasks

## 1. Destacar identificação no primeiro post das Salas 2 e 3

- [x] 1.1 Ajustar testes unitários/integrados para exigir destaque Markdown nas linhas `no. ocorrência` e `paciente` no `room2_case_summary` e no `room3_request` (incluindo HTML formatado da Sala 2).
- [x] 1.2 Implementar o destaque no template em `src/triage_automation/infrastructure/matrix/message_templates.py` sem alterar contratos estruturais de parser.
- [x] 1.3 Executar validações do slice (`uv run pytest` alvo, `uv run ruff check`, `uv run mypy`, `markdownlint-cli2` nos artefatos OpenSpec alterados) e registrar resultados.

## Notes

- Evidência TDD (red):
  - `uv run pytest tests/unit/test_room1_room3_message_templates.py::test_build_room3_request_message_prioritizes_human_identification_without_uuid tests/unit/test_room2_message_templates.py::test_build_room2_case_summary_message_avoids_full_flattened_dump tests/unit/test_room2_message_templates.py::test_build_room2_case_summary_formatted_html_includes_sections tests/integration/test_post_room2_widget.py::test_post_room2_widget_includes_prior_and_moves_to_wait_doctor tests/integration/test_post_room3_request.py::test_room3_request_posts_request_and_template_and_moves_wait_appt -q`
  - Resultado: `5 failed` (asserts aguardando headings de identificação).
- Evidência TDD (green):
  - Mesmo comando após implementação.
  - Resultado: `5 passed`.
- Cobertura de regressão do slice:
  - `uv run pytest tests/unit/test_room1_room3_message_templates.py tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py tests/integration/test_post_room3_request.py -q`
  - Resultado: `40 passed`.
- Qualidade estática:
  - `uv run ruff check src/triage_automation/infrastructure/matrix/message_templates.py tests/unit/test_room1_room3_message_templates.py tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py tests/integration/test_post_room3_request.py`
  - `uv run mypy src/triage_automation/infrastructure/matrix/message_templates.py tests/unit/test_room1_room3_message_templates.py tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py tests/integration/test_post_room3_request.py`
- Lint Markdown OpenSpec:
  - `markdownlint-cli2 "openspec/changes/room2-room3-identification-heading-highlight/*.md" "openspec/changes/room2-room3-identification-heading-highlight/specs/**/*.md"`
  - Resultado: `0 error(s)`.

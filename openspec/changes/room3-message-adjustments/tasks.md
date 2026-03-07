# room3-message-adjustments Tasks

## 1. Configuration

- [x] 1.1 Add `TRIAGE_DEFAULT_TIMEZONE` to `Settings` class in `src/triage_automation/infrastructure/config/settings.py` with default `America/Bahia`
- [x] 1.2 Add timezone validation at startup to fail fast on invalid IANA timezone identifiers
- [x] 1.3 Update `.env.example` with `TRIAGE_DEFAULT_TIMEZONE` documentation

## 2. Data Layer - Doctor Display Name

- [x] 2.1 Add `doctor_display_name: str | None` field to `CaseDoctorDecisionSnapshot` dataclass in `src/triage_automation/application/ports/case_repository_port.py`
- [x] 2.2 Update `get_case_doctor_decision_snapshot()` in `src/triage_automation/infrastructure/db/case_repository.py` to JOIN with `case_matrix_message_transcripts` and retrieve `sender_display_name` where `message_type = 'room2_doctor_reply'`

## 3. Domain Layer - Timezone Support

- [x] 3.1 Update `scheduler_parser.py` to accept timezone as parameter instead of hardcoded `_BRT`
- [x] 3.2 Ensure parser continues to accept both `DD-MM-YYYY HH:MM` and `DD/MM/YYYY HH:MM` formats

## 4. Message Templates - Room-3 Request Message

- [x] 4.1 Add `doctor_display_name: str | None = None` parameter to `build_room3_request_message()` in `message_templates.py`
- [x] 4.2 Add line `aceito por: <name>` below `exame solicitado` in the message body, using fallback `"não informado"` when name is unavailable
- [x] 4.3 Add `doctor_display_name` parameter to `build_room3_request_message_formatted_html()` if it exists

## 5. Message Templates - Room-3 Reply Template

- [x] 5.1 Update `build_room3_reply_template_message()` to change `data_hora: DD-MM-YYYY HH:MM BRT` to `data_hora: DD/MM/YYYY HH:MM`
- [x] 5.2 Fix `instrucoes` to `instruções` in the template
- [x] 5.3 Update `build_room3_reply_template_formatted_html()` if it exists with same changes

## 6. Message Templates - Room-3 Ack Message

- [x] 6.1 Update `build_room3_ack_message()` to change `Reaja com +1 para confirmar.` to `Reaja com +1 para confirmar ciência do encerramento.`

## 7. Message Templates - Room-3 Error Reprompt

- [x] 7.1 Update `build_room3_invalid_format_reprompt()` to change `data_hora: DD-MM-YYYY HH:MM BRT` to `data_hora: DD/MM/YYYY HH:MM`
- [x] 7.2 Fix `instrucoes` to `instruções` in the reprompt template

## 8. Service Layer - PostRoom3RequestService

- [ ] 8.1 Update `post_request()` in `PostRoom3RequestService` to pass `snapshot.doctor_display_name` to `build_room3_request_message()`

## 9. Unit Tests

- [ ] 9.1 Add/update tests for `CaseDoctorDecisionSnapshot` with `doctor_display_name` field
- [ ] 9.2 Add/update tests for `build_room3_request_message()` with doctor name and fallback
- [ ] 9.3 Update tests for `build_room3_reply_template_message()` with new date format and corrected spelling
- [ ] 9.4 Update tests for `build_room3_ack_message()` with new confirmation text
- [ ] 9.5 Update tests for `build_room3_invalid_format_reprompt()` with new date format and corrected spelling
- [ ] 9.6 Add tests for timezone validation in settings
- [ ] 9.7 Update scheduler parser tests to verify both date formats still work with configurable timezone

## 10. Integration Tests

- [ ] 10.1 Update `test_room3_scheduler_reply_flow.py` to verify doctor name appears in request message
- [ ] 10.2 Add integration test for configurable timezone parsing

## 11. Documentation

- [ ] 11.1 Update `README.md` and `README.en.md` with `TRIAGE_DEFAULT_TIMEZONE` environment variable documentation

## 12. Verification

- [ ] 12.1 Run `uv run pytest tests/unit/test_room1_room3_message_templates.py tests/unit/test_scheduler_parser.py -v`
- [ ] 12.2 Run `uv run pytest tests/integration/test_room3_scheduler_reply_flow.py -v`
- [ ] 12.3 Run `uv run ruff check src/triage_automation/`
- [ ] 12.4 Run `uv run mypy src/triage_automation/`

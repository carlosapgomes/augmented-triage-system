# Room-2 copy/paste template tolerance tasks

- [x] 1.1 Make the Room-2 doctor decision parser ignore known bot-authored helper/context lines (`no. ocorrência`, `paciente`, `Modelo obrigatório`) and add regression tests for copy/pasted template and error-prompt replies.
- [x] 1.2 Run targeted Room-2 workflow verification to confirm strict rejection still applies to truly unknown labeled fields after the parser tolerance change.

## Notes

- Verification run: `uv run pytest tests/unit/test_doctor_decision_parser.py tests/unit/test_room2_reply_parser.py tests/integration/test_room2_reply_flow.py -k "ignores_copy_pasted or rejects_unknown_labeled_field or rejects_reply_with_unknown_labeled_field or typed_doctor_identity" -q`
- Result: copy/pasted helper-line replies are accepted, while truly unknown labeled fields and typed doctor identity fields still return `invalid_template` and do not mutate Room-2 state.

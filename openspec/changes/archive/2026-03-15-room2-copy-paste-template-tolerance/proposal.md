# Room-2 copy/paste template tolerance

## Why

Recent Room-2 doctor replies can fail with `invalid_template` even when the clinician copies the bot-provided template. The current parser treats helper/context lines such as `no. ocorrência`, `paciente`, and `Modelo obrigatório` as unknown structured fields, which breaks copy/paste UX and creates false negatives in a critical workflow.

## What Changes

- Allow the Room-2 doctor decision parser to ignore known non-decision helper/context lines that may appear above the structured reply fields.
- Preserve strict validation for true unknown structured fields outside the allowed ignore list.
- Add regression coverage proving that copy/pasted bot template text and copy/pasted error-model text are accepted when the decision fields themselves are valid.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `room2-structured-reply-decision`: tolerate known Room-2 helper/context lines during parsing without relaxing the strict contract for unknown fields.

## Impact

- Affected code: `src/triage_automation/domain/doctor_decision_parser.py`
- Affected tests: Room-2 parser unit coverage
- Affected behavior: Room-2 decision replies copied from bot-provided templates or error prompts will no longer fail due to known helper lines

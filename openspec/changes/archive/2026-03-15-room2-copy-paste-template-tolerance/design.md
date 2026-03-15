# Room-2 copy/paste template tolerance design

## Context

Room-2 uses a strict parser so free-form responses do not mutate workflow state. However, the bot also renders helper/context lines around the structured template, including patient identification and validation guidance. When clinicians paste those helper lines back into their reply, the parser currently rejects the message as `invalid_template`.

## Goals / Non-Goals

**Goals:**

- Preserve strict structured parsing for actual decision fields.
- Ignore only a small, explicit allowlist of known helper/context labels emitted by the bot.
- Add regression tests covering copy/paste of the Room-2 template and error prompt.

**Non-Goals:**

- Accept arbitrary new structured labels.
- Add support for misspelled support values.
- Redesign Room-2 message composition or workflow routing.

## Decisions

### Decision 1: Ignore known helper labels before field resolution

- **Choice:** treat selected labels as ignorable metadata lines during parsing: `no. ocorrência`, `paciente`, and `modelo obrigatório`.
- **Rationale:** these lines are bot-authored context, not user-entered business fields, and they appear in copy/paste flows.
- **Alternatives considered:**
  - Relax all unknown labels: rejected because it weakens the safety contract.
  - Remove helper lines from bot messages only: rejected because existing UX intentionally includes them and error prompts may still be copied.

### Decision 2: Keep unknown labeled fields strict

- **Choice:** continue raising `unknown_field` for any labeled line outside the supported decision fields and helper allowlist.
- **Rationale:** this preserves deterministic validation and avoids accidental acceptance of malformed structured input.

## Risks / Trade-offs

- **[Risk]** Future bot helper labels could be added without parser support and reintroduce copy/paste failures. → **Mitigation:** document the explicit allowlist in tests and extend it deliberately when templates change.
- **[Risk]** Overmatching helper labels could hide real user mistakes. → **Mitigation:** keep the allowlist narrow and normalized.

## Migration Plan

1. Add failing parser tests for copy/pasted template and error-prompt text.
2. Implement the narrow helper-label ignore list.
3. Run targeted verification and ship as a low-risk parser fix.
4. Roll back by reverting the parser/test change if unexpected parsing behavior appears.

## Open Questions

- None.

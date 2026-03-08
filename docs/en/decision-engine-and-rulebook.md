# Decision Engine and Rulebook

Language: [Portugues (BR)](../decision-engine-and-rulebook.md) | **English**

## Goal

This document explains how ATS makes decisions throughout the triage flow,
with a focus on maintainability and predictable evolution.

The goal is to avoid a common misunderstanding: assuming clinical decisions come
from prompts. In ATS, prompts guide extraction and suggestion, while critical
operational rules are deterministic in code, and final clinical decision remains
with the physician.

## Decision-engine principles

1. Prompts are extraction/structure contracts, not final rule authority.
2. Deterministic rules are implemented in domain/application policy code.
3. Critical outputs must stay auditable (`reason_code`, `reason_text`, evidence).
4. Final clinical decision is human (Matrix structured reply in Room-2).

## End-to-end flow (narrative)

1. **Intake and initial extraction**
   - A case enters via Room-1 with a PDF.
   - Worker extracts text and calls LLM1 to structure data.

1. **Deterministic scope pre-processing**
   - The system evaluates `preop_screening.exam_type`.
   - If `non_eda|unknown`, it closes as `manual_review_required`, posts closure
     in Room-1, records audit, and does not continue to automatic Room-2
     recommendation.

1. **LLM2 suggestion and reconciliation**
   - For `eda`, the system calls LLM2 for suggestion (`accept|deny`).
   - Then deterministic policy reconciliation (hard-rules) is applied to prevent
     inconsistencies between suggestion and mandatory rules.

1. **Deterministic pre-procedure gate (`preop_gate`)**
   - Deterministic EDA policy computes explainable decision fields (`decision`,
     `reason_code`, `reason_text`, `evidence_spans`, `pediatric_flag`).
   - This block is persisted in `suggested_action_json.preop_gate` without
     breaking legacy `suggestion` consumers.

1. **Room-2 physician review publication**
   - Only eligible cases are published with technical summary and strict reply
     template.

1. **Physician decision and finalization**
   - Physician replies via Matrix structured reply in Room-2.
   - System validates contract, applies state transition, and executes final jobs
     (Room-3/Room-1 depending on outcome).

## End-to-end flow (table)

| Stage | Input | Main component | Main output |
| --- | --- | --- | --- |
| Intake + extraction | Room-1 PDF | `process_pdf_case_service` + LLM1 | `structured_data_json` |
| Scope gate | `structured_data_json.preop_screening.exam_type` | `process_pdf_case_service` | `manual_review_required` (for `non_eda\|unknown`) |
| Clinical suggestion | `structured_data_json` (EDA) | `llm2_service` | `suggested_action_json.suggestion` |
| Hard-rule reconciliation | precheck + LLM2 suggestion | `domain/policy/eda_policy.py` | reconciled suggestion |
| Deterministic EDA gate | `structured_data_json` | `domain/policy/eda_preop_policy.py` | explainable `preop_gate` |
| Room-2 physician review | message I/II/III + template | `room2_reply_service` | physician decision applied |
| Operational finalization | human decision + state | post-final services/jobs | final reply + audit + cleanup |

## EDA domain (first supported domain)

Currently, automatic flow applies deterministic rules for EDA and treats
`non_eda|unknown` as mandatory manual review.

EDA rules are split into two blocks:

- **Explainable pre-procedure rules:** `eda_preop_policy.py` (`preop_gate`).
- **LLM2 suggestion hard-rule reconciliation:** `eda_policy.py`.

## Where rules live in code

- Pipeline orchestration: `src/triage_automation/application/services/process_pdf_case_service.py`
- Deterministic EDA policy (`preop_gate`): `src/triage_automation/domain/policy/eda_preop_policy.py`
- LLM2 suggestion hard-rule reconciliation: `src/triage_automation/domain/policy/eda_policy.py`
- Physician decision capture (Room-2):
  - `src/triage_automation/application/services/room2_reply_service.py`
  - `src/triage_automation/application/services/handle_doctor_decision_service.py`

## Rule evolution (short guide)

To add/remove/modify rules safely:

1. Update OpenSpec (design/spec/tasks) before implementing meaningful rule change.
2. Write RED tests at the right level (policy unit + runtime/message integration).
3. Implement deterministic rule in the appropriate policy module.
4. Ensure explainable output with `reason_code`/`reason_text` and, when
   applicable, `evidence_spans`.
5. Update operational runbook docs and English mirror.
6. Run full quality gates (`pytest`, `ruff`, `mypy`, `markdownlint`).

## References

- `docs/en/manual_e2e_runbook.md`
- `openspec/changes/eda-preop-criteria-and-eda-scope-gating/design.md`
- `openspec/changes/eda-preop-criteria-and-eda-scope-gating/specs/`

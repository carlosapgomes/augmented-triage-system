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

### Term definitions (operational EDA vs non-operational EDA)

In this rulebook, **operational EDA** and **non-operational EDA** are
labels for deterministic rule-priority groups (not a care-site label).

- **Operational EDA**: EDA with `indication_category` in `bleeding`,
  `abdominal_pain`, or `dyspepsia`.
- **Non-operational EDA**: any confirmed EDA outside those three scenarios.

These definitions consolidate the alignment between local CHD criteria
(including operational clinical messaging) and the criteria spreadsheet
reviewed during this change modeling.

## EDA rulebook (deterministic precedence)

The ordering below is the reference for current behavior.

| Priority | Condition | Output | Main `reason_code` |
| --- | --- | --- | --- |
| 0 | `exam_type` = `non_eda` | `manual_review_required` | `non_eda_request` |
| 0 | `exam_type` = `unknown` | `manual_review_required` | `unknown_exam_type` |
| 1 | `eda.exclusion_type = gastrostomy` | `excluded` | `excluded_gastrostomy` |
| 1 | `eda.exclusion_type = esophageal_dilation` | `excluded` | `excluded_esophageal_dilation` |
| 2 | Cardiovascular risk reported + missing ECG | `deny` | `missing_ecg_with_cardiovascular_disease` |
| 2 | Respiratory risk reported + missing chest X-ray | `deny` | `missing_chest_xray_with_respiratory_risk` |
| 3 | Operational EDA (`bleeding`, `abdominal_pain`, `dyspepsia`) + `hb <= 7` | `deny` | `hb_below_threshold` |
| 3 | Operational EDA + `platelets <= 100000` | `deny` | `platelets_below_threshold` |
| 3 | Operational EDA + `inr >= 1.5` | `deny` | `inr_above_threshold` |
| 3 | Operational EDA + missing ECG | `deny` | `missing_ecg_with_cardiovascular_disease` |
| 4 | Non-operational EDA + `hb < 7` | `deny` | `hb_below_threshold` |
| 4 | Non-operational EDA + `platelets < 50000` | `deny` | `platelets_below_threshold` |
| 4 | Non-operational EDA + `inr > 2` | `deny` | `inr_above_threshold` |
| 5 | `eda.indication_category = foreign_body` | `accept` | `foreign_body_exception` |
| 6 | No deny/exclusion trigger matched | `accept` | `criteria_met` |

## Practical `reason_code` catalog

| `reason_code` | Operational meaning | Main consumer |
| --- | --- | --- |
| `non_eda_request` | Non-EDA scope: mandatory manual review | runtime + Room-1 final |
| `unknown_exam_type` | Unknown exam type: mandatory manual review | runtime + Room-1 final |
| `excluded_gastrostomy` | Request excluded from automatic EDA flow | `preop_gate` |
| `excluded_esophageal_dilation` | Request excluded from automatic EDA flow | `preop_gate` |
| `missing_ecg_with_cardiovascular_disease` | Cardiovascular risk without ECG | `preop_gate` + Room-2 summary |
| `missing_chest_xray_with_respiratory_risk` | Respiratory risk without chest X-ray | `preop_gate` + Room-2 summary |
| `hb_below_threshold` | Hemoglobin below scenario threshold | `preop_gate` |
| `platelets_below_threshold` | Platelets below scenario threshold | `preop_gate` |
| `inr_above_threshold` | INR above scenario threshold | `preop_gate` |
| `manual_review_required_insufficient_data` | Defensive fallback for incomplete payload | `preop_gate` serialization |
| `foreign_body_exception` | Foreign-body exception (accept without routine lab gate) | `preop_gate` |
| `criteria_met` | Deterministic criteria satisfied | `preop_gate` |

## Rule extension map (where to change)

| Desired change | Main file | Expected minimum tests |
| --- | --- | --- |
| New deterministic EDA gate/threshold | `src/triage_automation/domain/policy/eda_preop_policy.py` | `tests/unit/test_eda_preop_policy.py` |
| Scope routing change (`non_eda\|unknown`) | `src/triage_automation/application/services/process_pdf_case_service.py` | `tests/integration/test_process_pdf_case_llm2.py` |
| Room-2 concise deny text change | `src/triage_automation/infrastructure/matrix/message_templates.py` | `tests/unit/test_room2_message_templates.py` + `tests/integration/test_post_room2_widget.py` |
| Room-2 physician decision parser/contract change | `src/triage_automation/domain/doctor_decision_parser.py` | parser unit tests + reply integration tests |

## Where rules live in code

- Pipeline orchestration: `src/triage_automation/application/services/process_pdf_case_service.py`
- Deterministic EDA policy (`preop_gate`): `src/triage_automation/domain/policy/eda_preop_policy.py`
- LLM2 suggestion hard-rule reconciliation: `src/triage_automation/domain/policy/eda_policy.py`
- Physician decision capture (Room-2):
  - `src/triage_automation/application/services/room2_reply_service.py`
  - `src/triage_automation/application/services/handle_doctor_decision_service.py`

## Rule-evolution playbook (add/remove/change)

### Recommended flow per change

1. **Define functional impact before coding**
   - Update OpenSpec (design/spec/tasks) whenever contract, precedence, or new
     `reason_code` semantics change.
   - State clearly whether scope is EDA-only or decision-engine-wide.

2. **Write RED tests first (contract + behavior)**
   - Deterministic policy: unit tests in the policy module.
   - Runtime/orchestration: integration tests for state, jobs, and audit.
   - Messages/UX: template unit tests plus Room-2 posting integration tests.

3. **Implement in the correct module (avoid rule scattering)**
   - Deterministic clinical rule: `eda_preop_policy.py`.
   - Scope gate/flow routing: `process_pdf_case_service.py`.
   - Physician-facing concise deny text: `message_templates.py`.

4. **Guarantee explainability and compatibility**
   - Relevant outputs must keep `reason_code`, `reason_text`, and when
     applicable, `evidence_spans`.
   - Preserve legacy `suggestion` while keeping `preop_gate` as explainable block.

5. **Update docs in the same slice**
   - Update this rulebook and the PT-BR mirror.
   - Update operational runbook if observed behavior changes.

6. **Run validations and record evidence**
   - Run tests/lint/types and record command evidence in the change `tasks.md`.

### Mandatory anti-regression checklist

- [ ] Rule remains deterministic in code (not shifted to prompt authority).
- [ ] New/changed `reason_code` is mapped in relevant downstream consumers.
- [ ] `preop_gate` remains serialized without breaking `suggestion` consumers.
- [ ] `non_eda|unknown` cases still avoid automatic `accept|deny`.
- [ ] Room-2 still skips recommendation summary for scope-gated manual review.
- [ ] Room-2 physician decision parser keeps strict contract behavior.

### Minimum validation commands

```bash
uv run pytest tests/unit/test_eda_preop_policy.py tests/integration/test_process_pdf_case_llm2.py tests/integration/test_post_room2_widget.py tests/unit/test_room2_message_templates.py -q
uv run ruff check src/triage_automation/domain/policy/eda_preop_policy.py src/triage_automation/application/services/process_pdf_case_service.py src/triage_automation/infrastructure/matrix/message_templates.py
uv run mypy src/triage_automation/domain/policy/eda_preop_policy.py src/triage_automation/application/services/process_pdf_case_service.py src/triage_automation/infrastructure/matrix/message_templates.py
markdownlint-cli2 "docs/decision-engine-and-rulebook.md" "docs/en/decision-engine-and-rulebook.md"
```

## References

- `docs/en/manual_e2e_runbook.md`
- `openspec/changes/eda-preop-criteria-and-eda-scope-gating/design.md`
- `openspec/changes/eda-preop-criteria-and-eda-scope-gating/specs/`

# Decision Engine and Rulebook

Language: [Portugues (BR)](../decision-engine-and-rulebook.md) | **English**

## Goal

This document explains how ATS makes decisions throughout the triage flow, with
an emphasis on predictability, auditability, and safe rulebook evolution.

The goal is to avoid a common ambiguity: assuming the clinical decision comes
from the prompt. In ATS, the prompt guides extraction and suggestion, but the
critical automatic-flow rules are deterministic in code. Final clinical
decision-making remains human and is recorded by the physician in Room-2.

## Decision-engine principles

1. Prompts are extraction and structure contracts, not final rule authority.
2. Deterministic rules are implemented in domain policies and services.
3. Every critical output must remain auditable with `reason_code`,
   `reason_text`, and, when available, `evidence_spans`.
4. Final clinical decision remains human and explicit in Room-2.
5. Rulebook changes must preserve compatibility for `suggestion` consumers while
   keeping added explainability in `preop_gate`.

## End-to-end flow (narrative)

1. **Intake and initial extraction**
   - A case enters through Room-1 with a PDF.
   - The worker extracts text and calls LLM1 to structure the clinical data.

2. **Deterministic scope gate**
   - The system evaluates `preop_screening.exam_type`.
   - If it is `non_eda` or `unknown`, the case moves to
     `manual_review_required`, with operational closure in Room-1, audit
     records, and no Room-2 summary publication.

3. **LLM2 suggestion and reconciliation**
   - For `eda` cases, the system calls LLM2 to produce a clinical suggestion.
   - It then applies deterministic reconciliation to align that suggestion with
     the current rulebook.

4. **Deterministic pre-procedure gate (`preop_gate`)**
   - Deterministic EDA policy computes an explainable block with `decision`,
     `reason_code`, `reason_text`, `evidence_spans`, and `pediatric_flag`.
   - This block is persisted in `suggested_action_json.preop_gate`.

5. **Practical ASA and support synthesis**
   - The system derives a practical `ASA estimate` (`I-II`, `III ou mais`, or an
     insufficient-data fallback).
   - The same synthesis defines the recommended support (`none`, `anesthesist`,
     or `anesthesist_icu`).

6. **Publication for physician review in Room-2**
   - Only eligible cases are published with a technical summary, procedure
     context, and a strict reply template.

7. **Physician decision and finalization**
   - The physician replies through a structured message in Room-2.
   - The system validates the contract, applies state transitions, and runs the
     finalization jobs in the downstream rooms.

## End-to-end flow (table)

| Stage | Input | Main component | Main output |
| --- | --- | --- | --- |
| Intake + extraction | Room-1 PDF | `process_pdf_case_service` + LLM1 | `structured_data_json` |
| Scope gate | `structured_data_json.preop_screening.exam_type` | `process_pdf_case_service` | `manual_review_required` (for `non_eda\|unknown`) |
| Clinical suggestion | `structured_data_json` (supported EDA) | `llm2_service` | `suggested_action_json.suggestion` |
| Deterministic EDA gate | `structured_data_json` | `domain/policy/eda_preop_policy.py` | explainable `preop_gate` |
| ASA/support synthesis | `structured_data_json` | `domain/policy/eda_recommendation_synthesis.py` | `asa` + `support_recommendation` |
| Room-2 physician review | message I/II/III + template | `post_room2_widget_service` + `room2_reply_service` | physician decision applied |
| Operational finalization | human decision + state | final services/jobs | final reply + audit + cleanup |

## Supported EDA domain

The rewritten rulebook abandons the legacy split between “operational” and
“non-operational” EDA as the main axis for automatic decision-making. The flow
now supports a single clinical EDA domain with explicit subtypes and CHD-local
criteria.

### Supported subtypes inside the automatic flow

| Subtype | Description | Flow behavior |
| --- | --- | --- |
| `standard` | Standard EDA | follows the full rule set |
| `gastrostomy` | EDA for gastrostomy | follows the same minimum rule set as `standard` |
| `esophageal_dilation` | EDA for esophageal dilation | follows the same minimum rule set as `standard` |
| `foreign_body` | EDA for foreign-body removal | bypasses minimum exams and conditional gates |

### Unsupported scope

- `non_eda`: mandatory manual review.
- `unknown`: mandatory manual review.

## Rewritten EDA rulebook

The deterministic policy follows the priority below.

### 1. Scope gate

| Priority | Condition | Output | `reason_code` |
| --- | --- | --- | --- |
| 0 | `exam_type = non_eda` | `manual_review_required` | `non_eda_request` |
| 0 | `exam_type = unknown` | `manual_review_required` | `unknown_exam_type` |

### 2. Foreign-body exception

| Priority | Condition | Output | `reason_code` |
| --- | --- | --- | --- |
| 1 | `foreign_body` subtype | `accept` | `foreign_body_exception` |

For `foreign_body`, the system bypasses:

- mandatory minimum exams;
- conditional ECG, chest X-ray, and echocardiogram gates.

Even so, the case may still receive a support recommendation based on the
remaining clinical context and the practical ASA estimate.

### 3. Mandatory minimum exams

For `standard`, `gastrostomy`, and `esophageal_dilation`, automatic acceptance
is only possible when there is minimum evidence for:

- `Hb/Ht`;
- platelets;
- `TP|INR|RNI` with numeric evidence;
- `TTPa`;
- urea;
- creatinine.

#### Evidence rules

- `Hb` alone satisfies the `Hb/Ht` requirement.
- Generic phrases such as `normal blood count`, `coagulation panel without
  changes`, or `lab tests without changes` **do not** satisfy the numeric
  requirements for Hb, platelets, or `TP|INR|RNI`.
- Qualitative evidence may satisfy:
  - `TTPa` when text such as `normal TTPa` is present;
  - urea and creatinine when `preserved renal function` or an equivalent phrase
    is present;
  - `normal coagulation panel` satisfies `TTPa` only if `TP|INR|RNI` is already
    documented with numeric evidence.

#### Minimum-exam `reason_code` values

| Failure | `reason_code` |
| --- | --- |
| Missing Hb/Ht | `missing_minimum_exam_hb_or_ht` |
| Missing platelets | `missing_minimum_exam_platelets` |
| Missing TP/INR/RNI | `missing_minimum_exam_tp_inr_rni` |
| Missing TTPa | `missing_minimum_exam_ttpa` |
| Missing urea | `missing_minimum_exam_urea` |
| Missing creatinine | `missing_minimum_exam_creatinine` |

### 4. Contraindication thresholds

Once minimum exams are present, the system applies denial thresholds according
to the explicitly documented clinical profile.

| Clinical profile | Hb | Platelets | RNI/INR |
| --- | --- | --- | --- |
| General (no explicit hepatopathy/cardiopathy) | `< 7` | `< 100000` | `> 1.5` |
| Explicit hepatopathy | `< 7` | `< 50000` | `> 1.5` |
| Explicit cardiopathy | `< 8` | `< 100000` | `> 1.5` |
| Explicit hepatopathy + cardiopathy | `< 8` | `< 50000` | `> 1.5` |

#### Threshold `reason_code` values

| Failure | `reason_code` |
| --- | --- |
| Hb below threshold | `hb_below_threshold` |
| Platelets below threshold | `platelets_below_threshold` |
| INR/RNI above threshold | `inr_above_threshold` |

## Conditional cardiorespiratory completeness gates

After minimum exams and before acceptance, the rulebook requires a minimal exam
report when certain clinical triggers are present.

### ECG

An ECG with a minimally reportable finding is mandatory if at least one of the
following signals is present:

- age above 40 years;
- known cardiovascular disease;
- recent chest pain;
- recent dyspnea;
- palpitations;
- syncope;
- multiple comorbidities;
- use of QT-prolonging medications;
- diabetes mellitus;
- explicit obesity.

If the trigger exists and the report only mentions exam existence without a
minimal finding, the decision is `deny` with:

- `reason_code`: `missing_ecg_with_cardiovascular_disease`.

### Chest X-ray

A chest X-ray with a minimally reportable finding is mandatory if there is:

- active respiratory symptoms; or
- prior respiratory disease.

If the minimal report is missing, the decision is `deny` with:

- `reason_code`: `missing_chest_xray_with_respiratory_risk`.

### Echocardiogram

An echocardiogram with a minimally reportable finding is mandatory if there is:

- unexplained dyspnea;
- signs of heart failure;
- new or unevaluated murmur;
- moderate or severe valvulopathy without a recent echo;
- worsening cardiomyopathy;
- pulmonary hypertension;
- prior myocardial infarction;
- prior coronary bypass surgery;
- prior coronary angioplasty.

If the minimal report is missing, the decision is `deny` with:

- `reason_code`: `missing_echocardiogram_with_structural_heart_risk`.

### Completeness notes

- Mentioning that the exam “exists” or “was requested” does not satisfy the
  rule.
- The report must include a minimally reportable finding, such as `ECG without
  changes` or `normal chest X-ray`.
- Isolated suspicion, without explicit clinical evidence, does not create a hard
  trigger for conditional gates.

## Pediatric signaling

Cases with age below 16 are explicitly marked as pediatric. This signal is
preserved for downstream consumers and appears in Room-2 as:

- `paciente pediátrico: sim`.

## Practical ASA and support semantics

The system derives a conservative practical ASA estimate independently from the
final decision. That value is shown in Room-2 and also drives the support
recommendation.

### Practical ASA buckets

| Persisted value | Display |
| --- | --- |
| `I-II` | `I-II` |
| `III ou mais` | `III ou mais` |
| `insufficient_data` | `não foi possível estimar com os dados apresentados` |

### Support mapping

| Context | `support_recommendation` | Practical interpretation |
| --- | --- | --- |
| Practical ASA `I-II` and no high cardiovascular risk | `none` | sedation by the endoscopist, with no mandatory extra support |
| Practical ASA `III ou mais` | `anesthesist` | minimum requirement for anesthetist support |
| Practical ASA + `moderate_high` cardiovascular risk | `anesthesist_icu` | anesthetic support in a context compatible with ICU support |
| Insufficient ASA data, without signals that escalate support | derived from the remaining confirmed evidence | conservative fallback without inventing a formal ASA class |

## Persisted auditable output

For supported EDA cases, persistence must keep enough context for
recommendation, audit, and Room-2 rendering.

### Expected minimum clinical fields

- `suggestion`;
- `decision`;
- `reason_code`;
- `reason_text`;
- `support_recommendation`;
- `asa.bucket` and `asa.display_text`;
- `preop_gate.decision`;
- `preop_gate.reason_code`;
- `preop_gate.reason_text`;
- `preop_gate.evidence_spans`;
- subtype and pediatric signaling in the structured context.

## Room-2 rendering

The Room-2 technical message now follows a fixed seven-block layout:

1. `Resumo clínico`
2. `Achados críticos`
3. `Pendências críticas`
4. `Decisão sugerida`
5. `Suporte recomendado`
6. `ASA estimado`
7. `Motivo objetivo`

### Objective-reason text rules

- In `accept`, the reason must be short and aligned with support context.
- In `deny`, the reason must list objective causes from the rewritten rulebook.
- The priority for `deny` objective reason is:
  1. missing mandatory minimum exam;
  2. missing minimal ECG/chest X-ray/echo report when applicable;
  3. contraindication due to exceeded threshold;
  4. defensive safety fallback.
- If there are more than two objective causes, Room-2 shows at most two and
  adds a compact marker equivalent to `e outras pendências críticas`.
- The summary also makes explicit:
  - the canonical supported subtype procedure;
  - the pediatric marker when applicable;
  - `ASA estimado` in its own dedicated block.

## Practical `reason_code` catalog

| `reason_code` | Operational meaning | Main consumer |
| --- | --- | --- |
| `non_eda_request` | Non-EDA scope: mandatory manual review | runtime + Room-1 final |
| `unknown_exam_type` | Unknown exam type: mandatory manual review | runtime + Room-1 final |
| `foreign_body_exception` | Foreign-body exception with minimum-gate bypass | `preop_gate` + final synthesis |
| `missing_minimum_exam_hb_or_ht` | Missing minimum Hb/Ht | `preop_gate` + Room-2 |
| `missing_minimum_exam_platelets` | Missing minimum platelets | `preop_gate` + Room-2 |
| `missing_minimum_exam_tp_inr_rni` | Missing minimum TP/INR/RNI | `preop_gate` + Room-2 |
| `missing_minimum_exam_ttpa` | Missing minimum TTPa | `preop_gate` + Room-2 |
| `missing_minimum_exam_urea` | Missing minimum urea | `preop_gate` + Room-2 |
| `missing_minimum_exam_creatinine` | Missing minimum creatinine | `preop_gate` + Room-2 |
| `missing_ecg_with_cardiovascular_disease` | Cardiovascular gate without minimal ECG report | `preop_gate` + Room-2 |
| `missing_chest_xray_with_respiratory_risk` | Respiratory gate without minimal chest X-ray report | `preop_gate` + Room-2 |
| `missing_echocardiogram_with_structural_heart_risk` | Structural cardiac gate without minimal echo report | `preop_gate` + Room-2 |
| `hb_below_threshold` | Hb below the threshold for the applicable profile | `preop_gate` + Room-2 |
| `platelets_below_threshold` | Platelets below the threshold for the applicable profile | `preop_gate` + Room-2 |
| `inr_above_threshold` | INR/RNI above the threshold for the applicable profile | `preop_gate` + Room-2 |
| `criteria_met` | Deterministic criteria satisfied | `preop_gate` |
| `manual_review_required_insufficient_data` | Defensive fallback for incomplete payload | `preop_gate` serialization |

## Rule extension map (where to change)

| Desired change | Main file | Expected minimum tests |
| --- | --- | --- |
| New minimum exam, conditional gate, or EDA threshold | `src/triage_automation/domain/policy/eda_preop_policy.py` | `tests/unit/test_eda_preop_policy.py` |
| Change practical ASA or support synthesis | `src/triage_automation/domain/policy/eda_recommendation_synthesis.py` | `tests/unit/test_eda_recommendation_synthesis.py` |
| Change scope routing (`non_eda\|unknown`) | `src/triage_automation/application/services/process_pdf_case_service.py` | `tests/integration/test_process_pdf_case_llm2.py` |
| Change objective reason, ASA, or Room-2 summary context | `src/triage_automation/infrastructure/matrix/message_templates.py` | `tests/unit/test_room2_message_templates.py` + `tests/integration/test_post_room2_widget.py` |
| Change Room-2 physician decision parser/contract | `src/triage_automation/domain/doctor_decision_parser.py` | parser unit tests + reply integration tests |

## Where rules live in code

- Pipeline orchestration:
  `src/triage_automation/application/services/process_pdf_case_service.py`
- Deterministic EDA policy (`preop_gate`):
  `src/triage_automation/domain/policy/eda_preop_policy.py`
- Practical ASA and support synthesis:
  `src/triage_automation/domain/policy/eda_recommendation_synthesis.py`
- Room-2 publication and rendering:
  `src/triage_automation/application/services/post_room2_widget_service.py`
  and `src/triage_automation/infrastructure/matrix/message_templates.py`
- Physician decision capture (Room-2):
  `src/triage_automation/application/services/room2_reply_service.py` and
  `src/triage_automation/application/services/handle_doctor_decision_service.py`

## Rule-evolution playbook (add/remove/change)

### Recommended flow per change

1. **Define functional impact before coding**
   - Update OpenSpec whenever contract, precedence, supported subtype,
     `reason_code`, or support semantics change.
   - State clearly whether the change affects only EDA or the wider engine.

2. **Write RED tests first**
   - Deterministic policy: unit tests in the policy module.
   - Runtime/orchestration: integration tests for state, jobs, and audit.
   - Messages/UX: template tests and Room-2 publication integration tests.

3. **Implement in the correct module**
   - Deterministic clinical rule: `eda_preop_policy.py`.
   - ASA/support synthesis: `eda_recommendation_synthesis.py`.
   - Scope gate: `process_pdf_case_service.py`.
   - Physician-facing review text: `message_templates.py`.

4. **Guarantee explainability and compatibility**
   - Preserve `reason_code`, `reason_text`, and `evidence_spans`.
   - Preserve legacy `suggestion` while keeping `preop_gate` as an explainable
     block.

5. **Update operational documentation**
   - Update this rulebook and the Portuguese mirror.
   - Update the manual runbook when observed Room-2 or operational-closing
     behavior changes.

6. **Run validation and record evidence**
   - Run the applicable lint/tests and record commands/results in the change
     `tasks.md`.

### Mandatory anti-regression checklist

- [ ] Rule remains deterministic in code.
- [ ] New `reason_code` values are documented and mapped in consumers.
- [ ] `preop_gate` remains serialized without breaking `suggestion` consumers.
- [ ] `non_eda|unknown` cases still avoid automatic `accept|deny`.
- [ ] `foreign_body` remains inside supported EDA flow with explicit bypass.
- [ ] Room-2 still makes subtype, ASA, and pediatric context explicit when
  applicable.

### Minimum validation commands

```bash
uv run pytest tests/unit/test_eda_preop_policy.py tests/unit/test_eda_recommendation_synthesis.py tests/integration/test_process_pdf_case_llm2.py tests/integration/test_post_room2_widget.py tests/unit/test_room2_message_templates.py -q
uv run ruff check src/triage_automation/domain/policy/eda_preop_policy.py src/triage_automation/domain/policy/eda_recommendation_synthesis.py src/triage_automation/application/services/process_pdf_case_service.py src/triage_automation/infrastructure/matrix/message_templates.py
uv run mypy src/triage_automation/domain/policy/eda_preop_policy.py src/triage_automation/domain/policy/eda_recommendation_synthesis.py src/triage_automation/application/services/process_pdf_case_service.py src/triage_automation/infrastructure/matrix/message_templates.py
markdownlint-cli2 "docs/decision-engine-and-rulebook.md" "docs/en/decision-engine-and-rulebook.md"
```

## References

- `docs/manual_e2e_runbook.md`
- `openspec/changes/eda-decision-rulebook-rewrite/specs/eda-preop-deterministic-criteria/spec.md`
- `openspec/changes/eda-decision-rulebook-rewrite/specs/room2-concise-medical-opinion-message/spec.md`

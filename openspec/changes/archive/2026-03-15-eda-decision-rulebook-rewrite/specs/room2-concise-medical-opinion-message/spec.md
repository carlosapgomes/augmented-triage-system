# room2-concise-medical-opinion-message Delta Specification

## MODIFIED Requirements

### Requirement: Room-2 Summary SHALL Include Mandatory Seven-Block Layout

The system SHALL render the Room-2 summary with a fixed seven-block layout to standardize medical reading flow under the rewritten EDA rulebook.

#### Scenario: Summary message is posted in Room-2

- **WHEN** the bot posts message II for a case in Room-2
- **THEN** the message MUST include the following blocks in order:
- **AND** `Resumo clínico`
- **AND** `Achados críticos`
- **AND** `Pendências críticas`
- **AND** `Decisão sugerida`
- **AND** `Suporte recomendado`
- **AND** `ASA estimado`
- **AND** `Motivo objetivo`

### Requirement: Decision, Support, And Objective Reason SHALL Be Explicit And Coherent

The message SHALL explicitly show the final recommendation fields and an objective reason aligned with the rewritten EDA rulebook.

#### Scenario: Suggested action is rendered after the rulebook rewrite

- **WHEN** `suggested_action_json` already reflects the rewritten EDA recommendation logic
- **THEN** `Decisão sugerida` MUST reflect the final recommendation value consumed by Room-2 rendering
- **AND** `Suporte recomendado` MUST reflect the final support value consumed by Room-2 rendering
- **AND** `ASA estimado` MUST reflect the practical ASA bucket or explicit inability to estimate it
- **AND** if final suggestion is `deny`, `Motivo objetivo` MUST state objective denial causes and MUST NOT contain acceptance phrasing
- **AND** if final suggestion is `deny`, `Motivo objetivo` MUST NOT include support recommendation phrasing
- **AND** if final suggestion is `deny`, objective causes MUST be derived from rewritten EDA rulebook signals with this priority: missing mandatory minimum exam, missing applicable ECG/RX/ECO report, explicit contraindication threshold, fallback safety cause
- **AND** if final suggestion is `deny` and more than two objective causes exist, `Motivo objetivo` MUST list at most two causes and MUST include a compact continuation marker equivalent to `e outras pendências críticas`
- **AND** if final suggestion is `accept`, `Motivo objetivo` MUST be a short acceptance phrase with support context only
- **AND** if final suggestion is `accept`, `Motivo objetivo` MUST preserve explicit uncertainty notes only when the report contains evidence-insufficient but non-blocking context

### Requirement: Room-2 Summary SHALL Explain Deterministic Preop Denial Causes

When the rewritten EDA rulebook recommends denial due to missing required exams or contraindication thresholds, message II SHALL present concise explicit justification suitable for physician review.

#### Scenario: Denial due to missing mandatory minimum exam

- **WHEN** rewritten EDA recommendation returns `deny` because a mandatory minimum exam is absent
- **THEN** Room-2 summary MUST include concise text stating which minimum exam is missing
- **AND** the summary MUST keep decision-oriented wording suitable for physician review

#### Scenario: Denial due to cardiovascular trigger without ECG report

- **WHEN** rewritten EDA recommendation returns `deny` because ECG-triggering criteria are present and no ECG report finding is documented
- **THEN** Room-2 summary MUST include concise text stating that ECG report evidence is missing
- **AND** the summary MUST keep decision-oriented wording suitable for physician review

#### Scenario: Denial due to respiratory trigger without chest X-ray report

- **WHEN** rewritten EDA recommendation returns `deny` because respiratory criteria are present and no chest X-ray report finding is documented
- **THEN** Room-2 summary MUST include concise text stating that chest X-ray report evidence is missing
- **AND** the summary MUST keep decision-oriented wording suitable for physician review

#### Scenario: Denial due to echocardiogram trigger without echo report

- **WHEN** rewritten EDA recommendation returns `deny` because echo-triggering criteria are present and no echocardiogram report finding is documented
- **THEN** Room-2 summary MUST include concise text stating that echocardiogram report evidence is missing
- **AND** the summary MUST keep decision-oriented wording suitable for physician review

#### Scenario: Denial due to contraindication threshold

- **WHEN** rewritten EDA recommendation returns `deny` because a hepatopathy, cardiopathy, combined, or general contraindication threshold is exceeded
- **THEN** Room-2 summary MUST include concise text stating which threshold failed
- **AND** the summary MUST keep decision-oriented wording suitable for physician review

## ADDED Requirements

### Requirement: Room-2 Summary SHALL Include Procedure Context And Pediatric Marker

The system SHALL render the supported EDA subtype context explicitly in Room-2 and SHALL preserve pediatric signaling near the case context lines.

#### Scenario: Supported EDA subtype is gastrostomy, esophageal dilation, or foreign-body removal

- **WHEN** message II is rendered for supported subtype `gastrostomy`, `esophageal_dilation`, or `foreign_body`
- **THEN** the summary context MUST display the canonical requested procedure text for that subtype
- **AND** the displayed procedure text MUST remain consistent with downstream room propagation

#### Scenario: Pediatric marker is available

- **WHEN** the case is pediatric
- **THEN** the Room-2 context area MUST include `paciente pediátrico: sim`
- **AND** the marker MUST be rendered near the human-readable case context rather than hidden inside free-text rationale

### Requirement: Room-2 Summary SHALL Surface Practical ASA Estimate Explicitly

The system SHALL surface the practical ASA estimate in a dedicated Room-2 block so physicians can quickly distinguish support recommendation from formal clinical rationale.

#### Scenario: Practical ASA estimate is available

- **WHEN** recommendation context includes practical ASA bucket `I-II` or `III ou mais`
- **THEN** the `ASA estimado` block MUST render that bucket explicitly

#### Scenario: Practical ASA estimate is not safely available

- **WHEN** recommendation context indicates insufficient evidence to estimate practical ASA
- **THEN** the `ASA estimado` block MUST render fallback text equivalent to `não foi possível estimar com os dados apresentados`

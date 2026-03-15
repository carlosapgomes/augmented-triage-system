# manual-e2e-readiness Specification

## Purpose

Define deterministic runtime smoke checks and tunnel validation steps used
before manual end-to-end testing.

## Requirements

### Requirement: Deterministic Manual Runtime Validation

The project SHALL define deterministic smoke checks for validating live runtime
readiness before full manual end-to-end testing using the single structured-
reply Room-2 decision path.

#### Scenario: Pre-E2E smoke execution

- **WHEN** operators prepare for manual end-to-end testing
- **THEN** they MUST be able to verify service startup, database readiness, and
  Room-2 structured reply readiness with documented deterministic checks

### Requirement: Configurable External Dependency Test Modes

Runtime execution SHALL support explicit configuration modes that enable
 deterministic manual validation when external providers are unavailable.

#### Scenario: LLM provider unavailable in manual testing

- **WHEN** deterministic runtime mode is enabled for manual validation
- **THEN** LLM-dependent workflow steps MUST remain executable via configured
  deterministic adapters without altering triage business semantics

### Requirement: Manual E2E Runbook SHALL Define Operational Validation Flow

The project SHALL keep one human-readable manual E2E runbook that is actionable
for operations and support teams before production usage.

#### Scenario: Operator performs manual E2E checks

- **WHEN** a team member follows the manual runbook
- **THEN** the runbook MUST cover startup prerequisites, execution flow, and
  expected outputs
- **AND** each step MUST be concrete enough to execute without code changes
- **AND** language navigation MUST provide Portuguese default and English
  mirror to support mixed-language teams

#### Scenario: Role, prompt, and user governance checks are reviewed

- **WHEN** manual validation reaches authorization, prompt-management, and
  user-management checks
- **THEN** the runbook MUST include role matrix expectations (`reader` vs
  `admin`)
- **AND** the runbook MUST include prompt activation/create verification points
  consistent with current admin surface
- **AND** the runbook MUST include user-management verification points for
  create, block, reactivate, and remove actions with expected authorization
  outcomes
- **AND** the runbook MUST include expected audit-event verification points for
  user-management actions

### Requirement: Manual E2E SHALL Validate Single Room-2 Structured Reply Decision Path

Manual runbooks SHALL validate the three-message Room-2 combo protocol and
structured doctor replies as the only standard decision path, including
explicit physician choice of admission flow for accepted decisions.

#### Scenario: Operator validates accepted scheduled workflow in mobile-capable client

- **WHEN** operator follows the documented Room-2 decision runbook for an
  accepted case routed to scheduling
- **THEN** they MUST verify message I + II + III publication, grouped
  relations for II/III to I, and structured reply submission to message I
- **AND** they MUST verify message III includes the explicit
  `fluxo de admissão` line
- **AND** they MUST verify the accepted reply with `agendamento` produces the
  expected Room-3 scheduling progression
- **AND** they MUST verify a Room-2 decision confirmation message is posted by
  the bot after successful decision handling

#### Scenario: Operator validates accepted immediate-admission workflow in mobile-capable client

- **WHEN** operator follows the documented Room-2 decision runbook for an
  accepted case routed to immediate admission
- **THEN** they MUST verify the physician can submit the structured reply using
  `vinda_imediata` or equivalent accepted alias
- **AND** they MUST verify the Room-2 decision confirmation echoes the
  normalized immediate-admission flow
- **AND** they MUST verify positive acknowledgment reaction in Room-2 remains
  optional and non-blocking for workflow progression

### Requirement: Manual E2E SHALL Validate Structured Reply Rejection Cases

Manual runbooks SHALL include negative checks for malformed template content,
wrong reply-parent targeting, and invalid admission-flow usage.

#### Scenario: Malformed structured reply submitted

- **WHEN** a reply does not satisfy strict decision template rules
- **THEN** the decision MUST be rejected and no state/job mutation MUST occur

#### Scenario: Reply targets wrong parent event

- **WHEN** a structured reply is posted without referencing the active Room-2
  case message
- **THEN** the decision MUST be rejected and no state/job mutation MUST occur

#### Scenario: Accepted reply omits required admission-flow field

- **WHEN** a physician submits `decisao=aceitar` without the required
  `fluxo de admissão` line
- **THEN** the decision MUST be rejected
- **AND** the correction guidance MUST show the accepted template with the
  missing admission-flow field restored

### Requirement: Manual E2E SHALL Validate Dashboard Timeline Auditability

Manual runbooks SHALL validate that case timeline views expose chronological
records across rooms with actor, timestamp, and ACK visibility.

#### Scenario: Operator reviews a processed case in dashboard

- **WHEN** operator opens a case detail in the monitoring dashboard
- **THEN** the timeline MUST display chronological events across
  Room-1/Room-2/Room-3
- **AND** ACK and human reply events MUST be visible with actor and timestamp
  metadata

### Requirement: Manual E2E SHALL Validate Prompt Management Authorization

Manual runbooks SHALL validate role-based authorization for prompt-management
operations.

#### Scenario: Admin and reader execute prompt-management actions

- **WHEN** an `admin` performs prompt activation and a `reader` attempts the
  same action
- **THEN** admin action MUST succeed and produce an audit event
- **AND** reader action MUST be rejected with no mutation of active prompt
  version

### Requirement: Manual E2E SHALL Validate EDA Scope-Gating Manual Review Path

Manual runbooks SHALL validate that true non-EDA and unresolved unknown exam
requests do not receive automatic recommendation, while supported EDA subtypes
continue through physician review.

#### Scenario: Non-EDA request is processed

- **WHEN** operator executes manual E2E with a report classified as true
  non-EDA
- **THEN** outcome MUST be `manual_review_required`
- **AND** no automatic `accept` or `deny` recommendation MUST be produced
- **AND** Room-1 MUST receive manual-review closure message

#### Scenario: Unknown unsupported exam type request is processed

- **WHEN** operator executes manual E2E with a report whose exam type cannot be
  confirmed as supported EDA
- **THEN** outcome MUST be `manual_review_required`
- **AND** no automatic `accept` or `deny` recommendation MUST be produced
- **AND** Room-1 MUST receive manual-review closure message

#### Scenario: Gastrostomy request remains inside supported EDA flow

- **WHEN** operator executes manual E2E with a report classified as
  `EDA para gastrostomia`
- **THEN** the case MUST continue to automatic recommendation and Room-2
  physician review
- **AND** it MUST NOT be closed as out-of-scope manual review

#### Scenario: Esophageal dilation request remains inside supported EDA flow

- **WHEN** operator executes manual E2E with a report classified as
  `EDA para dilatação esofágica`
- **THEN** the case MUST continue to automatic recommendation and Room-2
  physician review
- **AND** it MUST NOT be closed as out-of-scope manual review

### Requirement: Manual E2E SHALL Validate Deterministic Denial By Missing Prerequisite Exams

Manual runbooks SHALL validate deterministic negative recommendations when
mandatory minimum exams, applicable conditional exams, or contraindication
thresholds fail under the rewritten EDA rulebook.

#### Scenario: Mandatory minimum exam is absent

- **WHEN** operator executes manual E2E for supported EDA request missing one
  of the mandatory minimum exams
- **THEN** recommendation MUST be `deny`
- **AND** output MUST identify the missing minimum exam explicitly

#### Scenario: Cardiovascular trigger exists without ECG report

- **WHEN** operator executes manual E2E for supported EDA request with
  ECG-triggering criteria and no ECG report finding in the source text
- **THEN** recommendation MUST be `deny`
- **AND** output MUST include explicit explanatory text that ECG evidence is
  missing

#### Scenario: Respiratory trigger exists without chest X-ray report

- **WHEN** operator executes manual E2E for supported EDA request with
  respiratory trigger and no chest X-ray report finding in the source text
- **THEN** recommendation MUST be `deny`
- **AND** output MUST include explicit explanatory text that chest X-ray
  evidence is missing

#### Scenario: Echo trigger exists without echocardiogram report

- **WHEN** operator executes manual E2E for supported EDA request with
  echo-triggering criteria and no echocardiogram report finding in the source
  text
- **THEN** recommendation MUST be `deny`
- **AND** output MUST include explicit explanatory text that echocardiogram
  evidence is missing

#### Scenario: Contraindication threshold is exceeded

- **WHEN** operator executes manual E2E for supported EDA request where
  hepatopathy, cardiopathy, combined, or general thresholds are exceeded
- **THEN** recommendation MUST be `deny`
- **AND** output MUST include explicit explanatory text naming the failed
  threshold

### Requirement: Manual E2E SHALL Validate Supported EDA Special Subtypes And Room-2 Clinical Context

Manual runbooks SHALL validate the new supported EDA subtypes and the rewritten
Room-2 summary context under the new rulebook.

#### Scenario: Foreign-body removal bypasses minimum exams but still reaches Room-2

- **WHEN** operator executes manual E2E with a report classified as
  `EDA para retirada de corpo estranho`
- **THEN** the case MUST continue to automatic recommendation and Room-2
  physician review without requiring the mandatory minimum exam set
- **AND** the recommendation MUST still include support context when clinically
  applicable

#### Scenario: Room-2 summary renders ASA and pediatric context explicitly

- **WHEN** operator reviews a supported EDA case in Room-2 after recommendation
  is produced
- **THEN** message II MUST show the `ASA estimado` block explicitly
- **AND** when the case is pediatric it MUST show `paciente pediátrico: sim`
  near the case context
- **AND** the requested procedure text MUST reflect the supported subtype when
  applicable

### Requirement: Manual E2E SHALL Validate Immediate Admission Operational Branch

Manual runbooks SHALL validate the non-scheduling operational branch created by
physician-selected immediate admission.

#### Scenario: Immediate-admission case notifies Room-3 without scheduling

- **WHEN** operator executes manual E2E for a case accepted with
  `vinda_imediata`
- **THEN** Room-3 MUST receive the informational immediate-admission
  communication
- **AND** Room-3 MUST receive an audit acknowledgment target
- **AND** Room-3 MUST NOT receive the standard scheduling request/template
  combo for that case

#### Scenario: Immediate-admission case closes through Room-1 acknowledgment

- **WHEN** operator executes manual E2E for a case accepted with
  `vinda_imediata`
- **THEN** Room-1 MUST receive a final message equivalent to
  `aceito com vinda imediata autorizada`
- **AND** the case MUST remain governed by the Room-1 final acknowledgment for
  closure
- **AND** Room-3 acknowledgment MUST be observable as optional, not mandatory

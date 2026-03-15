# manual-e2e-readiness Delta Specification

## MODIFIED Requirements

### Requirement: Manual E2E SHALL Validate Single Room-2 Structured Reply Decision Path

Manual runbooks SHALL validate the three-message Room-2 combo protocol and structured doctor replies as the only standard decision path, including explicit physician choice of admission flow for accepted decisions.

#### Scenario: Operator validates accepted scheduled workflow in mobile-capable client

- **WHEN** operator follows the documented Room-2 decision runbook for an accepted case routed to scheduling
- **THEN** they MUST verify message I + II + III publication, grouped relations for II/III to I, and structured reply submission to message I
- **AND** they MUST verify message III includes the explicit `fluxo de admissão` line
- **AND** they MUST verify the accepted reply with `agendamento` produces the expected Room-3 scheduling progression
- **AND** they MUST verify a Room-2 decision confirmation message is posted by the bot after successful decision handling

#### Scenario: Operator validates accepted immediate-admission workflow in mobile-capable client

- **WHEN** operator follows the documented Room-2 decision runbook for an accepted case routed to immediate admission
- **THEN** they MUST verify the physician can submit the structured reply using `vinda_imediata` or equivalent accepted alias
- **AND** they MUST verify the Room-2 decision confirmation echoes the normalized immediate-admission flow
- **AND** they MUST verify positive acknowledgment reaction in Room-2 remains optional and non-blocking for workflow progression

### Requirement: Manual E2E SHALL Validate Structured Reply Rejection Cases

Manual runbooks SHALL include negative checks for malformed template content, wrong reply-parent targeting, and invalid admission-flow usage.

#### Scenario: Malformed structured reply submitted

- **WHEN** a reply does not satisfy strict decision template rules
- **THEN** the decision MUST be rejected and no state/job mutation MUST occur

#### Scenario: Reply targets wrong parent event

- **WHEN** a structured reply is posted without referencing the active Room-2 case message
- **THEN** the decision MUST be rejected and no state/job mutation MUST occur

#### Scenario: Accepted reply omits required admission-flow field

- **WHEN** a physician submits `decisao=aceitar` without the required `fluxo de admissão` line
- **THEN** the decision MUST be rejected
- **AND** the correction guidance MUST show the accepted template with the missing admission-flow field restored

## ADDED Requirements

### Requirement: Manual E2E SHALL Validate Immediate Admission Operational Branch

Manual runbooks SHALL validate the non-scheduling operational branch created by physician-selected immediate admission.

#### Scenario: Immediate-admission case notifies Room-3 without scheduling

- **WHEN** operator executes manual E2E for a case accepted with `vinda_imediata`
- **THEN** Room-3 MUST receive the informational immediate-admission communication
- **AND** Room-3 MUST receive an audit acknowledgment target
- **AND** Room-3 MUST NOT receive the standard scheduling request/template combo for that case

#### Scenario: Immediate-admission case closes through Room-1 acknowledgment

- **WHEN** operator executes manual E2E for a case accepted with `vinda_imediata`
- **THEN** Room-1 MUST receive a final message equivalent to `aceito com vinda imediata autorizada`
- **AND** the case MUST remain governed by the Room-1 final acknowledgment for closure
- **AND** Room-3 acknowledgment MUST be observable as optional, not mandatory

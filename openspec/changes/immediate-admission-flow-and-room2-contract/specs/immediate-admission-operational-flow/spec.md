# immediate-admission-operational-flow Specification

## ADDED Requirements

### Requirement: Accepted Doctor Decisions SHALL Route By Normalized Admission Flow

The system SHALL route accepted Room-2 decisions according to the normalized admission-flow value selected by the physician, distinguishing scheduled cases from immediate-admission cases without requiring a second human decision step.

#### Scenario: Accepted decision selects immediate admission

- **WHEN** a Room-2 accepted decision is applied with normalized admission flow `vinda_imediata`
- **THEN** the system MUST branch to the dedicated immediate-admission workflow
- **AND** it MUST NOT open the standard Room-3 scheduling request/template flow for that case

#### Scenario: Accepted decision selects scheduled admission

- **WHEN** a Room-2 accepted decision is applied with normalized admission flow `agendamento`
- **THEN** the system MUST continue through the existing scheduling workflow
- **AND** it MUST preserve the current Room-3 scheduling combo behavior

### Requirement: Immediate Admission SHALL Notify Room-3 Without Requesting Scheduling

The system SHALL notify Room-3 when immediate admission is authorized, but SHALL treat Room-3 as an informational and audit surface rather than a scheduling gate for this branch.

#### Scenario: Room-3 notification is posted for immediate admission

- **WHEN** the immediate-admission workflow executes after a physician accepts the case
- **THEN** the system MUST post an informational Room-3 message stating that immediate admission was authorized
- **AND** the Room-3 communication MUST NOT ask Room-3 to schedule the patient
- **AND** the Room-3 communication MUST include, when available, the requested procedure, accepting physician, support recommendation, pediatric marker, and supported EDA subtype context

#### Scenario: Room-3 acknowledgment target is posted for immediate admission

- **WHEN** the immediate-admission workflow posts the informational Room-3 message
- **THEN** the system MUST also post a dedicated Room-3 acknowledgment target for auditability
- **AND** Room-3 acknowledgment MUST remain optional for workflow progression

### Requirement: Immediate Admission SHALL Notify Room-1 With Final Authorization Message

The system SHALL post a final Room-1 message for immediate-admission cases that communicates the acceptance outcome directly to the requesting side without waiting for a scheduling response.

#### Scenario: Room-1 receives immediate-admission final message

- **WHEN** the immediate-admission workflow executes after physician acceptance
- **THEN** the system MUST post a final Room-1 message equivalent to `aceito com vinda imediata autorizada`
- **AND** the final message MUST include the relevant case context already available to the workflow
- **AND** the final message MUST NOT depend on appointment date/time, location, or scheduling instructions

### Requirement: Immediate Admission Closure SHALL Depend Only On Room-1 Final Acknowledgment

The system SHALL keep Room-1 as the authoritative closure gate for immediate-admission cases, even when Room-3 audit events are missing, delayed, or fail.

#### Scenario: Room-1 acknowledges before Room-3 reacts

- **WHEN** the Room-1 final immediate-admission message receives the supported positive acknowledgment before any Room-3 reaction
- **THEN** the case MUST be eligible to close normally
- **AND** no Room-3 reaction MUST be required to finish the workflow

#### Scenario: Room-3 does not acknowledge immediate-admission message

- **WHEN** the Room-3 informational message or its acknowledgment target receives no positive reaction
- **THEN** the case MUST remain open only until the Room-1 final acknowledgment condition is satisfied
- **AND** the absence of Room-3 acknowledgment MUST NOT reopen or roll back the case

#### Scenario: Room-3 posting fails during immediate admission

- **WHEN** the system cannot post the Room-3 informational message or audit acknowledgment target
- **THEN** the workflow MUST still continue to the Room-1 final notification step
- **AND** the case MUST remain closable through the Room-1 acknowledgment path alone

### Requirement: Immediate Admission Branch SHALL Be Recoverable And Idempotent

The system SHALL preserve the selected admission-flow branch so restart recovery and duplicate-event handling resume the same operational path without producing conflicting Room-3 scheduling artifacts.

#### Scenario: Recovery resumes case after accepted immediate-admission decision

- **WHEN** runtime recovery scans a case whose physician decision was already accepted with normalized admission flow `vinda_imediata`
- **THEN** the system MUST resume the immediate-admission workflow rather than the scheduling workflow
- **AND** it MUST NOT enqueue or post the standard Room-3 scheduling request/template for that case

#### Scenario: Immediate-admission notifications are retried after partial progress

- **WHEN** the system retries the immediate-admission workflow after only part of the room notifications were posted
- **THEN** the workflow MUST remain idempotent for already-posted messages
- **AND** it MUST avoid producing duplicate final outcomes visible to operators in Room-1 or Room-3

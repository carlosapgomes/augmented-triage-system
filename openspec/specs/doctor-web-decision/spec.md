# doctor-web-decision Specification

## Purpose

Define the authenticated web workflow used by doctors to review pending cases
and submit structured medical decisions through the Django operations app.

## Requirements

### Requirement: Doctor SHALL See A Web Queue Of Pending Cases

The system SHALL provide authenticated `doctor` users a queue of cases waiting
for medical decision.

#### Scenario: Doctor opens pending queue

- **WHEN** an authenticated `doctor` requests the doctor queue page
- **THEN** the system MUST list cases currently awaiting medical decision
- **AND** each case entry MUST expose sufficient clinical summary to support
  opening the decision form

### Requirement: Doctor SHALL Submit Structured Decision Through Web Form

The system SHALL allow authenticated `doctor` users to submit the same
structured decision semantics currently enforced by the backend.

#### Scenario: Doctor accepts a case with scheduled admission flow

- **WHEN** an authenticated `doctor` submits a valid accept decision with
  required fields for scheduled flow
- **THEN** the system MUST persist the decision
- **AND** the backend MUST continue the workflow to the scheduling stage

#### Scenario: Doctor accepts a case with immediate admission flow

- **WHEN** an authenticated `doctor` submits a valid accept decision with
  immediate admission flow
- **THEN** the system MUST persist the decision
- **AND** the backend MUST continue the workflow through the
  immediate-admission branch

#### Scenario: Doctor denies a case with required reason

- **WHEN** an authenticated `doctor` submits a valid deny decision with the
  required denial reason
- **THEN** the system MUST persist the decision
- **AND** the backend MUST continue the workflow through the denial branch

#### Scenario: Doctor submits invalid structured decision

- **WHEN** an authenticated `doctor` submits a decision missing fields required
  by the chosen branch
- **THEN** the system MUST reject the submission deterministically
- **AND** no invalid workflow transition MUST be applied

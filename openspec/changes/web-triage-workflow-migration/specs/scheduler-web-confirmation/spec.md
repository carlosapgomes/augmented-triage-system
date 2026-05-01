# scheduler-web-confirmation Specification

## ADDED Requirements

### Requirement: Scheduler SHALL See A Web Queue Of Pending Scheduling Cases

The system SHALL provide authenticated `scheduler` users a queue of cases waiting for scheduling confirmation.

#### Scenario: Scheduler opens pending queue

- **WHEN** an authenticated `scheduler` requests the scheduler queue page
- **THEN** the system MUST list cases currently awaiting scheduling action
- **AND** each case entry MUST expose the data required to open the scheduling form

### Requirement: Scheduler SHALL Confirm Or Deny Scheduling Through Web Form

The system SHALL allow authenticated `scheduler` users to confirm or deny scheduling from the web app.

#### Scenario: Scheduler confirms appointment with date and time

- **WHEN** an authenticated `scheduler` submits a valid confirmation with the required date and time
- **THEN** the system MUST persist the scheduling result
- **AND** the backend MUST continue the workflow toward final NIR communication

#### Scenario: Scheduler denies appointment with required reason

- **WHEN** an authenticated `scheduler` submits a valid denial with the required reason
- **THEN** the system MUST persist the scheduling denial
- **AND** the backend MUST continue the workflow toward final NIR communication

#### Scenario: Scheduler submits invalid scheduling payload

- **WHEN** an authenticated `scheduler` submits a scheduling form missing required fields for the chosen branch
- **THEN** the system MUST reject the submission deterministically
- **AND** no invalid workflow transition MUST be applied

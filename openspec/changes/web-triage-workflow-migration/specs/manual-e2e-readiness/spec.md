# manual-e2e-readiness Specification

## MODIFIED Requirements

### Requirement: Manual E2E Runbook SHALL Define Operational Validation Flow

The project SHALL keep one human-readable manual E2E runbook that is actionable for operations and support teams before production usage.

#### Scenario: Operator performs manual E2E checks for the web workflow

- **WHEN** a team member follows the manual runbook after the migration to operational web flows
- **THEN** the runbook MUST cover NIR upload, doctor decision, scheduler confirmation, and final NIR acknowledgment through the web surfaces
- **AND** each step MUST remain concrete enough to execute without code changes

### Requirement: Manual E2E SHALL Validate Single Web-Based Doctor Decision Path

Manual runbooks SHALL validate the doctor web form as the standard human decision path.

#### Scenario: Operator validates accepted scheduled workflow through web surfaces

- **WHEN** operator follows the documented web workflow for an accepted case routed to scheduling
- **THEN** they MUST verify NIR upload, doctor web decision submission, scheduler web confirmation, and final NIR acknowledgment
- **AND** they MUST verify the expected backend workflow progression between those steps

#### Scenario: Operator validates invalid doctor form submission

- **WHEN** operator submits an invalid doctor decision payload through the web form
- **THEN** the decision MUST be rejected
- **AND** no invalid workflow mutation MUST occur

### Requirement: Manual E2E SHALL Validate Web-Based Scheduler Decision Path

Manual runbooks SHALL validate the scheduler web form as the standard human scheduling path.

#### Scenario: Operator validates invalid scheduler form submission

- **WHEN** operator submits an invalid scheduler payload through the web form
- **THEN** the scheduling action MUST be rejected
- **AND** no invalid workflow mutation MUST occur

# manual-e2e-readiness Specification

## MODIFIED Requirements

### Requirement: Manual E2E Runbook SHALL Define Operational Validation Flow

The project SHALL keep one human-readable manual E2E runbook that is actionable for operations and support teams before production usage.

#### Scenario: Role matrix is validated for manager and admin in the consolidated Django app

- **WHEN** manual validation reaches dashboard and administrative surfaces after consolidation
- **THEN** the runbook MUST include explicit checks that `manager` has read-only dashboard/reporting access
- **AND** it MUST include explicit checks that only `admin` can access user-management and prompt-management surfaces

### Requirement: Manual E2E SHALL Validate Prompt Management Authorization

Manual runbooks SHALL validate role-based authorization for prompt-management operations.

#### Scenario: Admin and manager execute prompt-management actions

- **WHEN** an `admin` performs prompt activation and a `manager` attempts the same action in the consolidated Django surface
- **THEN** admin action MUST succeed and produce an audit event
- **AND** manager action MUST be rejected with no mutation of active prompt version

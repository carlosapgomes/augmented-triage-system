# manual-e2e-readiness Specification

## MODIFIED Requirements

### Requirement: Deterministic Manual Runtime Validation

The project SHALL define deterministic smoke checks for validating live readiness of the consolidated same-host stack before full manual end-to-end testing.

#### Scenario: Pre-E2E smoke execution for consolidated stack

- **WHEN** operators prepare for manual end-to-end testing after the web consolidation
- **THEN** they MUST be able to verify service startup, database readiness, consolidated web availability, and role-zone publication expectations with documented deterministic checks

### Requirement: Manual E2E Runbook SHALL Define Operational Validation Flow

The project SHALL keep one human-readable manual E2E runbook that is actionable for operations and support teams before production usage.

#### Scenario: Operator validates remote and intranet access behavior

- **WHEN** a team member follows the runbook for the consolidated same-host topology
- **THEN** the runbook MUST include explicit checks that remote-capable roles can access the approved external path
- **AND** it MUST include explicit checks that intranet-only roles are validated through the correct internal path and denied through the wrong path

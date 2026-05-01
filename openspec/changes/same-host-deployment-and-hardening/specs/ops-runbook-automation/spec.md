# ops-runbook-automation Specification

## MODIFIED Requirements

### Requirement: Operations Runbook SHALL Define End-To-End Deploy Procedure

The project SHALL provide an operations runbook that defines the complete procedure for the consolidated same-host stack.

#### Scenario: IT executes initial installation procedure for consolidated stack

- **WHEN** hospital IT follows the documented initial installation runbook after the Django consolidation
- **THEN** the runbook MUST provide ordered commands and required preconditions for the consolidated same-host stack

### Requirement: Runbook SHALL Provide Post-Deploy Validation Checklist

The operations runbook SHALL include deterministic post-deploy checks for service health, runtime readiness, and role-zone publication behavior.

#### Scenario: Operator validates consolidated deployment outcome

- **WHEN** deployment playbook execution completes for the consolidated stack
- **THEN** the runbook MUST provide objective verification steps for process/runtime health
- **AND** it MUST include checks for internal vs remote access-path behavior by role

### Requirement: Runbook SHALL Include First-Level Troubleshooting Guidance

The operations runbook SHALL include troubleshooting guidance for common consolidated-stack publication and startup failures.

#### Scenario: Operator encounters access-publication failure

- **WHEN** a known publication or zone-hardening failure occurs
- **THEN** the runbook MUST provide immediate corrective actions for first-level support
- **AND** it MUST indicate when escalation to development is required

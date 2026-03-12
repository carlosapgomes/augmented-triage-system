# ops-runbook-automation Specification

## Purpose

TBD - created by archiving change ansible-rootless-docker-deploy. Update Purpose after archive.

## Requirements

### Requirement: Operations Runbook SHALL Define End-To-End Deploy Procedure

The project SHALL provide an operations runbook that defines the complete procedure for initial install, upgrade, and rollback using the official Ansible playbooks.

#### Scenario: TI executes initial installation procedure

- **WHEN** hospital IT follows the documented initial installation runbook
- **THEN** the runbook MUST provide ordered commands and required preconditions for successful execution
- **AND** the documented flow MUST map directly to the maintained Ansible playbooks

### Requirement: Runbook SHALL Declare Mandatory Inventory And Variables

The operations documentation SHALL explicitly define required inventory structure, mandatory variables, and secret input expectations for remote deployment.

#### Scenario: Operator prepares environment configuration

- **WHEN** an operator fills inventory and variable files before deployment
- **THEN** the runbook MUST identify which fields are mandatory
- **AND** missing mandatory values MUST be detectable before runtime deployment starts

### Requirement: Runbook SHALL Provide Post-Deploy Validation Checklist

The operations runbook SHALL include deterministic post-deploy checks for service health and runtime readiness.

#### Scenario: Operator validates deployment outcome

- **WHEN** deployment playbook execution completes
- **THEN** the runbook MUST provide objective verification steps for process/runtime health
- **AND** expected success criteria MUST be clearly defined for first-level support

### Requirement: Runbook SHALL Include First-Level Troubleshooting Guidance

The operations runbook SHALL include troubleshooting guidance for common deployment and startup failures, including escalation boundaries.

#### Scenario: Operator encounters deployment failure

- **WHEN** a known failure condition occurs during bootstrap or deploy
- **THEN** the runbook MUST provide immediate corrective actions for first-level support
- **AND** the runbook MUST indicate when escalation to development is required

### Requirement: Operations Runbook SHALL Document Three-Cutoff Summary Schedule

The operations runbook SHALL document the global Room-4 summary schedule baseline with three daily cutoffs and variable windows between consecutive cutoffs.

#### Scenario: Operator reviews periodic summary schedule contract

- **WHEN** an operator follows the official runbook for Room-4 periodic summaries
- **THEN** the runbook MUST document cutoffs `07:00`, `13:00`, and `19:00` in `America/Bahia`
- **AND** it MUST document expected windows `[19:00 previous day, 07:00)`, `[07:00, 13:00)`, and `[13:00, 19:00)`

### Requirement: Runbook SHALL Define Timezone-Coherence Validation Between Cron And Runtime

The runbook SHALL include a deterministic checklist to validate timezone coherence between cron scheduling and application runtime summary timezone configuration.

#### Scenario: Operator validates scheduler configuration after deploy

- **WHEN** deployment or upgrade completes
- **THEN** the runbook MUST require verifying both cron timezone/schedule values and runtime `SUPERVISOR_SUMMARY_TIMEZONE`
- **AND** it MUST provide explicit success criteria to confirm they are coherent

### Requirement: Runbook SHALL State Non-Catch-Up Scheduler Behavior

The runbook SHALL explicitly state that scheduler executions do not auto-backfill missed windows and SHALL define first-level operational checks for missed periods.

#### Scenario: Operator investigates a missed summary period

- **WHEN** a scheduled execution window is missed due to cron/runtime failure
- **THEN** the runbook MUST state that subsequent runs process only the immediately previous window
- **AND** it MUST direct operators to scheduler logs and enqueue evidence for diagnosis

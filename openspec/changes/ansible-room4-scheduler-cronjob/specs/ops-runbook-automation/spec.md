# Specification Delta

## ADDED Requirements

### Requirement: Operations Runbook SHALL Document Managed Room-4 Scheduler Cron

The operations runbook SHALL document that Room-4 periodic scheduler execution is managed by Ansible and runs in the installation service-user context.

#### Scenario: Operator reviews deploy operating model

- **WHEN** an operator follows the official Ansible runbook
- **THEN** the runbook MUST describe who owns scheduler cron provisioning (Ansible)
- **AND** it MUST clarify that execution occurs as the dedicated service user via rootless runtime

### Requirement: Runbook SHALL Define Scheduler Cron Verification Checklist

The runbook SHALL provide deterministic checks to confirm scheduler cron is configured and operational after deploy/upgrade.

#### Scenario: Operator validates scheduler automation after deploy

- **WHEN** deployment completes successfully
- **THEN** the runbook MUST provide steps to verify managed crontab entries and scheduler log output
- **AND** it MUST include at least one check that confirms `post_room4_summary` jobs are being enqueued as expected

### Requirement: Runbook SHALL Include First-Level Troubleshooting For Scheduler Cron

The runbook SHALL include first-level troubleshooting for rootless Docker cron execution failures in the Room-4 scheduler path.

#### Scenario: Scheduler cron exists but fails at runtime

- **WHEN** operators observe cron-trigger errors for scheduler execution
- **THEN** the runbook MUST provide immediate checks for `XDG_RUNTIME_DIR`, `DOCKER_HOST`, and compose command reachability
- **AND** it MUST define escalation criteria when first-level remediation does not restore periodic execution

# Specification Delta

## ADDED Requirements

### Requirement: Deploy Automation SHALL Converge Scheduler Cron State In Rootless Context

The rootless deploy automation SHALL converge the Room-4 scheduler cron configuration to desired state (`enabled` or `disabled`) in the same dedicated user context used for runtime operations.

#### Scenario: Deploy converges cron state together with runtime

- **WHEN** operators execute deploy or upgrade playbooks
- **THEN** automation MUST enforce scheduler cron desired state for the dedicated service user
- **AND** cron convergence MUST be repeatable across reruns without configuration drift

### Requirement: Deploy Automation SHALL Validate Summary Scheduler Prerequisites

When scheduler cron is enabled, the automation SHALL validate required Room-4 summary runtime configuration before finalizing deployment.

#### Scenario: Scheduler enabled with missing required summary env

- **WHEN** scheduler cron is enabled and required summary variables are missing or empty
- **THEN** automation MUST fail fast with actionable validation feedback
- **AND** it MUST prevent leaving a configured cron that cannot execute the scheduler correctly

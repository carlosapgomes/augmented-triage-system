# Specification Delta

## ADDED Requirements

### Requirement: Deploy Automation SHALL Require Cutoff-Hour Runtime Configuration For Scheduler

When Room-4 scheduler cron is enabled, deploy automation SHALL require a non-empty cutoff-hour configuration key for summary scheduling.

#### Scenario: Scheduler enabled with missing cutoff-hour key

- **WHEN** deploy automation runs with scheduler cron enabled and `SUPERVISOR_SUMMARY_CUTOFF_HOURS` missing or empty
- **THEN** automation MUST fail fast with actionable validation feedback
- **AND** automation MUST NOT converge a cron configuration that cannot resolve summary windows

### Requirement: Default Scheduler Cron SHALL Align With Global Three-Cutoff Baseline

The managed scheduler cron default configuration SHALL align with the global three-cutoff baseline (`07:00`, `13:00`, `19:00`) for `America/Bahia` operations.

#### Scenario: Operators use default cron inventory values on UTC host baseline

- **WHEN** operators apply deploy automation without overriding scheduler cron defaults
- **THEN** managed cron hour defaults MUST map to `07:00`, `13:00`, `19:00` in `America/Bahia`
- **AND** the resulting default cron expression MUST execute the scheduler three times per day

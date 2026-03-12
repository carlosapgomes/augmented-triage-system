# Specification Delta

## ADDED Requirements

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

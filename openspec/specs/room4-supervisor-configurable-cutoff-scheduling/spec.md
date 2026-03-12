# room4-supervisor-configurable-cutoff-scheduling Specification

## Purpose

TBD - created by archiving change room4-summary-configurable-cutoff-hours. Update Purpose after archive.

## Requirements

### Requirement: Scheduler SHALL Resolve Summary Windows From Configurable Daily Cutoffs

The scheduler SHALL compute Room-4 summary windows from a configurable list of daily cutoff hours in the configured summary timezone, where each run covers the interval from the immediately previous cutoff to the current cutoff.

#### Scenario: Morning run resolves previous-evening window

- **WHEN** cutoff hours are configured as `7,13,19` and scheduler runs at 07:00 in the configured timezone
- **THEN** the system MUST enqueue one `post_room4_summary` job for window `[19:00 previous day, 07:00 current day)`
- **AND** payload timestamps MUST be emitted as timezone-aware UTC ISO-8601 values

#### Scenario: Midday run resolves same-day morning window

- **WHEN** cutoff hours are configured as `7,13,19` and scheduler runs at 13:00 in the configured timezone
- **THEN** the system MUST enqueue one `post_room4_summary` job for window `[07:00 current day, 13:00 current day)`
- **AND** payload timestamps MUST be emitted as timezone-aware UTC ISO-8601 values

#### Scenario: Evening run resolves same-day midday window

- **WHEN** cutoff hours are configured as `7,13,19` and scheduler runs at 19:00 in the configured timezone
- **THEN** the system MUST enqueue one `post_room4_summary` job for window `[13:00 current day, 19:00 current day)`
- **AND** payload timestamps MUST be emitted as timezone-aware UTC ISO-8601 values

### Requirement: Cutoff Hour Configuration SHALL Be Normalized And Validated

The runtime configuration for summary cutoff hours SHALL accept free-order comma-separated hours, normalize to a unique sorted internal list, and reject invalid values.

#### Scenario: Free-order input is normalized

- **WHEN** runtime receives `SUPERVISOR_SUMMARY_CUTOFF_HOURS=19,7,13`
- **THEN** the effective internal cutoff sequence MUST be normalized to `[7,13,19]`
- **AND** scheduler window resolution MUST use the normalized sequence

#### Scenario: Duplicate hour is rejected

- **WHEN** runtime receives `SUPERVISOR_SUMMARY_CUTOFF_HOURS=7,13,13`
- **THEN** startup MUST fail fast with a validation error
- **AND** the error MUST indicate duplicate cutoff hour configuration

#### Scenario: Out-of-range hour is rejected

- **WHEN** runtime receives `SUPERVISOR_SUMMARY_CUTOFF_HOURS=7,24,19`
- **THEN** startup MUST fail fast with a validation error
- **AND** the error MUST indicate allowed hour range `0..23`

### Requirement: Scheduler SHALL Operate In Single-Window Mode Without Catch-Up

Each scheduler execution SHALL enqueue at most one window, corresponding only to the immediately previous cutoff interval, without automatic backfill of missed windows.

#### Scenario: Missed midday run does not trigger backfill at evening run

- **WHEN** cutoff hours are `7,13,19`, the 13:00 execution was missed, and scheduler executes at 19:00
- **THEN** the system MUST enqueue only the `[13:00, 19:00)` window
- **AND** the system MUST NOT auto-enqueue `[07:00, 13:00)` during that execution

### Requirement: Scheduler Logging SHALL Expose Resolved Window And Catch-Up Policy

Scheduler runtime logs SHALL provide deterministic observability for cutoff selection, resolved window, timezone, and explicit non-catch-up policy.

#### Scenario: Scheduler run emits structured observability fields

- **WHEN** scheduler completes one execution pass
- **THEN** logs MUST include resolved `window_start` and `window_end` in UTC
- **AND** logs MUST include the configured timezone and cutoff used for `window_end`
- **AND** logs MUST include an explicit indicator that automatic catch-up is disabled

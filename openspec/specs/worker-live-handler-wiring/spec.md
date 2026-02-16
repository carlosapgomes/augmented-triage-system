# worker-live-handler-wiring Specification

## Purpose
Define runtime worker handler coverage, failure semantics, and recovery behavior requirements.

## Requirements
### Requirement: Runtime Worker Handler Map Coverage
The system SHALL wire runtime handlers for all existing production job types required by the triage workflow.

#### Scenario: Worker starts with runtime handler map
- **WHEN** the worker process starts in live runtime mode
- **THEN** it MUST register handlers for `process_pdf_case`, `post_room2_widget`, `post_room3_request`, final-reply job variants, and `execute_cleanup`

#### Scenario: Due job dispatch in runtime mode
- **WHEN** a due queued job is claimed by the worker runtime
- **THEN** the corresponding wired handler MUST execute and preserve existing success/failure semantics

### Requirement: Existing Retry and Dead-Letter Semantics Preservation
Worker live wiring SHALL preserve the current retry scheduling and dead-letter behavior.

#### Scenario: Handler raises retriable failure
- **WHEN** a wired runtime job handler raises an error
- **THEN** worker runtime MUST apply existing retry/backoff and max-attempt dead-letter logic without behavior changes

### Requirement: Recovery Startup Integration
Worker startup SHALL execute boot reconciliation and recovery scan before entering steady-state polling.

#### Scenario: Worker boot sequence
- **WHEN** the worker process starts
- **THEN** stale running jobs MUST be reset according to existing rules and recovery enqueue logic MUST run before polling loop begins

# runtime-orchestration Specification

## Purpose
Define runtime process startup requirements and parity constraints for local and compose execution.

## Requirements
### Requirement: Bot API Runtime Serving
The system SHALL run `bot-api` as a long-lived ASGI process that serves existing webhook and login endpoints in local/dev runtime.

#### Scenario: Bot API process starts in runtime mode
- **WHEN** the `bot-api` runtime entrypoint is launched with valid settings
- **THEN** the process MUST remain running and serve `/callbacks/triage-decision` and `/auth/login`

#### Scenario: Bot API route behavior remains unchanged
- **WHEN** a valid request is sent to existing webhook or login routes
- **THEN** the response and state-transition behavior MUST match existing service contracts

### Requirement: Compose and UV Runtime Parity
The system SHALL provide behaviorally equivalent runtime startup paths for local `uv` execution and Docker Compose execution.

#### Scenario: Runtime command parity
- **WHEN** operators launch services via `uv` entrypoints or via Compose commands
- **THEN** both paths MUST execute the same application startup composition and dependency wiring

### Requirement: No Workflow Redesign During Runtime Wiring
Runtime orchestration changes SHALL NOT alter authoritative triage workflow behavior.

#### Scenario: Runtime orchestration code is introduced
- **WHEN** runtime-serving and startup wiring are implemented
- **THEN** state-machine semantics, webhook callback contract, and cleanup trigger behavior MUST remain unchanged

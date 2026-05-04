# runtime-orchestration Specification

## MODIFIED Requirements

### Requirement: Compose and UV Runtime Parity

The system SHALL provide behaviorally equivalent runtime startup paths for local execution and Docker Compose execution for the consolidated same-host stack.

#### Scenario: Consolidated runtime command parity

- **WHEN** operators launch the supported consolidated services via local entrypoints or via Compose commands
- **THEN** both paths MUST execute the same supported startup composition
- **AND** that composition MUST include the Django web application where required by the consolidated product scope

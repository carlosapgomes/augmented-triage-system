# runtime-orchestration Specification

## MODIFIED Requirements

### Requirement: Bot API Runtime Serving

The system SHALL run the supported runtime processes required for HTTP/web workflow needs while medical workflow progression remains orchestrated by the backend services.

#### Scenario: Runtime processes start in web-workflow mode

- **WHEN** the supported runtime entrypoints are launched with valid settings
- **THEN** the system MUST remain running and serve the web workflow surfaces required by the current product scope
- **AND** workflow progression MUST remain orchestrated by backend services rather than by manual message handling

### Requirement: No Workflow Redesign During Runtime Wiring

Runtime orchestration changes SHALL NOT alter authoritative triage workflow behavior.

#### Scenario: Human workflow surfaces migrate from messages to web

- **WHEN** the system replaces human message interactions with web interactions
- **THEN** the backend MUST preserve the existing state-machine semantics and branch behavior
- **AND** only the human interaction surface MUST change

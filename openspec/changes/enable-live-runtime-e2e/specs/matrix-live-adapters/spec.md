## ADDED Requirements

### Requirement: Matrix Adapter Port Implementation
The system SHALL provide concrete Matrix runtime adapters implementing required posting, replying, redaction, and MXC download ports used by existing services.

#### Scenario: Service port call uses concrete adapter
- **WHEN** application services invoke Matrix send/reply/redact/download operations in runtime mode
- **THEN** calls MUST be executed through concrete infrastructure adapters rather than placeholders

### Requirement: Bot Matrix Event Routing
The system SHALL route supported Matrix events to existing application services without introducing business logic in adapters.

#### Scenario: Room-1 PDF intake event received
- **WHEN** a valid Room-1 PDF message event is observed by runtime listener
- **THEN** the event MUST be parsed and forwarded to Room-1 intake service

#### Scenario: Room-3 scheduler reply event received
- **WHEN** a Room-3 scheduler reply is observed
- **THEN** the event MUST be forwarded to Room-3 reply service for strict template handling

#### Scenario: Thumbs-up reaction event received
- **WHEN** a thumbs-up reaction event is observed in monitored rooms
- **THEN** the event MUST be forwarded to reaction service with existing room-specific semantics

### Requirement: Unsupported Matrix Events Are Safely Ignored
The runtime listener SHALL ignore unsupported or non-actionable Matrix events deterministically.

#### Scenario: Unsupported event payload observed
- **WHEN** an event does not match supported intake/reply/reaction patterns
- **THEN** the listener MUST not mutate case workflow state and MUST continue processing subsequent events

# matrix-live-adapters Specification

## Purpose
Define runtime Matrix adapter and listener-routing requirements for live event handling.
## Requirements
### Requirement: Matrix Adapter Port Implementation
The system SHALL provide concrete Matrix runtime adapters implementing required posting, replying, redaction, MXC download, and structured Room-2 reply parsing/routing used by existing services.

#### Scenario: Service port call uses concrete adapter
- **WHEN** application services invoke Matrix send/reply/redact/download operations in runtime mode
- **THEN** calls MUST be executed through concrete infrastructure adapters rather than placeholders

#### Scenario: Room-2 structured decision reply observed
- **WHEN** the runtime listener receives a Room-2 event that is a reply candidate for decision processing
- **THEN** adapter-layer parsing MUST extract deterministic fields needed by decision routing
- **AND** the sender identity MUST be preserved for downstream actor attribution

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

#### Scenario: Room-2 structured decision reply event received
- **WHEN** a valid Room-2 structured decision reply is observed
- **THEN** the event MUST be forwarded to the doctor-decision application path using sender-derived actor identity

#### Scenario: Room-2 acknowledgment reaction event received
- **WHEN** a reaction event is observed in Room-2
- **THEN** routing MUST forward only supported positive acknowledgment reactions targeting stored Room-2 decision-confirmation messages
- **AND** unsupported Room-2 reaction keys MUST be ignored safely

### Requirement: Unsupported Matrix Events Are Safely Ignored
The runtime listener SHALL ignore unsupported or non-actionable Matrix events deterministically.

#### Scenario: Unsupported event payload observed
- **WHEN** an event does not match supported intake/reply/reaction patterns
- **THEN** the listener MUST not mutate case workflow state and MUST continue processing subsequent events

### Requirement: Room-2 Decision Reply Parent Binding SHALL Be Enforced
Runtime adapters SHALL enforce that Room-2 decision replies are bound to the active case context event via reply relation metadata.

#### Scenario: Reply relation missing or mismatched
- **WHEN** a Room-2 decision reply candidate does not reference the active root case message (message I)
- **THEN** adapter routing MUST classify it as invalid for decision execution
- **AND** no decision service call MUST be made

### Requirement: Bot Matrix Runtime SHALL Auto-Accept Invites For Configured Rooms Only

The system SHALL inspect Matrix `/sync` invite payloads and automatically join a room only when the invited `room_id` matches one of `ROOM1_ID`, `ROOM2_ID`, `ROOM3_ID`, or `ROOM4_ID`.

#### Scenario: Invite received for configured room id

- **WHEN** the bot receives an invite for a room whose id matches one configured runtime room id
- **THEN** it MUST call Matrix join for that room automatically
- **AND** it MUST emit an `INFO` log including the `room_id`

#### Scenario: Invite received for non-configured room id

- **WHEN** the bot receives an invite for a room id outside the configured runtime room ids
- **THEN** it MUST NOT call Matrix join for that room
- **AND** it MUST continue runtime processing without mutating case workflow state

### Requirement: Invite Auto-Accept Failures SHALL Be Visible And Retried On Future Polls

The system SHALL not fail silently when auto-join fails for an allowed room invite.

#### Scenario: Join request fails for allowed invite

- **WHEN** join execution for an allowed invited room fails due to transport or HTTP error
- **THEN** the bot MUST emit a `WARNING` log including the `room_id` and failure reason
- **AND** it MUST continue polling subsequent sync cycles

#### Scenario: Allowed invite remains pending after prior failure

- **WHEN** a subsequent `/sync` still contains the pending invite for the same allowed room
- **THEN** the bot MUST attempt join again automatically

### Requirement: Bot SHALL Rejoin Allowed Room On New Invite After Leave Or Kick

The auto-accept behavior SHALL remain valid for new invites to allowed rooms even if the bot had previously left or been removed.

#### Scenario: Bot removed and invited again to configured room

- **WHEN** the bot receives a new invite for an allowed room after previously not being joined to that room
- **THEN** it MUST attempt automatic join again using the same allowlist rule


# case-thread-monitoring-dashboard Specification

## MODIFIED Requirements

### Requirement: Dashboard SHALL Show Chronological Case Thread Across Rooms

The system SHALL provide a per-case detail view with a chronological sequence of workflow events even when human actions originate from the web app instead of room messages.

#### Scenario: Operator opens a case timeline containing web-origin actions

- **WHEN** an authenticated operational user opens the detail view for a case containing NIR, doctor, or scheduler actions submitted through the web app
- **THEN** the system MUST return those events in chronological order together with existing PDF, LLM, and system events
- **AND** each event MUST include actor identity, timestamp, origin/source metadata, and event type

### Requirement: Timeline SHALL Include ACKs And Human Replies

The timeline view SHALL include bot acknowledgments and human actions as first-class events to preserve end-to-end auditability.

#### Scenario: Case contains web-human actions and acknowledgments

- **WHEN** a case includes web-origin human actions together with automated acknowledgments or downstream events
- **THEN** those records MUST appear in the same timeline sequence
- **AND** they MUST remain distinguishable by event type and actor metadata

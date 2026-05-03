# full-transcript-persistence Specification

## MODIFIED Requirements

### Requirement: System SHALL Persist Full Room Message Content

The system SHALL persist full content for auditable human and system interactions linked to a case, including legacy room messages where applicable and new web-origin actions.

#### Scenario: Human workflow action is submitted from the web app

- **WHEN** a human workflow action is performed from the NIR, doctor, scheduler, or final-acknowledgment web surfaces
- **THEN** the system MUST persist auditable content linked to the case
- **AND** the persisted record MUST include actor identity, timestamp, source channel metadata, action kind, and a summarized textual payload

### Requirement: Transcript Records SHALL Be Queryable In Chronological Order

The system SHALL provide queryable transcript records per case in deterministic chronological order for monitoring and audit use.

#### Scenario: Operator requests transcript timeline for a mixed-origin case

- **WHEN** the dashboard backend queries transcript data by case id for a case containing PDF, LLM, system, and web-human events
- **THEN** the system MUST return records in chronological order
- **AND** each record MUST include source metadata that distinguishes `web`, `pdf`, `llm`, `matrix`, and `system` origins

# full-transcript-persistence Specification

## Purpose

TBD - created by archiving change build-automation-monitoring-dashboard. Update Purpose after archive.

## Requirements

### Requirement: System SHALL Persist Full Extracted Report Text

The system SHALL persist the full textual extraction of the original report for each case as auditable content retrievable by case identifier.

#### Scenario: PDF extraction completes for a case

- **WHEN** the extraction stage stores report artifacts
- **THEN** the system MUST persist the complete extracted text content for that case
- **AND** the content MUST be available for later dashboard/audit retrieval

### Requirement: System SHALL Persist Full LLM Inputs And Outputs

The system SHALL persist the complete request/response payload content for LLM1 and LLM2 interactions, including stage identity and prompt-version metadata.

#### Scenario: LLM stage executes

- **WHEN** LLM1 or LLM2 is invoked for a case
- **THEN** the system MUST persist the full input payload sent to the model
- **AND** the system MUST persist the full output payload returned by the model

### Requirement: System SHALL Persist Full Room Message Content

The system SHALL persist full content for auditable human and system interactions linked to a case, including legacy room messages where applicable and new web-origin actions.

#### Scenario: Matrix message is sent or ingested

- **WHEN** a message event is produced by bot or received from a room participant
- **THEN** the system MUST persist the full textual content linked to the case
- **AND** the persisted record MUST include room id, sender, timestamp, and message kind

#### Scenario: Human workflow action is submitted from the web app

- **WHEN** a human workflow action is performed from the NIR, doctor, scheduler, or final-acknowledgment web surfaces
- **THEN** the system MUST persist auditable content linked to the case
- **AND** the persisted record MUST include actor identity, timestamp, source channel metadata, action kind, and a summarized textual payload

### Requirement: Transcript Records SHALL Be Queryable In Chronological Order

The system SHALL provide queryable transcript records per case in deterministic chronological order for monitoring and audit use.

#### Scenario: Operator requests transcript timeline for a case

- **WHEN** the dashboard backend queries transcript data by case id
- **THEN** the system MUST return records in chronological order
- **AND** each record MUST include source channel metadata that distinguishes PDF, LLM, and Matrix origins

#### Scenario: Operator requests transcript timeline for a mixed-origin case

- **WHEN** the dashboard backend queries transcript data by case id for a case containing PDF, LLM, system, and web-human events
- **THEN** the system MUST return records in chronological order
- **AND** each record MUST include source metadata that distinguishes `web`, `pdf`, `llm`, `matrix`, and `system` origins

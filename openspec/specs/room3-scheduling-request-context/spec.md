# room3-scheduling-request-context Specification

## Purpose

Define the operational context that must accompany the first scheduling request posted to Room-3.

## Requirements

### Requirement: Room-3 Scheduling Request SHALL Surface Pediatric Context

The system SHALL include explicit pediatric context in the first scheduling request message sent to Room-3 when the structured triage payload marks the case as pediatric.

#### Scenario: Pediatric scheduling request is posted to Room-3

- **GIVEN** the structured triage payload deterministically marks the patient as pediatric
- **WHEN** the bot renders the `room3_request` message
- **THEN** the message MUST include the line `paciente pediátrico: sim`
- **AND** it MUST preserve the existing lines for `idade`, `exame solicitado`, and `aceito por`
- **AND** it MUST keep the current scheduling guidance steps unchanged

#### Scenario: Non-pediatric scheduling request preserves current context

- **GIVEN** the structured triage payload does not mark the patient as pediatric
- **WHEN** the bot renders the `room3_request` message
- **THEN** the message MUST continue to render the existing scheduling context consistently
- **AND** it MUST remain compatible with the existing Room-3 scheduling reply flow

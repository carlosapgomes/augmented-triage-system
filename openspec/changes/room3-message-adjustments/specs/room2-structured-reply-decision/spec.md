# room2-structured-reply-decision Delta Specification

## ADDED Requirements

### Requirement: Doctor Decision Snapshot SHALL Include Display Name

The system SHALL include the doctor's display name in the decision snapshot, enabling downstream services to display who accepted the case.

#### Scenario: Decision snapshot is retrieved for accepted case

- **WHEN** a case with a doctor decision is queried via `get_case_doctor_decision_snapshot`
- **THEN** the snapshot MUST include `doctor_display_name` field
- **AND** `doctor_display_name` MUST be derived from `case_matrix_message_transcripts.sender_display_name` where `message_type = 'room2_doctor_reply'`
- **AND** when no display name is available, `doctor_display_name` MUST be `None`

#### Scenario: Decision snapshot is used for Room-3 request

- **WHEN** the PostRoom3RequestService builds the Room-3 request message
- **THEN** it MUST pass `doctor_display_name` to the message template
- **AND** the message MUST display the doctor's name or fallback text when unavailable

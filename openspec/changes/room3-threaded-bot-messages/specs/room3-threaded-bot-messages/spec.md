# Specification Delta

## ADDED Requirements

### Requirement: Room-3 Bot Request and Template SHALL Be Posted in One Thread

The system SHALL publish initial bot messages in Room-3 as a single reply chain, with `room3_request` as thread root and `room3_template` as reply to that root.

#### Scenario: Posting Room-3 scheduling guidance

- **WHEN** `post_room3_request` executes for a case ready for scheduling
- **THEN** the bot MUST post `room3_request` as a root message in Room-3
- **AND** the bot MUST post `room3_template` as a reply to the `room3_request` event

### Requirement: Room-3 Template Transcript SHALL Preserve Parent Event Link

The system SHALL persist thread parent linkage for `room3_template` in case message transcript data.

#### Scenario: Persisting Room-3 template transcript row

- **WHEN** `room3_template` is posted as a reply to `room3_request`
- **THEN** the transcript row for `room3_template` MUST set `reply_to_event_id` to the `room3_request` event id

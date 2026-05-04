# manager-operational-reporting Specification

## Purpose

Define the read-only supervisory operational reporting surface for `manager` users in the consolidated Django application.

## Requirements

### Requirement: Manager SHALL Access Operational Dashboard In Read-Only Mode

The system SHALL provide authenticated `manager` users a read-only operational dashboard in the Django application.

#### Scenario: Manager opens dashboard list

- **WHEN** an authenticated `manager` requests the consolidated dashboard page
- **THEN** the system MUST return operational monitoring data
- **AND** the page MUST remain read-only

### Requirement: Manager SHALL Access Case Detail In Read-Only Mode

The system SHALL allow authenticated `manager` users to inspect case detail and timeline without gaining administrative mutation powers.

#### Scenario: Manager opens case detail

- **WHEN** an authenticated `manager` requests a case detail page
- **THEN** the system MUST return the operational summary and audit timeline
- **AND** the page MUST NOT expose admin-only management controls

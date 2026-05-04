# case-thread-monitoring-dashboard Specification

## MODIFIED Requirements

### Requirement: Dashboard SHALL List Cases For Operational Monitoring

The system SHALL provide a dashboard case list view for authenticated supervisory users in the consolidated Django application.

#### Scenario: Manager lists cases processed in a period

- **WHEN** an authenticated `manager` requests the case list filtered by date range in the consolidated Django dashboard
- **THEN** the system MUST return paginated case entries ordered by most recent activity
- **AND** each entry MUST include case id, compact operational summary, and latest activity timestamp

#### Scenario: Admin lists cases processed in a period from the consolidated dashboard

- **WHEN** an authenticated `admin` requests the case list in the consolidated Django dashboard
- **THEN** the system MUST return the same monitoring behavior available to `manager`

### Requirement: Dashboard SHALL Show Chronological Case Thread Across Rooms

The system SHALL provide a per-case detail view in the consolidated Django application for supervisory users.

#### Scenario: Manager opens a case timeline in the consolidated dashboard

- **WHEN** an authenticated `manager` opens the detail view for a case
- **THEN** the system MUST return the chronological case events with operational summary and auditability preserved

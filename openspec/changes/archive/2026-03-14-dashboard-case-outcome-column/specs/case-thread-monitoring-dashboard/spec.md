# case-thread-monitoring-dashboard Delta Specification

## MODIFIED Requirements

### Requirement: Dashboard SHALL List Cases For Operational Monitoring

The system SHALL provide a dashboard case list view for authenticated operational users, including at minimum case identifier, current status, case outcome, latest update timestamp, and pagination/filter controls for daily monitoring.

#### Scenario: Reader lists cases processed in a period

- **WHEN** an authenticated `reader` requests the case list filtered by date range
- **THEN** the system MUST return paginated case entries ordered by most recent activity
- **AND** each entry MUST include case id, status, case outcome, and latest activity timestamp

#### Scenario: Admin lists cases processed in a period

- **WHEN** an authenticated `admin` requests the case list filtered by date range
- **THEN** the system MUST return the same paginated monitoring list behavior available to `reader`
- **AND** each entry MUST include case id, status, case outcome, and latest activity timestamp

#### Scenario: Case outcome reflects operational decision state

- **WHEN** the dashboard renders case rows with decision fields already persisted
- **THEN** the system MUST display `ACEITO` when `appointment_status = confirmed`
- **AND** the system MUST display `NEGADO` when `appointment_status = denied` or `doctor_decision = deny`
- **AND** the system MUST display `EM_ANDAMENTO` when no final accepted/denied outcome is available yet

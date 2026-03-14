# case-thread-monitoring-dashboard Delta Specification

## MODIFIED Requirements

### Requirement: Dashboard SHALL List Cases For Operational Monitoring

The system SHALL provide a dashboard case list view for authenticated operational users, including at minimum case identifier, current status, case outcome, latest update timestamp, pagination/filter controls for daily monitoring, and aggregated search totals by operational outcome.

#### Scenario: Reader lists cases processed in a period

- **WHEN** an authenticated `reader` requests the case list filtered by date range
- **THEN** the system MUST return paginated case entries ordered by most recent activity
- **AND** each entry MUST include case id, status, case outcome, and latest activity timestamp

#### Scenario: Admin lists cases processed in a period

- **WHEN** an authenticated `admin` requests the case list filtered by date range
- **THEN** the system MUST return the same paginated monitoring list behavior available to `reader`
- **AND** each entry MUST include case id, status, case outcome, and latest activity timestamp

#### Scenario: Dashboard shows aggregated totals for the full filtered search result

- **WHEN** an authenticated operational user executes a case search with filters and pagination
- **THEN** the dashboard MUST display, below the table, aggregated totals for `total de casos`, `ACEITO`, `NEGADO`, and `EM_ANDAMENTO` (em processamento)
- **AND** these totals MUST be calculated over the full filtered result set, not only the current page

#### Scenario: Initial dashboard load shows totals for the default current-day search

- **WHEN** an authenticated operational user opens `GET /dashboard/cases` without explicit date filters
- **THEN** the system MUST apply the default current-day period filter
- **AND** the dashboard MUST display the same aggregated totals for that initial search

#### Scenario: Search with no matching cases shows zeroed totals

- **WHEN** a search filter combination returns no matching cases
- **THEN** the dashboard MUST still render the totals block below the table
- **AND** the values for `total de casos`, `ACEITO`, `NEGADO`, and `EM_ANDAMENTO` MUST be `0`

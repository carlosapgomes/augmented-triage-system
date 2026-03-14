# case-thread-monitoring-dashboard Specification

## Purpose

TBD - created by archiving change build-automation-monitoring-dashboard. Update Purpose after archive.

## Requirements

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

### Requirement: Dashboard SHALL Show Chronological Case Thread Across Rooms

The system SHALL provide a per-case detail view with both `Fluxo por Etapas` and `Histórico Completo`, including the chronological sequence of messages/events across Room-1, Room-2, and Room-3 with visual room identification for authenticated operational users.

#### Scenario: Reader opens a case timeline

- **WHEN** an authenticated `reader` opens the detail view for a case
- **THEN** the system MUST return events ordered chronologically for that case
- **AND** each event MUST include room identifier, timestamp, actor/sender, and event type

#### Scenario: Admin opens a case timeline

- **WHEN** an authenticated `admin` opens the detail view for a case
- **THEN** the system MUST return events ordered chronologically for that case
- **AND** each event MUST include room identifier, timestamp, actor/sender, and event type

#### Scenario: Reader accesses full event content in Histórico Completo

- **WHEN** an authenticated `reader` opens the `Histórico Completo` view for a case with truncated excerpts
- **THEN** the system MUST provide a per-event control to expand and collapse full content text
- **AND** the full content shown MUST use the persisted event transcript/payload for that event

#### Scenario: Fluxo por Etapas shows PDF report toggle in the case details card

- **WHEN** an authenticated operational user opens `Fluxo por Etapas` for a case that has `pdf_report_extracted`
- **THEN** the top `Detalhe do Caso` card MUST show a control labeled to exibir/ocultar relatório PDF extraído
- **AND** the extracted PDF report text MUST start collapsed by default

#### Scenario: User toggles report visibility in Fluxo por Etapas

- **WHEN** the user clicks the report control in the top `Detalhe do Caso` card
- **THEN** the system MUST expand the same card and reveal the full persisted `pdf_report_extracted` text
- **AND** a subsequent click MUST collapse and hide the report text again

### Requirement: Timeline SHALL Include ACKs And Human Replies

The timeline view SHALL include bot acknowledgments and user replies as first-class events to preserve end-to-end auditability.

#### Scenario: Case contains ACK and human response events

- **WHEN** a case includes acknowledgments and human replies in its flow
- **THEN** those events MUST appear in the same timeline sequence
- **AND** they MUST remain distinguishable by event type and actor metadata

### Requirement: Dashboard Pages SHALL Be Accessible Through Web Session Authentication

The system SHALL allow dashboard pages to be accessed through authenticated browser session flow without requiring manual Bearer header injection.

#### Scenario: Authenticated browser session opens dashboard

- **WHEN** a logged-in user with role `reader` or `admin` requests `GET /dashboard/cases`
- **THEN** the system MUST authorize the request from session state
- **AND** the system MUST render dashboard HTML without requiring explicit Authorization header

### Requirement: Dashboard Monitoring SHALL Work In Standalone Installed Context

The system SHALL preserve dashboard monitoring behavior when pages are opened from an installed standalone app context on supported mobile platforms.

#### Scenario: Reader opens installed app with active session

- **WHEN** an authenticated `reader` launches the installed app entry pointing to `/dashboard/cases`
- **THEN** the system MUST render the same monitoring list behavior available in regular browser context
- **AND** case navigation to `/dashboard/cases/{case_id}` MUST remain available

#### Scenario: Admin opens installed app with active session

- **WHEN** an authenticated `admin` launches the installed app entry pointing to `/dashboard/cases`
- **THEN** the system MUST render the same monitoring behavior available in regular browser context
- **AND** role-based navigation visibility MUST remain consistent with existing authorization rules

### Requirement: Dashboard Monitoring Data SHALL Remain Consistent Across Desktop And Mobile

The system SHALL keep case list/detail monitoring data consistent regardless of access from desktop browser or mobile standalone context.

#### Scenario: Same case is inspected on desktop and mobile

- **WHEN** the same authenticated operational user inspects a case list/detail in desktop browser and in mobile standalone context
- **THEN** case status, outcome, and timeline ordering MUST remain semantically equivalent
- **AND** differences MUST be limited to presentation/layout adaptations for viewport size

# case-thread-monitoring-dashboard Specification

## Purpose

TBD - created by archiving change build-automation-monitoring-dashboard. Update Purpose after archive.

## Requirements

### Requirement: Dashboard SHALL List Cases For Operational Monitoring

The system SHALL provide a dashboard case list view for authenticated operational users, including at minimum case identifier, a compact operational summary, current status, pending stage when the case is still in progress, final outcome when the case is concluded, latest update timestamp, and pagination/filter controls for daily monitoring.

#### Scenario: Manager lists cases processed in a period

- **WHEN** an authenticated `manager` requests the case list filtered by date range in the consolidated Django dashboard
- **THEN** the system MUST return paginated case entries ordered by most recent activity
- **AND** each entry MUST include case id, compact operational summary, and latest activity timestamp

#### Scenario: Admin lists cases processed in a period from the consolidated dashboard

- **WHEN** an authenticated `admin` requests the case list in the consolidated Django dashboard
- **THEN** the system MUST return the same monitoring behavior available to `manager`
- **AND** each entry MUST include case id, compact operational summary, and latest activity timestamp

#### Scenario: Case row reflects pending immediate-admission branch without concluding the case

- **WHEN** the dashboard renders a case whose physician already selected `vinda_imediata` but whose Room-1 final acknowledgment has not yet occurred
- **THEN** the system MUST display the case as `EM_ANDAMENTO`
- **AND** it MUST expose a pending-stage summary equivalent to awaiting Room-1 acknowledgment/science
- **AND** it MUST expose the immediate-admission branch as operational context
- **AND** it MUST NOT display final outcome `VINDA_IMEDIATA` for that case yet

#### Scenario: Case row reflects concluded immediate-admission outcome

- **WHEN** the dashboard renders a case that concluded through the immediate-admission branch after Room-1 final acknowledgment
- **THEN** the system MUST display final outcome `VINDA_IMEDIATA`
- **AND** it MUST NOT collapse that concluded outcome into generic `ACEITO`

#### Scenario: Legacy case lacks immediate-admission branch evidence

- **WHEN** the dashboard renders a historical case that predates persisted immediate-admission observability data
- **THEN** the system MUST preserve deterministic status/outcome rendering from available persisted evidence
- **AND** any unavailable branch semantics MUST render as `não aplicável` or `indisponível`, not as an inferred immediate-admission classification

### Requirement: Dashboard SHALL Show Chronological Case Thread Across Rooms

The system SHALL provide a per-case detail view with both `Fluxo por Etapas` and `Histórico Completo`, including the chronological sequence of messages/events across Room-1, Room-2, and Room-3 with visual room identification for authenticated operational users, even when human workflow actions originate from the web app.

#### Scenario: Manager opens a case timeline in the consolidated dashboard

- **WHEN** an authenticated `manager` opens the detail view for a case
- **THEN** the system MUST return events ordered chronologically for that case
- **AND** each event MUST include room identifier, timestamp, actor/sender, and event type

#### Scenario: Admin opens a case timeline

- **WHEN** an authenticated `admin` opens the detail view for a case
- **THEN** the system MUST return events ordered chronologically for that case
- **AND** each event MUST include room identifier, timestamp, actor/sender, and event type

#### Scenario: Operator opens a case timeline containing web-origin actions

- **WHEN** an authenticated operational user opens the detail view for a case containing NIR, doctor, or scheduler actions submitted through the web app
- **THEN** the system MUST return those events in chronological order together with existing PDF, LLM, and system events
- **AND** each event MUST include actor identity, timestamp, origin/source metadata, and event type

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

The timeline view SHALL include bot acknowledgments and human actions as first-class events to preserve end-to-end auditability.

#### Scenario: Case contains ACK and human response events

- **WHEN** a case includes acknowledgments and human replies in its flow
- **THEN** those events MUST appear in the same timeline sequence
- **AND** they MUST remain distinguishable by event type and actor metadata

#### Scenario: Case contains web-human actions and acknowledgments

- **WHEN** a case includes web-origin human actions together with automated acknowledgments or downstream events
- **THEN** those records MUST appear in the same timeline sequence
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

### Requirement: Dashboard SHALL Support Operational Filters And Totals

The system SHALL provide dashboard filters and totals that distinguish backlog state from final outcomes, allowing operators to monitor where cases are currently blocked as well as how they eventually concluded.

#### Scenario: Operator filters by pending stage and immediate-admission branch

- **WHEN** an authenticated operational user filters the dashboard for cases in progress that belong to the `vinda_imediata` branch
- **THEN** the system MUST return only cases that are still open and already associated with the immediate-admission branch
- **AND** the filtered result MUST preserve the visible pending-stage summary for each returned case

#### Scenario: Dashboard totals separate backlog from concluded outcomes

- **WHEN** the dashboard renders totals for the current filtered result set
- **THEN** the totals MUST distinguish at minimum:
  - cases still `EM_ANDAMENTO`;
  - subtotal by pending stage;
  - subtotal of pending cases already in the `vinda_imediata` branch;
  - concluded `ACEITO` cases;
  - concluded `VINDA_IMEDIATA` cases;
  - concluded `NEGADO` cases

### Requirement: Dashboard SHALL Show Operational Summary In Case Detail

The system SHALL provide an operational summary block in the per-case detail view that makes the current stop point understandable without requiring the operator to infer workflow state only from the chronological timeline.

#### Scenario: Operator opens detail for in-progress immediate-admission case

- **WHEN** an authenticated operational user opens the detail view for a case whose physician selected `vinda_imediata` and that still awaits Room-1 final acknowledgment
- **THEN** the detail view MUST show that the case remains `EM_ANDAMENTO`
- **AND** it MUST show the current pending stage equivalent to awaiting Room-1 acknowledgment/science
- **AND** it MUST show the selected branch as `vinda_imediata`
- **AND** it MUST keep the chronological timeline available below the summary

#### Scenario: Operator opens detail for concluded immediate-admission case

- **WHEN** an authenticated operational user opens the detail view for a case that already concluded through the immediate-admission branch
- **THEN** the detail view MUST show final outcome `VINDA_IMEDIATA`
- **AND** it MUST no longer present the case as operationally pending
- **AND** it MUST keep the chronological timeline available for auditability

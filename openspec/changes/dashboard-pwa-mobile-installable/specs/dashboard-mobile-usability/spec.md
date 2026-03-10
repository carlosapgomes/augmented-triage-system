# dashboard-mobile-usability Delta Specification

## ADDED Requirements

### Requirement: Case List View SHALL Be Mobile-Friendly For Reader Workflow

The system SHALL provide a mobile-optimized experience for `GET /dashboard/cases` focused on operational reader usage while preserving monitoring information integrity.

#### Scenario: Reader opens case list on small viewport

- **WHEN** an authenticated `reader` opens `/dashboard/cases` on a mobile viewport
- **THEN** the list view MUST keep case identification, status, outcome, and latest activity clearly readable
- **AND** key interactions (filters, pagination, case opening) MUST remain usable with touch input

#### Scenario: Reader applies filters on mobile

- **WHEN** an authenticated `reader` submits date/status filters from a mobile device
- **THEN** the filtered result MUST preserve current functional behavior and totals semantics
- **AND** the interface MUST avoid requiring precision desktop-only interactions to complete filtering

### Requirement: Case Detail View SHALL Be Mobile-Friendly For Reader Workflow

The system SHALL provide a mobile-optimized experience for `GET /dashboard/cases/{case_id}` in both `Fluxo por Etapas` and `Histórico Completo` modes.

#### Scenario: Reader opens case detail on small viewport

- **WHEN** an authenticated `reader` opens `/dashboard/cases/{case_id}` on a mobile viewport
- **THEN** event chronology and room context MUST remain understandable without desktop layout assumptions
- **AND** controls for toggling views and expanding content MUST remain accessible by touch

#### Scenario: Reader alternates between thread and pure views on mobile

- **WHEN** an authenticated `reader` switches between `view=thread` and `view=pure` on mobile
- **THEN** the system MUST preserve existing data fidelity and authorization behavior
- **AND** the mobile layout MUST keep both modes operationally readable

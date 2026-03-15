# dashboard-mobile-usability Specification

## Purpose

TBD - created by archiving change dashboard-pwa-mobile-installable. Update Purpose after archive.

## Requirements

### Requirement: Case List View SHALL Be Mobile-Friendly For Reader Workflow

The system SHALL provide a mobile-optimized experience for `GET /dashboard/cases` focused on operational reader usage while preserving the expanded monitoring semantics for current status, pending stage, operational branch, final outcome, and totals integrity.

#### Scenario: Reader opens case list on small viewport

- **WHEN** an authenticated `reader` opens `/dashboard/cases` on a mobile viewport
- **THEN** the list view MUST keep case identification and the compact operational summary clearly readable
- **AND** that compact summary MUST preserve whether the case is still `EM_ANDAMENTO` or already concluded
- **AND** when the case is still in progress, the mobile layout MUST keep the pending stage understandable without desktop-only hover or expansion
- **AND** key interactions such as filters, pagination, and case opening MUST remain usable with touch input

#### Scenario: Reader applies operational filters on mobile

- **WHEN** an authenticated `reader` submits filters from a mobile device using status, pending-stage, branch, or final-outcome controls
- **THEN** the filtered result MUST preserve the same monitoring semantics and totals behavior available on desktop
- **AND** the interface MUST avoid requiring precision desktop-only interactions to complete the filtering flow

### Requirement: Case Detail View SHALL Be Mobile-Friendly For Reader Workflow

The system SHALL provide a mobile-optimized experience for `GET /dashboard/cases/{case_id}` in both `Fluxo por Etapas` and `Histórico Completo`, while preserving the operational summary needed to understand where an in-progress case is currently blocked.

#### Scenario: Reader opens case detail on small viewport

- **WHEN** an authenticated `reader` opens `/dashboard/cases/{case_id}` on a mobile viewport
- **THEN** the operational summary block MUST keep current status, pending stage, branch, and final-outcome information understandable without desktop layout assumptions
- **AND** event chronology and room context MUST remain understandable
- **AND** controls for toggling views and expanding content MUST remain accessible by touch

#### Scenario: Reader alternates between thread and pure views on mobile

- **WHEN** an authenticated `reader` switches between `view=thread` and `view=pure` on mobile
- **THEN** the system MUST preserve existing data fidelity and authorization behavior
- **AND** the mobile layout MUST keep both modes operationally readable
- **AND** the operational summary block MUST remain visible or equivalently accessible in both modes

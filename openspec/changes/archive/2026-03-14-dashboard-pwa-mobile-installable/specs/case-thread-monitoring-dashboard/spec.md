# case-thread-monitoring-dashboard Delta Specification

## ADDED Requirements

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

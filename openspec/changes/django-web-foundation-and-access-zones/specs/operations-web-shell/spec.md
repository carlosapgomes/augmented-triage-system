# operations-web-shell Specification

## MODIFIED Requirements

### Requirement: Web Pages SHALL Share A Unified Operations Shell

The system SHALL render authenticated Django operations pages within one shared shell containing consistent navigation, visual hierarchy, and session framing.

#### Scenario: Authenticated user opens a role-specific page

- **WHEN** an authenticated operational user requests a page in the Django operations app
- **THEN** the response MUST use the shared shell layout
- **AND** the shell MUST include a visible logout action

### Requirement: Shell Navigation SHALL Be Role-Aware

The system SHALL render navigation options according to the five operational roles.

#### Scenario: NIR user renders authenticated shell

- **WHEN** an authenticated `nir` user renders the shell
- **THEN** the shell MUST expose only NIR-relevant navigation
- **AND** it MUST NOT expose doctor, scheduler, manager, or admin-only navigation

#### Scenario: Doctor user renders authenticated shell

- **WHEN** an authenticated `doctor` user renders the shell
- **THEN** the shell MUST expose only doctor-relevant navigation

#### Scenario: Scheduler user renders authenticated shell

- **WHEN** an authenticated `scheduler` user renders the shell
- **THEN** the shell MUST expose only scheduler-relevant navigation

#### Scenario: Manager user renders authenticated shell

- **WHEN** an authenticated `manager` user renders the shell
- **THEN** the shell MUST expose dashboard/reporting navigation
- **AND** it MUST NOT expose admin-only user/prompt/system management navigation

#### Scenario: Admin user renders authenticated shell

- **WHEN** an authenticated `admin` user renders the shell
- **THEN** the shell MUST expose administrative navigation appropriate to system management

### Requirement: Unauthorized Shell Access SHALL Be Rejected Deterministically

The system SHALL enforce authorization for authenticated shell pages using server-side checks.

#### Scenario: Manager requests admin-only management page

- **WHEN** an authenticated `manager` requests a page reserved for `admin`
- **THEN** the system MUST deny access with authorization failure

#### Scenario: NIR requests scheduler page

- **WHEN** an authenticated `nir` user requests a scheduler-only page
- **THEN** the system MUST deny access with authorization failure

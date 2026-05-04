# operations-web-shell Specification

## MODIFIED Requirements

### Requirement: Shell Navigation SHALL Be Role-Aware

The system SHALL render navigation options according to the final consolidated Django role permissions.

#### Scenario: Manager navigates authenticated shell

- **WHEN** an authenticated `manager` renders any shell page
- **THEN** the shell MUST include dashboard/reporting navigation
- **AND** the shell MUST NOT include prompt-admin navigation
- **AND** the shell MUST NOT include user-admin navigation

#### Scenario: Admin navigates authenticated shell

- **WHEN** an authenticated `admin` renders any shell page
- **THEN** the shell MUST include dashboard/reporting, prompt-admin, and user-admin navigation

### Requirement: Unauthorized Shell Access SHALL Be Rejected Deterministically

The system SHALL enforce authorization for consolidated shell pages using server-side checks.

#### Scenario: Manager requests admin prompts HTML page in the consolidated shell

- **WHEN** an authenticated `manager` requests an admin prompts page
- **THEN** the system MUST deny access with authorization failure
- **AND** no prompt state MUST change

#### Scenario: Manager requests admin users HTML page in the consolidated shell

- **WHEN** an authenticated `manager` requests an admin users page
- **THEN** the system MUST deny access with authorization failure
- **AND** no user-account state MUST change

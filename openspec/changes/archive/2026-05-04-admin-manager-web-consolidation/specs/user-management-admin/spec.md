# user-management-admin Specification

## MODIFIED Requirements

### Requirement: Admin SHALL Access User Management Surface

The system SHALL provide the authenticated user-management surface as part of the consolidated Django administrative area for users with role `admin`.

#### Scenario: Admin opens user management page in the consolidated Django app

- **WHEN** an authenticated `admin` requests the user-management page in the consolidated Django admin area
- **THEN** the system MUST return the user-management HTML page with management controls

#### Scenario: Manager requests user management page

- **WHEN** an authenticated `manager` requests the user-management page
- **THEN** the system MUST reject access with authorization failure

### Requirement: Admin SHALL Manage All Supported Operational Roles

The system SHALL allow an authenticated `admin` to create and maintain user accounts with roles `nir`, `doctor`, `scheduler`, `manager`, and `admin`.

#### Scenario: Admin creates an operational account with any supported role

- **WHEN** an authenticated `admin` submits a valid create-user request for `nir`, `doctor`, `scheduler`, `manager`, or `admin`
- **THEN** the system MUST persist the user with the selected supported role

#### Scenario: Admin changes the role of an existing user

- **WHEN** an authenticated `admin` updates the role of an existing user to another supported role
- **THEN** the system MUST persist the new supported role deterministically

### Requirement: Legacy Supervisory Role Mapping SHALL Migrate Deterministically

The system SHALL treat the legacy role mapping as `reader -> manager` and `admin -> admin` during the consolidated administrative model.

#### Scenario: Legacy reader account is represented in the new role model

- **WHEN** the consolidated user-management model resolves a legacy `reader` account
- **THEN** the account MUST be treated as `manager`

#### Scenario: Legacy admin account is represented in the new role model

- **WHEN** the consolidated user-management model resolves a legacy `admin` account
- **THEN** the account MUST remain `admin`

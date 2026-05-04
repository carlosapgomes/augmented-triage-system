# user-management-admin Specification

## Purpose

Define user-management capabilities for administrative users in the operations dashboard, including lifecycle actions, safety invariants, and auditability.

## Requirements

### Requirement: Admin SHALL Access User Management Surface

The system SHALL provide an authenticated administrative user-management surface
at `GET /admin/users` for users with role `admin`.

#### Scenario: Admin opens user management page

- **WHEN** an authenticated `admin` requests `GET /admin/users`
- **THEN** the system MUST return the user-management HTML page
- **AND** the page MUST include user listing and management controls

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

#### Scenario: Duplicate email is submitted

- **WHEN** an authenticated `admin` submits a create-user request with an email that already exists after normalization
- **THEN** the system MUST reject the request
- **AND** no new user row MUST be created

### Requirement: Admin SHALL Manage User Lifecycle States

The system SHALL support lifecycle actions for existing users: block, reactivate,
and remove, with explicit account states.

#### Scenario: Admin blocks an active user

- **WHEN** an authenticated `admin` blocks a target user in `active` state
- **THEN** the target user state MUST become `blocked`
- **AND** the target user MUST be prevented from authenticating new sessions
- **AND** active sessions/tokens for the target user MUST be revoked

#### Scenario: Admin reactivates a blocked user

- **WHEN** an authenticated `admin` reactivates a target user in `blocked` state
- **THEN** the target user state MUST become `active`

#### Scenario: Admin removes a user

- **WHEN** an authenticated `admin` removes a target user
- **THEN** the target user state MUST become `removed`
- **AND** the user record MUST be retained as soft-deleted audit history
- **AND** active sessions/tokens for the target user MUST be revoked

### Requirement: Administrative Safety Invariants SHALL Be Enforced

The system SHALL enforce safety invariants that prevent administrative lockout
or unsafe self-management actions.

#### Scenario: Admin attempts self-block or self-remove

- **WHEN** an authenticated `admin` attempts to block or remove their own account
- **THEN** the system MUST reject the action
- **AND** no account state MUST change

#### Scenario: Action would leave zero active admins

- **WHEN** an authenticated `admin` attempts an action that would leave no active `admin` accounts
- **THEN** the system MUST reject the action
- **AND** at least one active `admin` account MUST remain

### Requirement: User Management Actions SHALL Be Auditable

The system SHALL append audit events for user-management actions with actor and
target metadata.

#### Scenario: User-management action succeeds

- **WHEN** an authenticated `admin` successfully creates, blocks, reactivates, removes, or role-changes a user
- **THEN** the system MUST append an audit event
- **AND** the event MUST include actor identity and target user metadata
- **AND** the event MUST include action type and resulting state when applicable

### Requirement: Legacy Supervisory Role Mapping SHALL Migrate Deterministically

The system SHALL treat the legacy role mapping as `reader -> manager` and `admin -> admin` during the consolidated administrative model.

#### Scenario: Legacy reader account is represented in the new role model

- **WHEN** the consolidated user-management model resolves a legacy `reader` account
- **THEN** the account MUST be treated as `manager`

#### Scenario: Legacy admin account is represented in the new role model

- **WHEN** the consolidated user-management model resolves a legacy `admin` account
- **THEN** the account MUST remain `admin`

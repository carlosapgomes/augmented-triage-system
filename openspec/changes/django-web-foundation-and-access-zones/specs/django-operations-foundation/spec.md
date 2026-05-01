# django-operations-foundation Specification

## ADDED Requirements

### Requirement: System SHALL Provide A Separate Django Operations App

The system SHALL provide a separate Django-based operations web application, deployed on the same host as the ATS runtime, without requiring an immediate rewrite of the existing clinical orchestration services.

#### Scenario: Operator opens the Django operations service

- **WHEN** the Django operations app is started in the repository runtime
- **THEN** the system MUST serve HTTP responses successfully
- **AND** the app MUST remain logically separated from the existing FastAPI runtime surface

### Requirement: System SHALL Maintain Individual Local Accounts For Operational Users

The system SHALL authenticate operational users with individual local accounts so each human action remains attributable to a specific person.

#### Scenario: Operational account is created for one person

- **WHEN** the system persists a local operational user account
- **THEN** the account MUST represent one individual person
- **AND** the account MUST use a unique normalized email identity

### Requirement: System SHALL Support Five Operational Roles

The system SHALL support the roles `nir`, `doctor`, `scheduler`, `manager`, and `admin` in the Django operations app.

#### Scenario: User role is loaded for authorization

- **WHEN** the system resolves an authenticated operational user
- **THEN** the user MUST have exactly one supported operational role
- **AND** unsupported role values MUST be rejected deterministically

### Requirement: System SHALL Redirect Users To Role-Specific Entry Surfaces

The system SHALL route authenticated users to a role-specific initial surface after successful login.

#### Scenario: NIR user logs in successfully

- **WHEN** an authenticated user with role `nir` completes login
- **THEN** the system MUST redirect the user to the NIR web surface

#### Scenario: Doctor user logs in successfully

- **WHEN** an authenticated user with role `doctor` completes login
- **THEN** the system MUST redirect the user to the doctor web surface

#### Scenario: Scheduler user logs in successfully

- **WHEN** an authenticated user with role `scheduler` completes login
- **THEN** the system MUST redirect the user to the scheduler web surface

#### Scenario: Manager user logs in successfully

- **WHEN** an authenticated user with role `manager` completes login
- **THEN** the system MUST redirect the user to the manager dashboard/reporting surface

#### Scenario: Admin user logs in successfully

- **WHEN** an authenticated user with role `admin` completes login
- **THEN** the system MUST redirect the user to the admin surface

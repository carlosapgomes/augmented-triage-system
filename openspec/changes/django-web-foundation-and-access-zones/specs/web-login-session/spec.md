# web-login-session Specification

## MODIFIED Requirements

### Requirement: System SHALL Provide Browser Login Entry Point

The system SHALL expose a browser-accessible landing/login flow so operational users can authenticate without manually sending API headers.

#### Scenario: Anonymous user opens root path

- **WHEN** an unauthenticated user requests the root entry of the Django operations app
- **THEN** the system MUST redirect to the login page

#### Scenario: Anonymous user opens login page

- **WHEN** an unauthenticated user requests the login page
- **THEN** the system MUST render an HTML login form with `email` and `password` fields

### Requirement: System SHALL Create Web Session On Successful Login

The system SHALL authenticate credentials and create a browser session for the Django operations app.

#### Scenario: Valid credentials submitted in login form

- **WHEN** a user submits valid credentials to the Django login form
- **THEN** the system MUST authenticate the user
- **AND** the system MUST create an authenticated browser session
- **AND** the system MUST redirect the user according to the authenticated role

#### Scenario: Invalid credentials submitted in login form

- **WHEN** a user submits invalid credentials to the Django login form
- **THEN** the system MUST return login error feedback in HTML
- **AND** the system MUST NOT create an authenticated session

### Requirement: System SHALL Destroy Web Session On Logout

The system SHALL provide explicit logout that invalidates browser session access.

#### Scenario: Authenticated user logs out

- **WHEN** an authenticated user submits logout from the Django operations app
- **THEN** the system MUST clear the authenticated session
- **AND** the system MUST redirect to the login page

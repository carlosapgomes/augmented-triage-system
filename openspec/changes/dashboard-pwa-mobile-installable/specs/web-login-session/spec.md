# web-login-session Delta Specification

## ADDED Requirements

### Requirement: Web Session Flow SHALL Support Installed App Start URL

The system SHALL preserve existing browser-first session semantics when access starts from the installed app entry URL `/dashboard/cases`.

#### Scenario: Unauthenticated launch from installed app

- **WHEN** an unauthenticated user launches the installed app entry that requests `/dashboard/cases`
- **THEN** the system MUST redirect to `GET /login`
- **AND** the user MUST authenticate through the same HTML login flow used by browser access

#### Scenario: Authenticated launch from installed app

- **WHEN** an authenticated user launches the installed app entry that requests `/dashboard/cases`
- **THEN** the system MUST authorize the request using existing session cookie behavior
- **AND** the system MUST render dashboard HTML without requiring bearer header injection

#### Scenario: Session becomes invalid before launch

- **WHEN** a previously authenticated installed-app launch presents invalid/expired session state
- **THEN** the system MUST reject the session according to existing auth guard rules
- **AND** the user MUST be redirected to `GET /login`

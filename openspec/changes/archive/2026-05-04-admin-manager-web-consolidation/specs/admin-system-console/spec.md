# admin-system-console Specification

## ADDED Requirements

### Requirement: Admin SHALL Access Consolidated Django System Console

The system SHALL provide authenticated `admin` users a consolidated Django administrative console for system management surfaces.

#### Scenario: Admin opens consolidated system console

- **WHEN** an authenticated `admin` enters the administrative area of the Django app
- **THEN** the system MUST provide entry navigation to supported administrative system surfaces

### Requirement: Non-Admin Roles SHALL Not Access The Consolidated System Console

The system SHALL reject access to the consolidated Django administrative console for non-admin roles.

#### Scenario: Manager requests admin console

- **WHEN** an authenticated `manager` requests the consolidated admin system console
- **THEN** the system MUST reject access with authorization failure

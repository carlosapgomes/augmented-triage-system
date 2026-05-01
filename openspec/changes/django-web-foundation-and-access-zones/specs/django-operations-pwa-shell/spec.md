# django-operations-pwa-shell Specification

## ADDED Requirements

### Requirement: Remote-Capable Django Operations Roles SHALL Have An Installable PWA Shell

The system SHALL expose installability metadata and assets from the Django operations shell so supported mobile browsers can install it for the remote-capable roles `doctor`, `manager`, and `admin`.

#### Scenario: Browser loads Django operations shell metadata for a remote-capable role

- **WHEN** a browser loads the Django operations shell for `doctor`, `manager`, or `admin`
- **THEN** the HTML MUST include a manifest reference and mobile installability metadata

#### Scenario: Browser fetches Django operations manifest for the remote shell

- **WHEN** a browser requests the PWA manifest resource for the remote-capable Django operations shell
- **THEN** the system MUST return a valid manifest document
- **AND** the manifest MUST describe standalone display behavior for the Django operations shell

### Requirement: Django Operations PWA SHALL Remain Online-Only

The system SHALL preserve the current project posture that operational web access is online-only.

#### Scenario: User navigates while connected

- **WHEN** the installed Django operations PWA is opened with network connectivity
- **THEN** the application MUST use live network responses as the authoritative source

#### Scenario: User opens the installed PWA while offline

- **WHEN** the installed Django operations PWA is opened without network connectivity
- **THEN** the system MUST NOT present cached operational content as supported offline behavior
- **AND** the result MUST follow normal network failure semantics

### Requirement: Remote-Capable Django Operations Shell SHALL Provide Role-Aware Installed Entry Behavior

The system SHALL preserve role-aware navigation when the installed shell is opened.

#### Scenario: Authenticated installed app launch resumes remote-capable user session

- **WHEN** an authenticated `doctor`, `manager`, or `admin` user opens the installed Django operations PWA
- **THEN** the system MUST restore the session according to normal web session rules
- **AND** the user MUST land in the role-appropriate surface

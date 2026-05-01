# role-zoned-access-control Specification

## ADDED Requirements

### Requirement: Intranet-Only Roles SHALL Be Restricted By Network Zone

The system SHALL restrict the `nir` and `scheduler` roles to authorized intranet network ranges.

#### Scenario: NIR user accesses from authorized intranet IP

- **WHEN** an authenticated `nir` user requests an allowed page from an IP inside the configured intranet CIDR allowlist
- **THEN** the system MUST allow the request to continue

#### Scenario: Scheduler user accesses from unauthorized external IP

- **WHEN** an authenticated `scheduler` user requests an allowed page from an IP outside the configured intranet CIDR allowlist
- **THEN** the system MUST reject the request

### Requirement: Intranet-Only Roles SHALL Be Restricted Again At Application Level

The system SHALL enforce the same `nir` and `scheduler` intranet policy in the Django application even when upstream publication controls are present.

#### Scenario: Valid NIR credentials are used from an unauthorized origin

- **WHEN** a user with role `nir` presents valid credentials from an origin outside the intranet policy
- **THEN** the application MUST deny access
- **AND** valid credentials alone MUST NOT bypass the intranet rule

### Requirement: Remote-Capable Roles SHALL Remain Reachable Outside The Intranet

The system SHALL allow `doctor`, `manager`, and `admin` users to access the Django application remotely through the approved publication path.

#### Scenario: Doctor user accesses from remote origin

- **WHEN** an authenticated `doctor` user accesses the Django app from a non-intranet origin
- **THEN** the system MUST allow access subject to normal authentication and authorization rules

### Requirement: Access Zone Denials SHALL Be Auditable

The system SHALL preserve audit evidence when access is denied because a role is outside its permitted network zone.

#### Scenario: NIR access is denied outside the intranet

- **WHEN** a `nir` access attempt is blocked by the zone policy
- **THEN** the system MUST record auditable evidence of the denial
- **AND** the evidence MUST include at minimum the role and resolved client origin context

### Requirement: Client Origin Resolution SHALL Use Trusted Proxy Rules

The system SHALL resolve the client origin only from explicitly trusted proxy/publication configuration.

#### Scenario: Request arrives through configured trusted proxy

- **WHEN** a request is forwarded through a configured trusted proxy
- **THEN** the system MUST use the approved forwarded client metadata to resolve origin IP

#### Scenario: Request supplies forwarding headers from untrusted source

- **WHEN** a request includes forwarding headers without coming through a trusted proxy path
- **THEN** the system MUST ignore those headers for zone authorization decisions

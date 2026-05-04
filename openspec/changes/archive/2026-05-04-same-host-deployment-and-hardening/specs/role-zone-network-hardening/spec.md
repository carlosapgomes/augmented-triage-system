# role-zone-network-hardening Specification

## ADDED Requirements

### Requirement: Intranet-Only Roles SHALL Be Restricted At Publication Layer

The system SHALL reinforce `nir` and `scheduler` intranet-only access at the publication/network layer in addition to application-level controls.

#### Scenario: Remote path is used for an intranet-only role

- **WHEN** an operator validates remote publication behavior for a `nir` or `scheduler` account
- **THEN** the supported topology MUST ensure that the remote publication path is not a valid operational access path for those roles

### Requirement: Publication Hardening SHALL Be Operationally Verifiable

The system SHALL provide deterministic validation steps to confirm that role/zone publication hardening is working as intended.

#### Scenario: Operator validates zone hardening after deploy

- **WHEN** deployment or topology changes are applied
- **THEN** operators MUST be able to execute deterministic checks for allowed and denied access paths by role/zone

### Requirement: Access-Publication Failures SHALL Have First-Level Troubleshooting Guidance

The system SHALL document first-level troubleshooting for publication and access-zone failures.

#### Scenario: Operator diagnoses unexpected access behavior

- **WHEN** an allowed role is denied or an intranet-only role appears reachable through the wrong path
- **THEN** the runbook MUST provide immediate diagnostic steps and escalation boundaries

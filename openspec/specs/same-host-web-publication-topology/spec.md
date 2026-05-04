# same-host-web-publication-topology Specification

## Purpose

Define the supported same-host publication topology for the consolidated ATS Django web stack.

## Requirements

### Requirement: System SHALL Define A Single-Host Publication Topology For The Consolidated Web Stack

The system SHALL define one supported same-host publication topology for the consolidated ATS runtime and Django web application.

#### Scenario: Operator reviews supported deployment topology

- **WHEN** operators prepare or review the production-like deployment model
- **THEN** the project MUST document the supported same-host topology clearly
- **AND** the topology MUST include how internal and remote access paths are differentiated

### Requirement: Remote Publication SHALL Use The Approved External Path

The system SHALL document and validate the approved remote publication path for roles allowed outside the intranet.

#### Scenario: Doctor accesses remote published surface

- **WHEN** an authenticated `doctor` user reaches the approved remote publication path
- **THEN** the system MUST allow the remote path as part of the supported topology

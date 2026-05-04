# ansible-rootless-runtime-deploy Specification

## MODIFIED Requirements

### Requirement: Deploy Automation SHALL Run Application Services As Dedicated User

The deploy automation SHALL start and manage the supported consolidated runtime services under the dedicated service user context using rootless Docker runtime.

#### Scenario: Consolidated runtime services start after deploy

- **WHEN** operators execute the deploy playbook with valid configuration for the consolidated stack
- **THEN** all supported application services MUST start under the dedicated non-root service user
- **AND** the deployment model MUST include the new Django web application in the supported runtime composition

### Requirement: Deploy Playbooks SHALL Be Idempotent

The deploy automation SHALL remain idempotent for the consolidated same-host stack.

#### Scenario: Re-run deploy with same version and variables for consolidated stack

- **WHEN** operators execute the same deploy playbook twice with identical inputs for the consolidated runtime composition
- **THEN** the second run MUST complete without destructive side effects
- **AND** resulting runtime state MUST remain equivalent to the first successful run

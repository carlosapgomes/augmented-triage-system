# ansible-rootless-runtime-deploy Specification

## Purpose

TBD - created by archiving change ansible-rootless-docker-deploy. Update Purpose after archive.

## Requirements

### Requirement: Ansible SHALL Provision Rootless Runtime Host Baseline

The deployment automation SHALL provision a compatible host baseline for runtime execution, including required system packages, dedicated service user, and rootless Docker prerequisites.

#### Scenario: Bootstrap host for first deployment

- **WHEN** operators run the bootstrap playbook against a new target host
- **THEN** the system MUST install required dependencies and configure the dedicated service user
- **AND** rootless Docker prerequisites MUST be configured successfully for that user context

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

### Requirement: Deploy Automation SHALL Support Versioned Upgrade And Rollback

The deploy automation SHALL support explicit target version deployment and deterministic rollback to a previously known stable version.

#### Scenario: Rollback after failed upgrade validation

- **WHEN** an upgrade deployment fails post-deploy validation checks
- **THEN** operators MUST be able to run the rollback playbook targeting a previous version tag
- **AND** services MUST return to the prior stable runtime version

### Requirement: Deploy Automation SHALL Scale Worker Replicas Explicitly

O deploy automation SHALL iniciar os serviços com escala explícita de workers para permitir paralelismo controlado no consumo da fila.

#### Scenario: Deploy starts runtime with worker scale

- **WHEN** operadores executam o playbook de deploy com configuração padrão
- **THEN** o comando `docker compose up` MUST incluir `--scale worker=<replicas>`
- **AND** o baseline de réplicas de worker MUST ser `3`

#### Scenario: Worker replica count remains configurable

- **WHEN** operadores ajustam variável de réplicas no inventário/role
- **THEN** o deploy MUST aplicar o novo valor sem alterar comandos suportados dos serviços
- **AND** os demais serviços (`bot-api`, `bot-matrix`) MUST continuar sob o mesmo fluxo de deploy

### Requirement: Deploy Automation SHALL Require Cutoff-Hour Runtime Configuration For Scheduler

When Room-4 scheduler cron is enabled, deploy automation SHALL require a non-empty cutoff-hour configuration key for summary scheduling.

#### Scenario: Scheduler enabled with missing cutoff-hour key

- **WHEN** deploy automation runs with scheduler cron enabled and `SUPERVISOR_SUMMARY_CUTOFF_HOURS` missing or empty
- **THEN** automation MUST fail fast with actionable validation feedback
- **AND** automation MUST NOT converge a cron configuration that cannot resolve summary windows

### Requirement: Default Scheduler Cron SHALL Align With Global Three-Cutoff Baseline

The managed scheduler cron default configuration SHALL align with the global three-cutoff baseline (`07:00`, `13:00`, `19:00`) for `America/Bahia` operations.

#### Scenario: Operators use default cron inventory values on UTC host baseline

- **WHEN** operators apply deploy automation without overriding scheduler cron defaults
- **THEN** managed cron hour defaults MUST map to `07:00`, `13:00`, `19:00` in `America/Bahia`
- **AND** the resulting default cron expression MUST execute the scheduler three times per day

### Requirement: Deploy Automation SHALL Converge Scheduler Cron State In Rootless Context

The rootless deploy automation SHALL converge the Room-4 scheduler cron configuration to desired state (`enabled` or `disabled`) in the same dedicated user context used for runtime operations.

#### Scenario: Deploy converges cron state together with runtime

- **WHEN** operators execute deploy or upgrade playbooks
- **THEN** automation MUST enforce scheduler cron desired state for the dedicated service user
- **AND** cron convergence MUST be repeatable across reruns without configuration drift

### Requirement: Deploy Automation SHALL Validate Summary Scheduler Prerequisites

When scheduler cron is enabled, the automation SHALL validate required Room-4 summary runtime configuration before finalizing deployment.

#### Scenario: Scheduler enabled with missing required summary env

- **WHEN** scheduler cron is enabled and required summary variables are missing or empty
- **THEN** automation MUST fail fast with actionable validation feedback
- **AND** it MUST prevent leaving a configured cron that cannot execute the scheduler correctly

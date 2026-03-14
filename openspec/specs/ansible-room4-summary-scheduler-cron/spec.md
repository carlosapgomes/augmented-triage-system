# ansible-room4-summary-scheduler-cron Specification

## Purpose
TBD - created by archiving change ansible-room4-scheduler-cronjob. Update Purpose after archive.
## Requirements
### Requirement: Ansible SHALL Manage Room-4 Scheduler Cronjob For Service User

The deployment automation SHALL provision and maintain one scheduler cronjob for Room-4 summaries in the crontab of the configured installation user (`ats_service_user`).

#### Scenario: Deploy applies cron for service user

- **WHEN** operators run deploy automation with scheduler cron enabled
- **THEN** the system MUST create or update exactly one managed cron entry under the service user crontab
- **AND** the cron entry MUST run without requiring root privileges

### Requirement: Cronjob SHALL Execute Scheduler Inside Application Container

The managed cronjob SHALL execute the Room-4 scheduler one-shot command inside the deployed application container image.

#### Scenario: Cron execution triggers one-shot scheduler command

- **WHEN** the scheduled cron time is reached
- **THEN** the cron command MUST invoke `uv run python -m apps.scheduler.main` inside a container launched from the runtime compose configuration
- **AND** stdout/stderr MUST be redirected to a deterministic log target

### Requirement: Cronjob SHALL Include Rootless Docker Runtime Environment

The managed cronjob SHALL define the required non-interactive environment needed to communicate with rootless Docker in user context.

#### Scenario: Cron runs in non-login shell

- **WHEN** cron executes without interactive profile initialization
- **THEN** the managed configuration MUST provide `XDG_RUNTIME_DIR` and `DOCKER_HOST` values compatible with the service user
- **AND** scheduler invocation MUST be able to reach the rootless Docker socket

### Requirement: Scheduler Cronjob SHALL Support Configurable Timezone And Schedule

The automation SHALL expose inventory-level configuration for scheduler cron timezone and schedule expression, with operational defaults aligned to Room-4 periodic summaries.

#### Scenario: Default production-like schedule is applied

- **WHEN** operators use default scheduler cron settings
- **THEN** the job MUST run at 07:00 and 19:00 in timezone `America/Bahia`
- **AND** the schedule MUST remain overridable by inventory variables without task code changes

### Requirement: Scheduler Cronjob SHALL Be Idempotent And Removable

The managed scheduler cron configuration SHALL be idempotent and support explicit disablement through configuration.

#### Scenario: Scheduler cron is disabled in inventory

- **WHEN** operators set scheduler cron as disabled and rerun deploy automation
- **THEN** the managed cron entry MUST be removed from the service user crontab
- **AND** no duplicate or stale scheduler cron entries MUST remain


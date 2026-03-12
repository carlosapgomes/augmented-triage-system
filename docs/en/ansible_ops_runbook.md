# Ansible Operations Runbook

Language: [Portugues (BR)](../ansible_ops_runbook.md) | **English**

This runbook defines the official ATS initial installation flow on a remote host using Ansible.

Supported baseline in this delivery:

- Ubuntu 24.04 LTS
- single-host
- rootless Docker with a dedicated service user
- public image on public GHCR

## Prerequisites

1. Operator workstation with Ansible installed.
1. SSH access to the remote host with a user that has `sudo`.
1. Target host running Ubuntu 24.04 LTS.
1. Repository cloned locally with the `ansible/` directory available.
1. Inventory and required variables filled before playbook execution.

## Dashboard Access Through a Domain

For real dashboard usage, the local `bot-api` endpoint (`http://127.0.0.1:8000`)
must be published through a hospital domain.

Supported options in this phase:

- reverse proxy (for example, Nginx/Caddy) forwarding to `127.0.0.1:8000`.
- Cloudflare Tunnel targeting `http://127.0.0.1:8000`.

Operational recommendation:

- use HTTPS on the public domain.
- do not expose the loopback port directly without a controlled publishing layer.

## Mobile Dashboard Installation (PWA)

Device installation prerequisites:

- dashboard published on a valid HTTPS domain;
- initial route reachable at `/dashboard/cases`;
- active authenticated web session for direct dashboard opening.

### Android (Chrome)

1. Open `https://<domain>/dashboard/cases` and authenticate when needed.
2. In Chrome, use the install prompt (when shown) or the `Install app` menu entry.
3. Confirm app name and icon on Android home screen.
4. Open the installed app and validate `standalone` mode (no browser URL bar).
5. Confirm initial launch at `/dashboard/cases`.
6. With missing/expired session, validate redirect to `/login`.

### iOS (Safari)

1. Open `https://<domain>/dashboard/cases` in Safari.
2. Use `Share` -> `Add to Home Screen`.
3. Confirm shortcut name and icon.
4. Open from home screen and validate Safari standalone context.
5. Confirm initial launch at `/dashboard/cases`.
6. With missing/expired session, validate redirect to `/login`.

### Explicit operational limitation

The installed dashboard PWA **does not support offline mode**.

When network is unavailable:

- the app must not show offline fallback with cached clinical content;
- load failures must follow normal browser network-error semantics.

## Minimum Inventory

Create `ansible/inventory/hosts.yml`:

```yaml
all:
  hosts:
    ats-prod-01:
      ansible_host: 203.0.113.10
      ansible_user: ubuntu
```

Fill mandatory variables in `ansible/host_vars/ats-prod-01.yml`:

```yaml
ats_runtime_env_required:
  DATABASE_URL: "postgresql+asyncpg://ats:<password>@127.0.0.1:5432/ats"
  ROOM1_ID: "!room1:example.org"
  ROOM2_ID: "!room2:example.org"
  ROOM3_ID: "!room3:example.org"
  MATRIX_HOMESERVER_URL: "https://matrix.example.org"
  MATRIX_BOT_USER_ID: "@ats-bot:example.org"
  MATRIX_ACCESS_TOKEN: "<token>"
  WEBHOOK_PUBLIC_URL: "https://ats.example.org/widget"
  WEBHOOK_HMAC_SECRET: "<secret>"
```

Optional bootstrap for the first admin:

```yaml
ats_runtime_env_optional:
  BOOTSTRAP_ADMIN_EMAIL: "admin@example.org"
  BOOTSTRAP_ADMIN_PASSWORD: "<strong-password>"
```

## Official Initial Installation Commands

1. Run host bootstrap (dependencies, service user, and rootless Docker):

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/bootstrap.yml
```

1. Run initial deployment with an explicit image tag:

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/deploy.yml \
  -e ats_runtime_image_tag=v1.0.0
```

1. Expected result:

- `bot-api`, `bot-matrix`, and `worker` services started.
- runtime artifacts rendered under `{{ ats_runtime_root }}` on the remote host.
- playbook completes without failures.

## Managed Room-4 Scheduler Cron

The Room-4 periodic summary cron is managed by Ansible during `deploy`,
`upgrade`, and `rollback`, always in the service-user context (`ats`).

Operational variables (override in `ansible/host_vars/<host>.yml` when needed):

```yaml
ats_room4_scheduler_cron_enabled: true
ats_room4_scheduler_cron_timezone: "UTC"
ats_room4_scheduler_cron_minute: "0"
ats_room4_scheduler_cron_hour: "10,16,22"
ats_room4_scheduler_cron_log_file: "/home/ats/augmented-triage-system/logs/room4-scheduler-cron.log"
```

Note: in the current baseline, the host clock runs in UTC; `10,16,22` in UTC
maps to `07:00, 13:00, and 19:00 in America/Bahia`.

Managed cron command:

- `docker compose ... run --rm --no-deps worker uv run python -m apps.scheduler.main`

Post-deploy checklist to validate scheduling and execution:

1. Verify managed entries in service-user crontab:

```bash
crontab -u ats -l | grep -E "ATS Room-4 Scheduler|CRON_TZ|XDG_RUNTIME_DIR|DOCKER_HOST"
```

1. Check scheduler logs:

```bash
tail -n 50 /home/ats/augmented-triage-system/logs/room4-scheduler-cron.log
```

1. Check enqueue evidence for `post_room4_summary`:

```bash
docker compose \
  --project-name augmented-triage-system \
  --file /home/ats/augmented-triage-system/docker-compose.yml \
  exec -T postgres psql -U triage -d triage \
  -c "SELECT job_id, job_type, status, created_at FROM jobs WHERE job_type = 'post_room4_summary' ORDER BY job_id DESC LIMIT 5;"
```

### Timezone-coherence checklist between app runtime and cron

1. Verify runtime app values in `.env`:

```bash
grep -E "SUPERVISOR_SUMMARY_TIMEZONE|SUPERVISOR_SUMMARY_CUTOFF_HOURS" /home/ats/augmented-triage-system/.env
```

1. Verify cron timezone and schedule values in `ats` user crontab:

```bash
crontab -u ats -l | grep -E "CRON_TZ|ATS Room-4 Scheduler"
```

1. Operational success criteria:

- `SUPERVISOR_SUMMARY_TIMEZONE` and `SUPERVISOR_SUMMARY_CUTOFF_HOURS` must represent the same cutoff schedule used by cron.
- In the current baseline this means `SUPERVISOR_SUMMARY_TIMEZONE=America/Bahia`, `SUPERVISOR_SUMMARY_CUTOFF_HOURS=7,13,19`, and UTC cron hours `10,16,22`.

## Image pull policy in deploy/upgrade

Current runtime default policy:

- `ats_runtime_pull_policy: "always"`

Operational implications:

- deploy/upgrade always attempts to pull the target-tag image from the registry;
- behavior does not depend on deleting the local target-tag image before `pull`.

Image cleanup note:

- pre-removal of the target image runs only in `missing` mode (best effort);
- under the baseline (`always`), that conditional removal remains inactive.

## Official Upgrade Flow

1. Set the new target tag (do not use `latest`):

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/upgrade.yml \
  -e ats_runtime_image_tag=v1.0.1
```

1. Expected result:

- services remain running after the update.
- playbook post-deploy validation runs `Validate all runtime services are running after upgrade`.
- playbook completes without failures.

## Official Rollback Flow

1. Set the previous stable tag to return to:

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/rollback.yml \
  -e ats_runtime_rollback_image_tag=v1.0.0
```

1. Expected result:

- services return to the stable version defined for rollback.
- playbook post-rollback validation runs `Validate all runtime services are running after rollback`.
- playbook completes without failures.

## First-Level Troubleshooting

1. Failure caused by missing mandatory variable during bootstrap:

- symptom: playbook fails with a message containing `Required runtime variable`.
- immediate action: review `ansible/host_vars/<host>.yml` and fill all keys under `ats_runtime_env_required`.
- rerun the official command:

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/bootstrap.yml
```

1. Failure caused by invalid tag (`latest`) in deploy/upgrade:

- symptom: playbook fails with `Explicit runtime image tag is required.`.
- immediate action: set an explicit versioned tag in `ats_runtime_image_tag` and rerun.

1. Failure in the post-deploy approval gate:

- symptom: error contains `Deploy approval gate failed.`.
- immediate action: validate service status on host and fix runtime configuration before retrying.
- rerun the corresponding playbook command (`deploy.yml`, `upgrade.yml`, or `rollback.yml`).

1. Room-4 cron is configured but execution fails:

- symptom: `ATS Room-4 Scheduler` entry exists in `crontab -u ats -l`, but there is no recent `post_room4_summary` enqueue evidence.
- immediate action:
  - validate cron environment variables (`CRON_TZ`, `XDG_RUNTIME_DIR`, `DOCKER_HOST`);
  - validate compose reachability in rootless context with `docker compose ... ps` under `ats` user;
  - inspect `ats_room4_scheduler_cron_log_file` for command/permission errors.
- if the issue persists after adjustment and a new `deploy/upgrade/rollback` run, escalate to development.

## Escalation Boundaries to Development

Escalate to development when:

- error persists after inventory/variable correction and full playbook rerun.
- failure indicates a potential automation bug (for example, inconsistent role behavior across idempotent runs).
- post-deploy validation failure cannot be resolved by first-level operational adjustments.

Include in the ticket when you escalate to development:

- executed command and timestamp.
- target host and used tag (`ats_runtime_image_tag` or `ats_runtime_rollback_image_tag`).
- relevant Ansible error excerpt.

## Why

The current codebase has strong service-level coverage but is not yet wired for real runtime execution, so live manual testing with Matrix rooms and Cloudflare webhook tunneling cannot be completed end-to-end. We need a focused runtime-readiness change now to validate the full deployed flow before further feature work.

## What Changes

- Enable real `bot-api` runtime serving for webhook and login endpoints in local/dev deployment.
- Wire worker runtime handlers to existing application services so queued jobs execute end-to-end.
- Introduce real Matrix runtime adapters/event loop wiring for intake, Room-3 replies, reactions, posting, media download, and cleanup redactions.
- Add runtime LLM adapter wiring suitable for manual end-to-end execution (with explicit deterministic test mode support).
- Expand runtime configuration and deployment wiring required for live testing (without changing triage business behavior).
- Add slice-level TDD guardrails and operational verification checklists for each runtime slice.
- Preserve existing triage workflow contract, state machine, webhook payload contract, and cleanup semantics (no redesign, no UI).

## Capabilities

### New Capabilities
- `runtime-orchestration`: Run `bot-api`, `bot-matrix`, and `worker` as real long-lived processes with production-style wiring of existing services.
- `worker-live-handler-wiring`: Provide a complete runtime job-handler map for existing job types so queue processing is functional in manual testing.
- `matrix-live-adapters`: Add concrete Matrix client adapters and event routing for Room-1 intake, Room-3 scheduler replies, thumbs-up reactions, message posting, MXC download, and redaction.
- `manual-e2e-readiness`: Define deterministic runtime smoke checks and manual test flow gates (including webhook tunnel readiness) without introducing new business behavior.

### Modified Capabilities
- `code-quality-ratchet`: Extend maintenance scope so all runtime-readiness changes keep public docstrings/type coverage and quality-gate compliance.

## Impact

- Affected code:
  - `apps/bot_api/main.py`
  - `apps/bot_matrix/main.py`
  - `apps/worker/main.py`
  - `src/triage_automation/infrastructure/matrix/**`
  - `src/triage_automation/infrastructure/llm/**`
  - `src/triage_automation/config/**`
  - `docker-compose.yml`, docs, and runtime verification artifacts
- API/runtime surface:
  - webhook endpoint becomes live-served in runtime
  - Matrix event handling and worker processing become runnable end-to-end
- Dependencies/systems:
  - Matrix homeserver connectivity
  - webhook ingress tunnel (Cloudflare)
  - Postgres-backed runtime services
  - LLM provider runtime integration path

## Context

The repository currently validates core triage behavior through unit/integration/e2e tests, but runtime entrypoints are not fully wired for live execution against a Matrix homeserver and external webhook ingress. `bot-api` builds a FastAPI app but does not start an ASGI server in process startup, `bot-matrix` still relies on a placeholder Matrix poster, and `worker` runs with an empty handler map. This prevents real manual end-to-end validation using live room IDs and a Cloudflare tunnel.

Constraints from the existing handoff contract remain strict:
- no changes to triage workflow semantics
- no changes to state machine behavior
- no changes to webhook payload contract beyond existing clarifications
- no UI implementation
- maintain architecture boundaries (adapters -> application -> domain)
- keep quality ratchet, public docstrings, and typed signatures in touched production code

## Goals / Non-Goals

**Goals:**
- Make all three runtime processes executable in local/dev for manual end-to-end validation.
- Wire existing services into runtime orchestration without redesigning business logic.
- Support live Matrix events for Room-1 intake, Room-3 replies, and reactions.
- Support worker execution of existing queued job types with deterministic retry/dead-letter behavior unchanged.
- Keep external dependency usage testable via deterministic fakes/modes and preserve TDD workflow.
- Provide deployment and smoke-test guidance for Cloudflare webhook tunnel testing.

**Non-Goals:**
- No new product behavior or state transitions.
- No admin UI or additional admin endpoints.
- No replacement of current persistence model or queue semantics.
- No broad refactor of service contracts unrelated to runtime readiness.
- No requirement to hard-bind to a single LLM vendor in this change.

## Decisions

1. Keep business services unchanged; implement runtime composition in app entrypoints and adapters.
- Decision: build runtime wiring around existing application services rather than moving logic.
- Rationale: preserves verified behavior and minimizes regression risk.
- Alternative considered: collapsing logic into app-level runtime modules.
- Rejected because it would violate layering and duplicate business paths.

2. Serve `bot-api` as ASGI with explicit application factory.
- Decision: keep `create_app()` and run with an ASGI server from runtime command wiring.
- Rationale: aligns with FastAPI best practice and keeps dependency injection testable.
- Alternative considered: direct in-module ad-hoc HTTP loop.
- Rejected due to weaker testability and framework bypass.

3. Build a concrete Matrix adapter implementing required ports (`send_text`, `reply_text`, `redact_event`, `download_mxc`) and event polling hooks.
- Decision: adapter layer in `infrastructure/matrix` exposes a stable interface consumed by `bot-matrix` and worker services.
- Rationale: isolates Matrix protocol/client details and allows deterministic test doubles.
- Alternative considered: calling Matrix SDK directly inside services.
- Rejected because it introduces adapter concerns into application layer.

4. Wire worker with explicit handler map for existing job types only.
- Decision: runtime startup creates handlers for `process_pdf_case`, `post_room2_widget`, `post_room3_request`, final-reply variants, and `execute_cleanup`.
- Rationale: closes the gap between tested orchestration and live execution without adding new job semantics.
- Alternative considered: generic reflection-based handler registration.
- Rejected for lower clarity and harder safety auditing.

5. Introduce configurable LLM runtime adapter with deterministic local fallback mode.
- Decision: runtime config selects either real provider adapter or deterministic fixed-response mode used by smoke tests.
- Rationale: enables progressive manual testing even when provider credentials are unavailable, while preserving service interfaces.
- Alternative considered: forcing real provider-only runtime.
- Rejected because it blocks early operational validation and CI-friendly smoke checks.

6. Keep Docker Compose and `uv` paths behaviorally aligned.
- Decision: one source of runtime commands and env assumptions, with compose wrapping the same module entrypoints.
- Rationale: reduces "works local but not in container" drift during manual testing.
- Alternative considered: separate compose-only behavior.
- Rejected due to increased operational divergence.

7. Enforce per-slice verification and docstring/type policy as mandatory completion gates.
- Decision: each implementation slice must run pytest + ruff + mypy and preserve ratchet compliance.
- Rationale: runtime wiring touches many boundaries and needs regression containment.
- Alternative considered: defer gates to final slice.
- Rejected due to compounded risk and harder diagnosis.

## Risks / Trade-offs

- [Risk] Matrix protocol edge-cases (event ordering, duplicate deliveries, redaction failures) appear in live environments.
  -> Mitigation: keep idempotency checks in repositories and add adapter integration tests with representative event fixtures.

- [Risk] Runtime startup complexity increases due to composing many dependencies.
  -> Mitigation: isolate composition functions per app and keep constructors typed/documented.

- [Risk] LLM provider/network instability introduces flaky manual runs.
  -> Mitigation: deterministic fallback mode and explicit retriable error mapping remain in services.

- [Risk] Container and host runtime commands drift over time.
  -> Mitigation: docs and compose commands reference identical startup paths; add smoke checks for both modes.

- [Risk] Cloudflare tunnel/ingress misconfiguration can be mistaken for app faults.
  -> Mitigation: add explicit webhook smoke checklist (local direct call first, then tunneled call with HMAC).

## Migration Plan

1. Implement runtime-serving support for `bot-api` and validate local endpoint behavior.
2. Implement worker handler-map composition using existing services and validate queue drain execution.
3. Implement Matrix adapter and `bot-matrix` event loop wiring for intake/reply/reaction routes.
4. Add runtime LLM adapter configuration and deterministic fallback mode for manual smoke runs.
5. Update compose/runtime docs and run end-to-end manual-test checklist (local + Cloudflare tunneled webhook).
6. Rollout strategy: ship in small vertical slices, commit each slice, and stop after each slice for verification.

Rollback strategy:
- Revert the last slice commit if regressions appear.
- Because slices are vertical and incremental, previous runtime-safe slices remain deployable.

## Open Questions

- Which Matrix client library/transport mode should be the default for long-polling in this repository?
- Should deterministic fallback mode for LLM be enabled by default in dev, or only when explicitly configured?
- Do we need a minimal authenticated health/readiness endpoint in `bot-api` for operational monitoring, or keep current scope to existing routes only?

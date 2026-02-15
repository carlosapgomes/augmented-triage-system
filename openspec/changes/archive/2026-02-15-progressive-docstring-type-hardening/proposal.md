## Why

The project now has full feature coverage for the current triage scope, but type/documentation quality remains uneven across modules. Tightening this in one pass is high risk and noisy, so we need a progressive, enforceable strategy that improves quality without blocking delivery.

## What Changes

- Introduce a progressive quality ratchet for docstrings and type annotations.
- Define explicit lint/type policy scope (public APIs first, then internal code by package).
- Add package-by-package rollout slices with required verification gates per slice.
- Require CI/local gates to prevent regression after each ratchet step.
- Keep business behavior unchanged; this is quality-hardening only.

## Capabilities

### New Capabilities
- `code-quality-ratchet`: Progressive enforcement of docstring and typing standards with incremental rollout slices and mandatory validation gates.

### Modified Capabilities
- None.

## Impact

- Affected areas: `ruff.toml`, `mypy.ini`, CI/lint/type commands, and multiple Python modules touched incrementally.
- No API contract changes for external consumers.
- No workflow/state-machine/LLM behavior changes.
- Developer workflow impact: stricter checks and incremental remediation commits.

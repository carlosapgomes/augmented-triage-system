## Context

The repository currently enforces formatting, lint, types, and tests, but docstring and typing strictness are not yet consistently required across all modules. Enabling strict rules globally in one step would generate large noisy diffs and raise merge risk. The team wants a progressive strategy that is deterministic, resumable, and safe to execute in small commits.

Constraints:
- Preserve existing architecture boundaries.
- Do not change triage business behavior.
- Keep each remediation step reviewable and independently verifiable.

## Goals / Non-Goals

**Goals:**
- Introduce enforceable docstring and typing policy with progressive ratcheting.
- Apply enforcement package-by-package with explicit completion criteria.
- Prevent regressions by adding CI/local quality gates.
- Keep workflow incremental so any slice can be resumed safely.

**Non-Goals:**
- No refactor of domain behavior or business logic.
- No changes to HTTP/API contracts unless required for typing/doc quality of public interfaces.
- No global one-shot strictness flip.

## Decisions

1. Use a ratchet model instead of global strict mode.
- Decision: tighten rules for one package group per slice.
- Rationale: minimizes disruption and keeps PRs small.
- Alternative considered: single repo-wide strict pass.
- Rejected because it creates high-risk large diffs and difficult review cycles.

2. Enforce policy via tooling config, not convention.
- Decision: codify docstring/type expectations in `ruff.toml` and `mypy.ini`, with incremental scope increases.
- Rationale: deterministic enforcement and no ambiguity for contributors.
- Alternative considered: team guideline only.
- Rejected because it is not machine-enforced and regresses over time.

3. Scope docstrings to public surfaces first.
- Decision: require docstrings on public modules/classes/functions before internal helper saturation.
- Rationale: best signal-to-noise ratio and fastest value.
- Alternative considered: require every function immediately.
- Rejected because it produces excessive churn with limited short-term value.

4. Keep quality gates mandatory per slice.
- Decision: each slice must pass target tests, `ruff check`, and `mypy` before commit.
- Rationale: prevents deferred breakage and maintains stable mainline.
- Alternative considered: defer full validation to final slice.
- Rejected because it accumulates risk.

## Risks / Trade-offs

- [Risk] Rule churn may cause frequent rebases in active areas.
  → Mitigation: process leaf packages first and keep slices short.

- [Risk] Overly strict docstring rules can generate low-value boilerplate.
  → Mitigation: enforce public-surface-first policy and tune ignores where justified.

- [Risk] Mypy strictness may expose latent typing gaps in shared utilities.
  → Mitigation: introduce strictness in per-package override blocks and add focused utility slices when needed.

- [Risk] CI duration can increase with additional checks.
  → Mitigation: keep command set stable and measure before adding new commands.

## Migration Plan

1. Establish baseline documentation/type policy and package rollout order in tasks.
2. Add initial tooling config for progressive enforcement with minimal blast radius.
3. Execute slices in order, each tightening one package/group and remediating violations.
4. Maintain ratchet rules so completed areas cannot regress.
5. After final slice, run full test/lint/type suite and archive the change.

Rollback strategy:
- Revert only the current slice commit if a package ratchet creates disruption.
- Because slices are independent, previous completed slices remain valid.

## Open Questions

- Should test modules be held to the same docstring policy level as production code or follow lighter rules?
- Should we require full parameter/return docstring detail (`D417`) now or defer until baseline adoption is complete?

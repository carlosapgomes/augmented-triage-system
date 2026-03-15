# Dashboard and Room-4 immediate-admission observability tasks

## 1. Shared observability projection foundations

- [x] 1.1 Define the shared monitoring projection that derives `status_atual`, `etapa_pendente`, `ramo_operacional`, and `desfecho_final` from persisted case state without changing runtime workflow semantics.
- [ ] 1.2 Add targeted unit/integration coverage for the shared projection, including scheduled pending cases, `vinda_imediata` pending on Room-1 acknowledgment, concluded `VINDA_IMEDIATA`, denied cases, and legacy fallback as `não aplicável`/`indisponível`.

## 2. Dashboard list, filters, and totals

- [ ] 2.1 Update dashboard monitoring queries/adapters so case list responses expose the compact operational summary and the derived observability fields needed by filters and totals.
- [ ] 2.2 Implement dashboard filters and totals that distinguish backlog state from concluded outcomes, including subtotal by pending stage and subtotal of pending cases already in the `vinda_imediata` branch.
- [ ] 2.3 Add dashboard list coverage proving that a pending immediate-admission case remains `EM_ANDAMENTO`, a concluded immediate-admission case renders `VINDA_IMEDIATA`, and legacy cases are not retroactively inferred as immediate-admission.

## 3. Dashboard detail and mobile usability

- [ ] 3.1 Add the operational summary block to the case detail view so operators can see current status, pending stage, branch, and final outcome without inferring them only from the timeline.
- [ ] 3.2 Adapt dashboard mobile rendering so the compact list summary, operational filters, totals, and detail summary remain readable and usable on small viewports.
- [ ] 3.3 Add UI/integration coverage for desktop and mobile dashboard behavior, including compact summary composition and visibility/accessibility of the detail operational summary in both thread and pure views.

## 4. Room-4 supervisory periodic summary

- [ ] 4.1 Extend Room-4 summary aggregation to report concluded outcomes as `aceitos por agendamento`, `vinda imediata`, and `recusados`, while preserving current period/window semantics.
- [ ] 4.2 Extend Room-4 summary aggregation to report current backlog totals by pending stage, including `aguardando Sala 2`, `aguardando Sala 3`, `aguardando Sala 1`, and `pendentes no ramo vinda imediata`.
- [ ] 4.3 Add targeted summary tests proving that pending `vinda_imediata` cases are counted in backlog but not as concluded `vinda imediata`, and that legacy cases only contribute to branch-specific totals when persisted evidence exists.

## 5. Verification and operational documentation

- [ ] 5.1 Update any monitoring/dashboard/Room-4 operational documentation affected by the new observability semantics, keeping Portuguese and English mirrors synchronized when docs change.
- [ ] 5.2 Run targeted verification for changed paths (`pytest`, `ruff`, `mypy`, and `markdownlint-cli2` when markdown changes) and record results in this task file during implementation.

## Verification log

### Task 1.1

- `uv run pytest tests/unit/test_monitoring_projection.py -q` ❌ failed first (red): `ModuleNotFoundError: No module named 'triage_automation.domain.monitoring_projection'`
- `uv run pytest tests/unit/test_monitoring_projection.py -q` ✅ passed (`5 passed`)
- `uv run ruff check src/triage_automation/domain/monitoring_projection.py tests/unit/test_monitoring_projection.py` ✅ passed
- `uv run mypy src/triage_automation/domain/monitoring_projection.py` ✅ passed

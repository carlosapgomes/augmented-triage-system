# Dashboard and Room-4 immediate-admission observability tasks

## 1. Shared observability projection foundations

- [x] 1.1 Define the shared monitoring projection that derives `status_atual`, `etapa_pendente`, `ramo_operacional`, and `desfecho_final` from persisted case state without changing runtime workflow semantics.
- [x] 1.2 Add targeted unit/integration coverage for the shared projection, including scheduled pending cases, `vinda_imediata` pending on Room-1 acknowledgment, concluded `VINDA_IMEDIATA`, denied cases, and legacy fallback as `não aplicável`/`indisponível`.

## 2. Dashboard list, filters, and totals

- [x] 2.1 Update dashboard monitoring queries/adapters so case list responses expose the compact operational summary and the derived observability fields needed by filters and totals.
- [x] 2.2 Implement dashboard filters and totals that distinguish backlog state from concluded outcomes, including subtotal by pending stage and subtotal of pending cases already in the `vinda_imediata` branch.
- [x] 2.3 Add dashboard list coverage proving that a pending immediate-admission case remains `EM_ANDAMENTO`, a concluded immediate-admission case renders `VINDA_IMEDIATA`, and legacy cases are not retroactively inferred as immediate-admission.

## 3. Dashboard detail and mobile usability

- [x] 3.1 Add the operational summary block to the case detail view so operators can see current status, pending stage, branch, and final outcome without inferring them only from the timeline.
- [x] 3.2 Adapt dashboard mobile rendering so the compact list summary, operational filters, totals, and detail summary remain readable and usable on small viewports.
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

### Task 1.2

- Added unit coverage for the non-blocking `vinda_imediata` branch mapping directly to `AGUARDANDO_SALA_1`
- Added integration coverage that derives the shared projection from persisted `cases` rows for scheduled pending, immediate pending, concluded immediate, denied, and legacy fallback scenarios
- `uv run pytest tests/unit/test_monitoring_projection.py tests/integration/test_monitoring_projection_persisted_state.py -q` ✅ passed (`11 passed`)
- `uv run ruff check src/triage_automation/domain/monitoring_projection.py tests/unit/test_monitoring_projection.py tests/integration/test_monitoring_projection_persisted_state.py` ✅ passed
- `uv run mypy src/triage_automation/domain/monitoring_projection.py` ✅ passed

### Task 2.1

- Extended monitoring list projections and API adapters to expose `compact_operational_summary`, `status_atual`, `etapa_pendente`, `ramo_operacional`, and `desfecho_final`
- Reused the shared domain projection in the SQLAlchemy monitoring repository instead of duplicating list-specific semantics
- Preserved the legacy `case_outcome` field for current dashboard rendering while exposing the richer observability fields needed by upcoming filters and totals
- `uv run pytest tests/integration/test_monitoring_case_list_endpoint.py tests/integration/test_case_repositories.py::test_case_monitoring_list_derives_operational_outcome_from_decision_fields -q` ✅ passed (`5 passed`)
- `uv run ruff check src/triage_automation/domain/monitoring_projection.py src/triage_automation/application/ports/case_repository_port.py src/triage_automation/application/dto/monitoring_models.py src/triage_automation/infrastructure/db/case_repository.py src/triage_automation/infrastructure/http/monitoring_router.py tests/integration/test_case_repositories.py tests/integration/test_monitoring_case_list_endpoint.py` ✅ passed
- `uv run mypy src/triage_automation/domain/monitoring_projection.py src/triage_automation/application/ports/case_repository_port.py src/triage_automation/application/dto/monitoring_models.py src/triage_automation/infrastructure/db/case_repository.py src/triage_automation/infrastructure/http/monitoring_router.py` ✅ passed

### Task 2.2

- Added operational dashboard filters for `status_atual`, `etapa_pendente`, `ramo_operacional`, and `desfecho_final`, while preserving the existing technical-status filter
- Refactored monitoring totals to distinguish backlog from concluded outcomes, including subtotals for `aguardando Sala 2`, `aguardando Sala 3`, `aguardando Sala 1`, and `pendentes no ramo vinda imediata`
- Updated dashboard rendering so totals reflect the end-of-flow semantics where cases only conclude after Room-1 acknowledgment/science
- `uv run pytest tests/unit/test_case_monitoring_service.py tests/integration/test_dashboard_pages.py tests/integration/test_case_repositories.py::test_case_monitoring_list_derives_operational_outcome_from_decision_fields -q` ✅ passed (`33 passed`)
- `uv run ruff check src/triage_automation/application/ports/case_repository_port.py src/triage_automation/application/services/case_monitoring_service.py src/triage_automation/infrastructure/db/case_repository.py src/triage_automation/infrastructure/http/dashboard_router.py tests/unit/test_case_monitoring_service.py tests/integration/test_dashboard_pages.py tests/integration/test_case_repositories.py` ✅ passed
- `uv run mypy src/triage_automation/application/ports/case_repository_port.py src/triage_automation/application/services/case_monitoring_service.py src/triage_automation/infrastructure/db/case_repository.py src/triage_automation/infrastructure/http/dashboard_router.py` ✅ passed

### Task 2.3

- Added dashboard list coverage proving that pending `vinda_imediata` rows still render `EM_ANDAMENTO`, concluded immediate-admission rows render `VINDA_IMEDIATA`, and legacy accepted rows fall back to `INDISPONIVEL` instead of retroactive inference
- Updated the dashboard list row to render the compact operational summary alongside the legacy outcome badge so the new observability semantics are visible in the list
- `uv run pytest tests/integration/test_dashboard_pages.py -q` ✅ passed (`32 passed`)
- `uv run ruff check tests/integration/test_dashboard_pages.py` ✅ passed
- `uv run mypy tests/integration/test_dashboard_pages.py` ✅ passed

### Task 3.1

- Extended monitoring detail projections so the dashboard detail view reuses the same derived `status_atual`, `etapa_pendente`, `ramo_operacional`, and `desfecho_final` semantics as the list
- Added an operational summary block above both thread and pure detail views, including a deterministic fallback of `Nao concluido` when the case is still open
- Added detail-page coverage for pending and concluded `vinda_imediata` cases, proving operators no longer need to infer stop-point semantics only from the timeline
- `uv run pytest tests/integration/test_dashboard_pages.py -q` ✅ passed (`34 passed`)
- `uv run ruff check src/triage_automation/application/ports/case_repository_port.py src/triage_automation/infrastructure/db/case_repository.py src/triage_automation/infrastructure/http/dashboard_router.py tests/integration/test_dashboard_pages.py` ✅ passed
- `uv run mypy src/triage_automation/application/ports/case_repository_port.py src/triage_automation/infrastructure/db/case_repository.py src/triage_automation/infrastructure/http/dashboard_router.py` ✅ passed

### Task 3.2

- Added mobile-specific list rendering hooks for the compact operational summary, operational filter controls, and operational totals cards so the richer semantics remain readable on small viewports
- Added mobile-specific detail rendering hooks for the operational summary grid/cards in both thread and pure modes
- `uv run pytest tests/integration/test_dashboard_pages.py -q` ✅ passed (`36 passed`)
- `uv run ruff check tests/integration/test_dashboard_pages.py` ✅ passed
- `uv run mypy tests/integration/test_dashboard_pages.py` ✅ passed

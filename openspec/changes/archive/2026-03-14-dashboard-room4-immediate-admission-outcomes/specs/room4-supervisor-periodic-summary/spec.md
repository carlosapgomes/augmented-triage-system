# room4-supervisor-periodic-summary Delta Specification

## MODIFIED Requirements

### Requirement: Summary Message SHALL Include Required Window And Metric Fields

The summary message SHALL include the reporting window and the minimum required
metrics for supervisory operations, combining concluded outcomes for the period
with the current operational backlog at the time the summary is emitted.

#### Scenario: Rendering supervisor summary payload

- **WHEN** the worker renders the Room-4 summary message
- **THEN** the message MUST include local window reference in `America/Bahia`
- **AND** it MUST include concluded-outcome totals for at least:
  - `pacientes recebidos`;
  - `relatórios processados`;
  - `casos avaliados`;
  - `aceitos por agendamento`;
  - `vinda imediata`;
  - `recusados`
- **AND** it MUST include current-backlog totals for at least:
  - `casos em andamento`;
  - `aguardando Sala 2`;
  - `aguardando Sala 3`;
  - `aguardando Sala 1`;
  - `pendentes no ramo vinda imediata`

### Requirement: Final Outcome Metrics SHALL Reflect End-Of-Flow Semantics

Summary counting SHALL use event timestamps within the requested window for
concluded outcomes and SHALL preserve end-of-flow semantics that distinguish
scheduled acceptance from immediate-admission completion.

#### Scenario: Counting accepted scheduled final outcomes

- **WHEN** final scheduling decisions in the window have
  `appointment_status = confirmed`
- **THEN** the system MUST count them as `aceitos por agendamento`

#### Scenario: Counting immediate-admission final outcomes

- **WHEN** cases in the window complete through the immediate-admission branch
  with the Room-1 final acknowledgment satisfied
- **THEN** the system MUST count them as concluded `vinda imediata`
- **AND** it MUST NOT collapse them into generic `aceitos por agendamento`

#### Scenario: Counting refused final outcomes

- **WHEN** final outcomes in the window include medical denial or scheduling
  denial
- **THEN** the system MUST count both classes as `recusados`

#### Scenario: Pending immediate-admission case is not counted as concluded immediate outcome

- **WHEN** a physician already selected `vinda_imediata` but Room-1 final
  acknowledgment has not yet occurred by the time the summary is generated
- **THEN** the system MUST NOT count that case as concluded `vinda imediata`
- **AND** it MUST count the case in the current backlog according to its
  pending stage
- **AND** it MUST count the case in `pendentes no ramo vinda imediata`

## ADDED Requirements

### Requirement: Current Backlog Metrics SHALL Reflect Operational Stop Point

The Room-4 periodic summary SHALL expose current backlog using a simplified
operational stop-point taxonomy so supervisors can see where open cases are
currently blocked without reading individual timelines.

#### Scenario: Backlog totals are grouped by current stop point

- **WHEN** the Room-4 summary is generated while cases are still open in the
  workflow
- **THEN** each open case MUST contribute to exactly one current pending-stage
  subtotal that reflects where the flow is presently stopped
- **AND** the summary MUST keep `aguardando Sala 2`, `aguardando Sala 3`, and
  `aguardando Sala 1` mutually understandable as supervisor-facing backlog
  categories

#### Scenario: Legacy case lacks immediate-admission branch evidence

- **WHEN** an open historical case predates persisted immediate-admission
  observability fields
- **THEN** the system MUST keep the case eligible for current backlog counting
  by pending stage when applicable
- **AND** it MUST NOT count the case in `pendentes no ramo vinda imediata`
  unless persisted evidence explicitly supports that branch

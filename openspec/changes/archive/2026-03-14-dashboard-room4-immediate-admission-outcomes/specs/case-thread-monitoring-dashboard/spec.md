# case-thread-monitoring-dashboard Delta Specification

## MODIFIED Requirements

### Requirement: Dashboard SHALL List Cases For Operational Monitoring

The system SHALL provide a dashboard case list view for authenticated
operational users, including at minimum case identifier, a compact operational
summary, current status, pending stage when the case is still in progress,
final outcome when the case is concluded, latest update timestamp, and
pagination/filter controls for daily monitoring.

#### Scenario: Reader lists cases processed in a period

- **WHEN** an authenticated `reader` requests the case list filtered by date
  range
- **THEN** the system MUST return paginated case entries ordered by most recent
  activity
- **AND** each entry MUST include case id, compact operational summary, and
  latest activity timestamp

#### Scenario: Admin lists cases processed in a period

- **WHEN** an authenticated `admin` requests the case list filtered by date
  range
- **THEN** the system MUST return the same paginated monitoring list behavior
  available to `reader`
- **AND** each entry MUST include case id, compact operational summary, and
  latest activity timestamp

#### Scenario: Case row reflects pending immediate-admission branch without concluding the case

- **WHEN** the dashboard renders a case whose physician already selected
  `vinda_imediata` but whose Room-1 final acknowledgment has not yet occurred
- **THEN** the system MUST display the case as `EM_ANDAMENTO`
- **AND** it MUST expose a pending-stage summary equivalent to awaiting Room-1
  acknowledgment/science
- **AND** it MUST expose the immediate-admission branch as operational context
- **AND** it MUST NOT display final outcome `VINDA_IMEDIATA` for that case yet

#### Scenario: Case row reflects concluded immediate-admission outcome

- **WHEN** the dashboard renders a case that concluded through the immediate-
  admission branch after Room-1 final acknowledgment
- **THEN** the system MUST display final outcome `VINDA_IMEDIATA`
- **AND** it MUST NOT collapse that concluded outcome into generic `ACEITO`

#### Scenario: Legacy case lacks immediate-admission branch evidence

- **WHEN** the dashboard renders a historical case that predates persisted
  immediate-admission observability data
- **THEN** the system MUST preserve deterministic status/outcome rendering from
  available persisted evidence
- **AND** any unavailable branch semantics MUST render as `não aplicável` or
  `indisponível`, not as an inferred immediate-admission classification

## ADDED Requirements

### Requirement: Dashboard SHALL Support Operational Filters And Totals

The system SHALL provide dashboard filters and totals that distinguish backlog
state from final outcomes, allowing operators to monitor where cases are
currently blocked as well as how they eventually concluded.

#### Scenario: Operator filters by pending stage and immediate-admission branch

- **WHEN** an authenticated operational user filters the dashboard for cases in
  progress that belong to the `vinda_imediata` branch
- **THEN** the system MUST return only cases that are still open and already
  associated with the immediate-admission branch
- **AND** the filtered result MUST preserve the visible pending-stage summary
  for each returned case

#### Scenario: Dashboard totals separate backlog from concluded outcomes

- **WHEN** the dashboard renders totals for the current filtered result set
- **THEN** the totals MUST distinguish at minimum:
  - cases still `EM_ANDAMENTO`;
  - subtotal by pending stage;
  - subtotal of pending cases already in the `vinda_imediata` branch;
  - concluded `ACEITO` cases;
  - concluded `VINDA_IMEDIATA` cases;
  - concluded `NEGADO` cases

### Requirement: Dashboard SHALL Show Operational Summary In Case Detail

The system SHALL provide an operational summary block in the per-case detail
view that makes the current stop point understandable without requiring the
operator to infer workflow state only from the chronological timeline.

#### Scenario: Operator opens detail for in-progress immediate-admission case

- **WHEN** an authenticated operational user opens the detail view for a case
  whose physician selected `vinda_imediata` and that still awaits Room-1 final
  acknowledgment
- **THEN** the detail view MUST show that the case remains `EM_ANDAMENTO`
- **AND** it MUST show the current pending stage equivalent to awaiting Room-1
  acknowledgment/science
- **AND** it MUST show the selected branch as `vinda_imediata`
- **AND** it MUST keep the chronological timeline available below the summary

#### Scenario: Operator opens detail for concluded immediate-admission case

- **WHEN** an authenticated operational user opens the detail view for a case
  that already concluded through the immediate-admission branch
- **THEN** the detail view MUST show final outcome `VINDA_IMEDIATA`
- **AND** it MUST no longer present the case as operationally pending
- **AND** it MUST keep the chronological timeline available for auditability

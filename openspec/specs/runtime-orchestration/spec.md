# runtime-orchestration Specification

## Purpose

Define runtime process startup requirements and parity constraints for local and compose execution.

## Requirements

### Requirement: Bot API Runtime Serving

The system SHALL run the supported runtime processes required for HTTP/web workflow needs while medical workflow progression remains orchestrated by the backend services.

#### Scenario: Runtime processes start in web-workflow mode

- **WHEN** the supported runtime entrypoints are launched with valid settings
- **THEN** the system MUST remain running and serve the web workflow surfaces required by the current product scope
- **AND** workflow progression MUST remain orchestrated by backend services rather than by manual message handling

### Requirement: Compose and UV Runtime Parity

The system SHALL provide behaviorally equivalent runtime startup paths for local `uv` execution and Docker Compose execution, and production runtime commands SHALL remain compatible with Ansible-managed deployment automation.

#### Scenario: Runtime command parity

- **WHEN** operators launch services via `uv` entrypoints or via Compose commands
- **THEN** both paths MUST execute the same application startup composition and dependency wiring

#### Scenario: Production deploy automation executes runtime commands

- **WHEN** operators run official Ansible deployment playbooks for production
- **THEN** deployed runtime commands MUST be compatible with the same supported startup composition
- **AND** production automation MUST NOT depend on an ad-hoc runtime path outside declared supported commands

### Requirement: No Workflow Redesign During Runtime Wiring

Runtime orchestration changes SHALL NOT alter authoritative triage workflow behavior.

#### Scenario: Runtime orchestration code is introduced

- **WHEN** runtime-serving and startup wiring are implemented
- **THEN** state-machine semantics, decision contract, and cleanup trigger behavior MUST remain unchanged

#### Scenario: Human workflow surfaces migrate from messages to web

- **WHEN** the system replaces human message interactions with web interactions
- **THEN** the backend MUST preserve the existing state-machine semantics and branch behavior
- **AND** only the human interaction surface MUST change

### Requirement: Matrix Structured Reply SHALL Be The Single Standard Room-2 Decision Path

Runtime behavior SHALL treat structured Matrix replies in Room-2 as the canonical doctor decision path for normal operations.

#### Scenario: Case awaiting doctor decision in Room-2

- **WHEN** a case is in `WAIT_DOCTOR`
- **THEN** decision processing MUST be driven by structured Matrix replies to Room-2 case context messages
- **AND** no optional parallel standard decision path MUST be required

### Requirement: Runtime SHALL Support Manual Review Terminal Path For Out-Of-Scope Requests

Runtime orchestration SHALL terminate automated recommendation for out-of-scope exam requests and SHALL route those cases to manual review.

#### Scenario: Exam scope gate returns non-EDA or unknown

- **WHEN** runtime receives a deterministic scope outcome of non-EDA or unknown
- **THEN** runtime MUST NOT continue automatic recommendation flow
- **AND** runtime MUST mark the case as `manual_review_required`
- **AND** runtime MUST avoid enqueueing downstream EDA recommendation jobs for that cycle

### Requirement: Runtime SHALL Close Scope-Gated Cases Through Room-1 Notification

Runtime orchestration SHALL emit Room-1 closure-facing communication for manual-review outcomes produced by EDA scope gating.

#### Scenario: Scope-gated manual review is produced

- **WHEN** runtime marks a case as `manual_review_required` due to non-EDA or unknown exam scope
- **THEN** runtime MUST post a Room-1 message indicating that the report is not an EDA request or exam type could not be detected
- **AND** the same message MUST state that manual review is required

### Requirement: Runtime SHALL Persist Deterministic Scope-Gating Audit Data

Runtime orchestration SHALL persist auditable deterministic reason metadata for scope-gated manual-review outcomes.

#### Scenario: Scope-gating decision is persisted

- **WHEN** a case is routed to `manual_review_required` by scope gating
- **THEN** runtime MUST append an audit event containing `reason_code` and `reason_text`
- **AND** runtime MUST include source evidence excerpts when available

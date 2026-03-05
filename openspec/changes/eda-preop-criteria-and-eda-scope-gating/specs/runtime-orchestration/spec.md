# Specification Delta

## ADDED Requirements

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

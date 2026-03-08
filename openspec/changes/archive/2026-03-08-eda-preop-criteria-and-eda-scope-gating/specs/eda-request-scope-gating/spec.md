# Specification Delta

## ADDED Requirements

### Requirement: EDA Scope Classification SHALL Gate Automatic Recommendation

The system SHALL classify request scope before recommendation and SHALL only allow automatic clinical recommendation when the exam type is confirmed as EDA.

#### Scenario: Request is non-EDA

- **WHEN** the extracted exam type is not EDA (for example gastrostomy, esophageal dilation, colonoscopy, or ERCP)
- **THEN** the system MUST NOT emit `accept` or `deny`
- **AND** the system MUST set outcome to `manual_review_required`

#### Scenario: Request exam type is unknown

- **WHEN** the extracted exam type cannot be confirmed from source documents
- **THEN** the system MUST NOT emit `accept` or `deny`
- **AND** the system MUST set outcome to `manual_review_required`

#### Scenario: Request is confirmed as EDA

- **WHEN** the extracted exam type is confirmed as EDA
- **THEN** the system MUST continue to deterministic EDA pre-procedure evaluation

### Requirement: Scope-Gated Manual Review SHALL Notify Room-1 And Audit Cause

When scope gating routes a case to manual review, the system SHALL publish a closure-facing Room-1 message and SHALL persist deterministic audit metadata for the reason.

#### Scenario: Non-EDA or unknown request is routed to manual review

- **WHEN** scope gating returns `manual_review_required`
- **THEN** the system MUST post a Room-1 message stating that the report is not an EDA request or exam type could not be detected and manual review is required
- **AND** the system MUST append an audit event with deterministic `reason_code`
- **AND** the system MUST include source evidence excerpts when available

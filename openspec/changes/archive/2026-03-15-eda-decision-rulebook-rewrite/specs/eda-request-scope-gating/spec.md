# eda-request-scope-gating Delta Specification

## MODIFIED Requirements

### Requirement: EDA Scope Classification SHALL Gate Automatic Recommendation

The system SHALL classify request scope before recommendation and SHALL only block automatic clinical recommendation when the exam is truly non-EDA or remains unresolved after supported-EDA subtype detection.

#### Scenario: Unknown exam type with explicit standard EDA evidence becomes supported EDA

- **WHEN** `preop_screening.exam_type` is `unknown`
- **AND** the report text contains explicit EDA request evidence
- **AND** no true non-EDA exclusion is present
- **THEN** the system MUST treat scope as confirmed supported EDA
- **AND** the system MUST continue to EDA recommendation evaluation

#### Scenario: Gastrostomy request is treated as supported EDA subtype

- **WHEN** the report text indicates gastrostomy as the requested procedure within the EDA workflow
- **THEN** the system MUST classify the request as supported EDA subtype `gastrostomy`
- **AND** the system MUST continue to EDA recommendation evaluation instead of routing to manual review

#### Scenario: Esophageal dilation request is treated as supported EDA subtype

- **WHEN** the report text indicates esophageal dilation as the requested procedure within the EDA workflow
- **THEN** the system MUST classify the request as supported EDA subtype `esophageal_dilation`
- **AND** the system MUST continue to EDA recommendation evaluation instead of routing to manual review

#### Scenario: Foreign-body removal request is treated as supported EDA subtype

- **WHEN** the report text indicates EDA for foreign-body removal
- **THEN** the system MUST classify the request as supported EDA subtype `foreign_body`
- **AND** the system MUST continue to EDA recommendation evaluation instead of routing to manual review

#### Scenario: Unknown request without explicit supported EDA evidence remains manual review

- **WHEN** `preop_screening.exam_type` is `unknown`
- **AND** the report text does not contain explicit supported EDA request evidence
- **THEN** the system MUST NOT emit `accept` or `deny`
- **AND** the system MUST set outcome to `manual_review_required`

### Requirement: Scope-Gated Manual Review SHALL Notify Room-1 And Audit Cause

When scope gating routes a case to manual review, the system SHALL publish a closure-facing Room-1 message and SHALL persist deterministic audit metadata only for requests that remain outside the supported EDA flow.

#### Scenario: True non-EDA request is routed to manual review

- **WHEN** scope gating resolves to `manual_review_required` because the report is a true non-EDA request
- **THEN** the system MUST post a Room-1 message stating that the report is not an EDA request and manual review is required
- **AND** the system MUST append an audit event with deterministic `reason_code`
- **AND** the system MUST include source evidence excerpts when available

#### Scenario: Unresolved unknown request is routed to manual review

- **WHEN** scope gating resolves to `manual_review_required` because the exam type cannot be confirmed as supported EDA
- **THEN** the system MUST post a Room-1 message stating that exam type could not be detected and manual review is required
- **AND** the system MUST append an audit event with deterministic `reason_code`
- **AND** the system MUST include source evidence excerpts when available

#### Scenario: Supported EDA subtype must not be closed as manual review

- **WHEN** scope detection resolves the report to supported EDA subtype `gastrostomy`, `esophageal_dilation`, or `foreign_body`
- **THEN** the system MUST NOT emit `manual_review_required` for scope reasons
- **AND** the system MUST continue to recommendation and physician-review flow

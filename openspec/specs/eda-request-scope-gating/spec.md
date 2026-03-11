# eda-request-scope-gating Specification

## Purpose

TBD - created by archiving change eda-preop-criteria-and-eda-scope-gating. Update Purpose after archive.

## Requirements

### Requirement: EDA Scope Classification SHALL Gate Automatic Recommendation

The system SHALL classify request scope before recommendation and SHALL only allow automatic clinical recommendation when the exam type is confirmed as EDA.

#### Scenario: Request exam type is unknown but report contains explicit EDA request

- **WHEN** `preop_screening.exam_type` is `unknown`
- **AND** the report text contains explicit EDA request evidence (for example, "Motivo da Solicitação: Endoscopia Digestiva Alta - EDA")
- **AND** no deterministic non-EDA exclusion keyword is present
- **THEN** the system MUST treat scope as confirmed EDA
- **AND** the system MUST continue to deterministic EDA pre-procedure evaluation

#### Scenario: Request exam type is unknown without explicit EDA request evidence

- **WHEN** `preop_screening.exam_type` is `unknown`
- **AND** the report text does not contain explicit EDA request evidence
- **THEN** the system MUST NOT emit `accept` or `deny`
- **AND** the system MUST set outcome to `manual_review_required`

### Requirement: Scope-Gated Manual Review SHALL Notify Room-1 And Audit Cause

When scope gating routes a case to manual review, the system SHALL publish a closure-facing Room-1 message and SHALL persist deterministic audit metadata for the reason.

#### Scenario: Non-EDA or unknown request is routed to manual review

- **WHEN** scope gating returns `manual_review_required`
- **THEN** the system MUST post a Room-1 message stating that the report is not an EDA request or exam type could not be detected and manual review is required
- **AND** the system MUST append an audit event with deterministic `reason_code`
- **AND** the system MUST include source evidence excerpts when available

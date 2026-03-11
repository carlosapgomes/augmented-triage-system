# eda-request-scope-gating Delta Specification

## MODIFIED Requirements

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

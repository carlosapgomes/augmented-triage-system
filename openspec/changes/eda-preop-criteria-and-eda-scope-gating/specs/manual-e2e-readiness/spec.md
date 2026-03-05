# Specification Delta

## ADDED Requirements

### Requirement: Manual E2E SHALL Validate EDA Scope-Gating Manual Review Path

Manual runbooks SHALL validate that non-EDA and unknown exam requests do not receive automatic recommendation and are closed through Room-1 manual-review messaging.

#### Scenario: Non-EDA request is processed

- **WHEN** operator executes manual E2E with a report classified as non-EDA
- **THEN** outcome MUST be `manual_review_required`
- **AND** no automatic `accept` or `deny` recommendation MUST be produced
- **AND** Room-1 MUST receive manual-review closure message

#### Scenario: Unknown exam type request is processed

- **WHEN** operator executes manual E2E with a report whose exam type cannot be detected
- **THEN** outcome MUST be `manual_review_required`
- **AND** no automatic `accept` or `deny` recommendation MUST be produced
- **AND** Room-1 MUST receive manual-review closure message

### Requirement: Manual E2E SHALL Validate Deterministic Denial By Missing Prerequisite Exams

Manual runbooks SHALL validate deterministic negative recommendations when risk is reported and prerequisite exam evidence is absent.

#### Scenario: Cardiovascular disease reported without ECG

- **WHEN** operator executes manual E2E for EDA case with cardiovascular disease evidence and missing ECG report
- **THEN** recommendation MUST be `deny`
- **AND** output MUST include reason code `missing_ecg_with_cardiovascular_disease`
- **AND** output MUST include explicit explanatory text and evidence excerpts

#### Scenario: Respiratory risk reported without chest X-ray

- **WHEN** operator executes manual E2E for EDA case with active or prior respiratory risk and missing chest X-ray report
- **THEN** recommendation MUST be `deny`
- **AND** output MUST include reason code `missing_chest_xray_with_respiratory_risk`
- **AND** output MUST include explicit explanatory text and evidence excerpts

# manual-e2e-readiness Delta Specification

## MODIFIED Requirements

### Requirement: Manual E2E SHALL Validate EDA Scope-Gating Manual Review Path

Manual runbooks SHALL validate that true non-EDA and unresolved unknown exam requests do not receive automatic recommendation, while supported EDA subtypes continue through physician review.

#### Scenario: Non-EDA request is processed

- **WHEN** operator executes manual E2E with a report classified as true non-EDA
- **THEN** outcome MUST be `manual_review_required`
- **AND** no automatic `accept` or `deny` recommendation MUST be produced
- **AND** Room-1 MUST receive manual-review closure message

#### Scenario: Unknown unsupported exam type request is processed

- **WHEN** operator executes manual E2E with a report whose exam type cannot be confirmed as supported EDA
- **THEN** outcome MUST be `manual_review_required`
- **AND** no automatic `accept` or `deny` recommendation MUST be produced
- **AND** Room-1 MUST receive manual-review closure message

#### Scenario: Gastrostomy request remains inside supported EDA flow

- **WHEN** operator executes manual E2E with a report classified as `EDA para gastrostomia`
- **THEN** the case MUST continue to automatic recommendation and Room-2 physician review
- **AND** it MUST NOT be closed as out-of-scope manual review

#### Scenario: Esophageal dilation request remains inside supported EDA flow

- **WHEN** operator executes manual E2E with a report classified as `EDA para dilatação esofágica`
- **THEN** the case MUST continue to automatic recommendation and Room-2 physician review
- **AND** it MUST NOT be closed as out-of-scope manual review

### Requirement: Manual E2E SHALL Validate Deterministic Denial By Missing Prerequisite Exams

Manual runbooks SHALL validate deterministic negative recommendations when mandatory minimum exams, applicable conditional exams, or contraindication thresholds fail under the rewritten EDA rulebook.

#### Scenario: Mandatory minimum exam is absent

- **WHEN** operator executes manual E2E for supported EDA request missing one of the mandatory minimum exams
- **THEN** recommendation MUST be `deny`
- **AND** output MUST identify the missing minimum exam explicitly

#### Scenario: Cardiovascular trigger exists without ECG report

- **WHEN** operator executes manual E2E for supported EDA request with ECG-triggering criteria and no ECG report finding in the source text
- **THEN** recommendation MUST be `deny`
- **AND** output MUST include explicit explanatory text that ECG evidence is missing

#### Scenario: Respiratory trigger exists without chest X-ray report

- **WHEN** operator executes manual E2E for supported EDA request with respiratory trigger and no chest X-ray report finding in the source text
- **THEN** recommendation MUST be `deny`
- **AND** output MUST include explicit explanatory text that chest X-ray evidence is missing

#### Scenario: Echo trigger exists without echocardiogram report

- **WHEN** operator executes manual E2E for supported EDA request with echo-triggering criteria and no echocardiogram report finding in the source text
- **THEN** recommendation MUST be `deny`
- **AND** output MUST include explicit explanatory text that echocardiogram evidence is missing

#### Scenario: Contraindication threshold is exceeded

- **WHEN** operator executes manual E2E for supported EDA request where hepatopathy, cardiopathy, combined, or general thresholds are exceeded
- **THEN** recommendation MUST be `deny`
- **AND** output MUST include explicit explanatory text naming the failed threshold

## ADDED Requirements

### Requirement: Manual E2E SHALL Validate Supported EDA Special Subtypes And Room-2 Clinical Context

Manual runbooks SHALL validate the new supported EDA subtypes and the rewritten Room-2 summary context under the new rulebook.

#### Scenario: Foreign-body removal bypasses minimum exams but still reaches Room-2

- **WHEN** operator executes manual E2E with a report classified as `EDA para retirada de corpo estranho`
- **THEN** the case MUST continue to automatic recommendation and Room-2 physician review without requiring the mandatory minimum exam set
- **AND** the recommendation MUST still include support context when clinically applicable

#### Scenario: Room-2 summary renders ASA and pediatric context explicitly

- **WHEN** operator reviews a supported EDA case in Room-2 after recommendation is produced
- **THEN** message II MUST show the `ASA estimado` block explicitly
- **AND** when the case is pediatric it MUST show `paciente pediátrico: sim` near the case context
- **AND** the requested procedure text MUST reflect the supported subtype when applicable

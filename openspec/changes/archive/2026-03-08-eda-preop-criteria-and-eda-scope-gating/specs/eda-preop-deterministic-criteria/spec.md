# Specification Delta

## ADDED Requirements

### Requirement: EDA Deterministic Policy SHALL Preserve CHD Local Criteria With Scenario Priority

The system SHALL evaluate confirmed EDA requests using deterministic CHD-local criteria and SHALL apply scenario-specific thresholds before baseline fallback.

#### Scenario: EDA for bleeding, abdominal pain, or dyspepsia

- **WHEN** indication is bleeding, abdominal pain, or dyspepsia
- **THEN** the system MUST deny when `hb <= 7`
- **AND** the system MUST deny when `platelets <= 100000`
- **AND** the system MUST deny when `inr >= 1.5`
- **AND** the system MUST deny when ECG report is absent

#### Scenario: EDA outside bleeding, abdominal pain, or dyspepsia

- **WHEN** indication is EDA and not in bleeding, abdominal pain, or dyspepsia
- **THEN** the system MUST apply baseline CHD contraindication thresholds
- **AND** baseline thresholds MUST include deny for `hb < 7`, `platelets < 50000`, or `inr > 2`

### Requirement: EDA Deterministic Policy SHALL Enforce Cardiorespiratory Completeness Gates

The system SHALL deny EDA recommendation when risk is explicitly reported and required associated exam evidence is missing.

#### Scenario: Cardiovascular disease reported without ECG

- **WHEN** source evidence reports cardiovascular disease
- **AND** no ECG report is available
- **THEN** the system MUST deny with reason code `missing_ecg_with_cardiovascular_disease`

#### Scenario: Respiratory risk reported without chest X-ray

- **WHEN** source evidence reports active respiratory symptoms or prior respiratory disease
- **AND** no chest X-ray report is available
- **THEN** the system MUST deny with reason code `missing_chest_xray_with_respiratory_risk`

### Requirement: EDA Deterministic Policy SHALL Handle Exclusions And Foreign Body Exception

The system SHALL apply deterministic exclusion and exception routing for EDA-adjacent requests.

#### Scenario: Request is gastrostomy or esophageal dilation

- **WHEN** extracted indication corresponds to gastrostomy or esophageal dilation
- **THEN** the system MUST set outcome to `excluded`
- **AND** the system MUST set reason code to `excluded_gastrostomy` or `excluded_esophageal_dilation` respectively

#### Scenario: Request is foreign-body removal

- **WHEN** extracted indication corresponds to foreign-body removal
- **THEN** the system MUST NOT require routine laboratory gate completion before recommendation

### Requirement: Deterministic Decision Output SHALL Be Explicit And Auditable

The system SHALL emit deterministic explanation fields for all pre-procedure decisions.

#### Scenario: Deterministic policy returns any terminal outcome

- **WHEN** deterministic policy resolves to `accept`, `deny`, `excluded`, or `manual_review_required`
- **THEN** output MUST include `decision`, `reason_code`, and `reason_text`
- **AND** output MUST include `evidence_spans` with source excerpts when available

### Requirement: Pediatric Requests SHALL Be Explicitly Flagged

The system SHALL flag pediatric cases for explicit visibility in clinical review output.

#### Scenario: Patient age is below pediatric threshold

- **WHEN** extracted patient age is lower than 16 years
- **THEN** the system MUST set `pediatric_flag` to true
- **AND** the decision output MUST include explicit pediatric signaling in explanatory text

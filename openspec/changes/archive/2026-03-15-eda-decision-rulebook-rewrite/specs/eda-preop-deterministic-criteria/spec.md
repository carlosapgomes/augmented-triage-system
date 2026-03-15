# eda-preop-deterministic-criteria Delta Specification

## MODIFIED Requirements

### Requirement: EDA Deterministic Policy SHALL Preserve CHD Local Criteria With Scenario Priority

The system SHALL evaluate supported EDA requests using the rewritten CHD-local rulebook, replacing the legacy split between EDA “operational” and “não operacional” with one unified clinical policy based on supported subtype, mandatory minimum exams, conditional completeness gates, and contraindication thresholds.

#### Scenario: Standard EDA, gastrostomy, and esophageal dilation require the same minimum exam set

- **WHEN** a request is classified as supported EDA with subtype `standard`, `gastrostomy`, or `esophageal_dilation`
- **THEN** the system MUST require evidence of `Hb/Ht`, platelets, `TP|INR|RNI`, `TTPa`, ureia, and creatinina before recommending acceptance
- **AND** `Hb` alone MUST be sufficient to satisfy the `Hb/Ht` requirement for rule evaluation
- **AND** missing any applicable minimum exam MUST drive recommendation to `deny` with explicit cause text for physician review

#### Scenario: Numeric-threshold exams require numeric evidence

- **WHEN** the system evaluates `Hb`, platelets, or `TP|INR|RNI` against contraindication thresholds
- **THEN** it MUST require numeric evidence for those items
- **AND** generic text such as `hemograma normal`, `coagulograma sem alterações`, or `exames laboratoriais sem alterações` MUST NOT satisfy the numeric minimum-exam requirement

#### Scenario: Qualitative evidence can satisfy TTPa and renal-function minimums

- **WHEN** the report contains qualitative evidence such as `TTPa normal`, `função renal preservada`, or `ureia/creatinina sem alterações`
- **THEN** the system MUST treat `TTPa`, ureia, and creatinina as present for minimum-exam completeness
- **AND** `função renal preservada` MUST satisfy both ureia and creatinina together
- **AND** `coagulograma normal` MUST satisfy `TTPa` only when `TP|INR|RNI` is already documented with numeric evidence

#### Scenario: Foreign-body removal bypasses minimum exams and conditional completeness gates

- **WHEN** a request is classified as supported EDA with subtype `foreign_body`
- **THEN** the system MUST bypass mandatory minimum laboratory checks
- **AND** the system MUST bypass conditional RX/ECG/ECO completeness gates before recommendation
- **AND** the system MAY still emit support recommendation based on the remaining clinical context and ASA estimate

#### Scenario: Hepatopathy contraindication thresholds apply when hepatopathy is explicitly documented

- **WHEN** the report contains explicit clinical evidence of hepatopathy
- **THEN** the system MUST recommend `deny` when `Hb < 7`, `platelets < 50000`, or `RNI > 1.5`

#### Scenario: Cardiopathy contraindication thresholds apply when cardiopathy is explicitly documented

- **WHEN** the report contains explicit clinical evidence of cardiopathy
- **THEN** the system MUST recommend `deny` when `Hb < 8`, `platelets < 100000`, or `RNI > 1.5`

#### Scenario: Combined hepatopathy and cardiopathy use the clinically stricter mixed thresholds

- **WHEN** the report contains explicit clinical evidence of both hepatopathy and cardiopathy
- **THEN** the system MUST recommend `deny` when `Hb < 8`, `platelets < 50000`, or `RNI > 1.5`

#### Scenario: Non-hepatopathic and non-cardiopathic patients use general thresholds

- **WHEN** a supported EDA request lacks explicit evidence of hepatopathy and cardiopathy
- **THEN** the system MUST recommend `deny` when `Hb < 7`, `platelets < 100000`, or `RNI > 1.5`

### Requirement: EDA Deterministic Policy SHALL Enforce Cardiorespiratory Completeness Gates

The system SHALL recommend denial for supported EDA requests when explicit clinical criteria indicate that ECG, chest X-ray, or echocardiogram evidence is required and no minimal reportable finding for that exam is present in the report.

#### Scenario: Cardiovascular criteria require ECG report evidence

- **WHEN** a supported EDA request has any ECG-triggering criterion documented, including age above 40 years, known cardiovascular disease, recent chest pain, dyspnea, palpitations, syncope, multiple comorbidities, QT-prolonging medication use, diabetes mellitus, or explicit obesity
- **THEN** the system MUST require ECG report evidence with at least a minimal reportable finding in the source text
- **AND** if such ECG evidence is absent the system MUST recommend `deny`

#### Scenario: Respiratory criteria require chest X-ray report evidence

- **WHEN** a supported EDA request documents respiratory symptoms or prior respiratory disease
- **THEN** the system MUST require chest X-ray report evidence with at least a minimal reported finding in the source text
- **AND** if such chest X-ray evidence is absent the system MUST recommend `deny`

#### Scenario: Cardiac-structural criteria require echocardiogram report evidence

- **WHEN** a supported EDA request documents unexplained dyspnea, signs of heart failure, new or unevaluated murmur, moderate/severe valvulopathy without recent echo, worsening cardiomyopathy, pulmonary hypertension, prior myocardial infarction, coronary bypass surgery, or coronary angioplasty
- **THEN** the system MUST require echocardiogram report evidence with at least a minimal reported finding in the source text
- **AND** if such echocardiogram evidence is absent the system MUST recommend `deny`

#### Scenario: Mentioning exam existence without findings does not satisfy completeness

- **WHEN** the report only states that ECG, chest X-ray, or echocardiogram exists or was requested
- **THEN** the system MUST treat that exam as incomplete for recommendation purposes
- **AND** the system MUST require a minimal reported finding such as `ECG sem alterações` or `raio-x de tórax normal`

#### Scenario: Isolated suspicion does not create a hard positive trigger

- **WHEN** the source text contains only isolated suspicion of hepatopathy, cardiopathy, or cardiovascular disease without explicit supporting evidence
- **THEN** the system MUST treat that condition as evidence-insufficient rather than confirmed
- **AND** the system MUST NOT enforce a completeness gate solely from that isolated suspicion

### Requirement: EDA Deterministic Policy SHALL Handle Exclusions And Foreign Body Exception

The system SHALL route EDA-adjacent requests according to the new supported-scope model, where gastrostomy, esophageal dilation, and foreign-body removal remain inside the automatic EDA recommendation flow, while true non-EDA or unresolved requests continue outside it.

#### Scenario: Gastrostomy request remains in supported EDA flow

- **WHEN** the request corresponds to gastrostomy
- **THEN** the system MUST classify it as supported EDA subtype `gastrostomy`
- **AND** the system MUST continue to recommendation and physician review instead of excluding it before Room-2

#### Scenario: Esophageal dilation request remains in supported EDA flow

- **WHEN** the request corresponds to esophageal dilation
- **THEN** the system MUST classify it as supported EDA subtype `esophageal_dilation`
- **AND** the system MUST continue to recommendation and physician review instead of excluding it before Room-2

#### Scenario: Foreign-body request remains in supported EDA flow with exception behavior

- **WHEN** the request corresponds to foreign-body removal
- **THEN** the system MUST classify it as supported EDA subtype `foreign_body`
- **AND** the system MUST continue to physician review under the bypass rules for minimum exams and conditional completeness gates

### Requirement: Deterministic Decision Output SHALL Be Explicit And Auditable

The system SHALL emit recommendation data that remains explicit and auditable after the rulebook rewrite, including structured explanation and the clinical signals required to render downstream Room-2 messaging.

#### Scenario: Supported EDA recommendation is produced

- **WHEN** recommendation for a supported EDA request resolves to `accept` or `deny`
- **THEN** the output MUST include `decision`, `reason_code`, and `reason_text`
- **AND** the output MUST include `evidence_spans` with source excerpts when available
- **AND** the output MUST preserve enough structured context to render procedure subtype, pediatric flag, ASA estimate, and support recommendation downstream

### Requirement: Pediatric Requests SHALL Be Explicitly Flagged

The system SHALL explicitly flag pediatric cases within the rewritten EDA rulebook so that the marker remains available to downstream messaging.

#### Scenario: Supported EDA request is pediatric

- **WHEN** patient age is below 16 years in a supported EDA request
- **THEN** the system MUST mark the request as pediatric
- **AND** the recommendation context MUST preserve that pediatric signal for downstream Room-2 rendering

## ADDED Requirements

### Requirement: Supported EDA Recommendation SHALL Include Practical ASA Estimate And Support Recommendation

The system SHALL derive a practical and conservative ASA estimate for supported EDA requests and SHALL use it to synthesize the support recommendation shown to clinical reviewers.

#### Scenario: Practical ASA indicates lower procedural support needs

- **WHEN** the available clinical evidence supports practical ASA bucket `I-II`
- **THEN** the system MUST emit `ASA estimado: I-II`
- **AND** the support recommendation MUST allow sedation by the endoscopist without requiring anesthetist support

#### Scenario: Practical ASA indicates higher procedural support needs

- **WHEN** the available clinical evidence supports practical ASA bucket `III ou mais`
- **THEN** the system MUST emit `ASA estimado: III ou mais`
- **AND** the support recommendation MUST be at least `anestesista`

#### Scenario: Practical ASA and context indicate cardiovascular risk high enough for ICU support

- **WHEN** the practical ASA estimate and supporting cardiovascular context indicate moderate-to-high cardiovascular risk
- **THEN** the support recommendation MUST be `anestesista_uti`

#### Scenario: Practical ASA cannot be estimated safely

- **WHEN** the report lacks sufficient evidence for a practical ASA bucket
- **THEN** the system MUST preserve explicit fallback equivalent to `não foi possível estimar com os dados apresentados`
- **AND** the support recommendation MUST remain derivable from the remaining confirmed evidence without inventing a formal ASA class

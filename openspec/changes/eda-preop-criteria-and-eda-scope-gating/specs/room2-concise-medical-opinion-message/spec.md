# Specification Delta

## ADDED Requirements

### Requirement: Room-2 Summary SHALL Explain Deterministic Preop Denial Causes

When deterministic EDA pre-procedure policy denies recommendation due to missing prerequisite exams under reported risk, message II SHALL present concise explicit justification.

#### Scenario: Denial due to cardiovascular risk without ECG

- **WHEN** deterministic policy returns reason code `missing_ecg_with_cardiovascular_disease`
- **THEN** Room-2 summary MUST include concise text stating cardiovascular disease was reported and ECG report is missing
- **AND** the summary MUST keep decision-oriented wording suitable for physician review

#### Scenario: Denial due to respiratory risk without chest X-ray

- **WHEN** deterministic policy returns reason code `missing_chest_xray_with_respiratory_risk`
- **THEN** Room-2 summary MUST include concise text stating respiratory risk was reported and chest X-ray report is missing
- **AND** the summary MUST keep decision-oriented wording suitable for physician review

### Requirement: Out-Of-Scope Manual Review Cases SHALL Not Publish Room-2 Recommendation Summary

The system SHALL avoid publishing Room-2 recommendation summary for requests routed to manual review by EDA scope gating.

#### Scenario: Manual review required due to non-EDA or unknown exam type

- **WHEN** scope gating resolves to `manual_review_required` for non-EDA or unknown exam type
- **THEN** the system MUST NOT post Room-2 recommendation summary blocks for that case in the same processing cycle
- **AND** closure communication MUST be handled through Room-1 manual-review notification

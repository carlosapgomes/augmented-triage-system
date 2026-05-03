# nir-web-intake Specification

## ADDED Requirements

### Requirement: NIR SHALL Create Cases From Web PDF Upload

The system SHALL allow authenticated `nir` users to create a case by uploading a PDF through the web application.

#### Scenario: NIR uploads a valid referral PDF

- **WHEN** an authenticated `nir` user submits a valid PDF upload
- **THEN** the system MUST create a new case
- **AND** the system MUST persist auditable evidence that the case was created from the web intake surface
- **AND** the downstream processing flow MUST start normally

### Requirement: NIR Intake SHALL Validate PDF Submission Deterministically

The system SHALL reject invalid upload attempts deterministically.

#### Scenario: NIR submits no file

- **WHEN** an authenticated `nir` user submits the intake form without a PDF file
- **THEN** the system MUST reject the submission with deterministic validation feedback

#### Scenario: NIR submits a non-PDF file

- **WHEN** an authenticated `nir` user submits a file outside the accepted PDF rules
- **THEN** the system MUST reject the submission with deterministic validation feedback

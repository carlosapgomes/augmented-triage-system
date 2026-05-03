# nir-web-case-tracking Specification

## Purpose

Define the authenticated NIR web surfaces used to inspect case progress,
review final results, and confirm final receipt through the Django operations
app.

## Requirements

### Requirement: NIR SHALL Track Case Progress Through The Web Surface

The system SHALL allow authenticated `nir` users to inspect case progress,
status, and final outcome through the web app.

#### Scenario: NIR opens case list

- **WHEN** an authenticated `nir` user requests the NIR case list page
- **THEN** the system MUST return recent or relevant cases for the NIR workflow
- **AND** each case entry MUST expose operational progress information

#### Scenario: NIR opens case detail

- **WHEN** an authenticated `nir` user opens one case detail page
- **THEN** the system MUST show the case progress and timeline in a way
  suitable for NIR follow-up

### Requirement: NIR SHALL Confirm Final Receipt Explicitly In The Web App

The system SHALL replace message-based final human acknowledgment with an
explicit web acknowledgment action by NIR.

#### Scenario: Web confirmation becomes the canonical human closure checkpoint

- **WHEN** the workflow reaches the final NIR acknowledgment stage in the
  web-only operating model
- **THEN** the logical human closure checkpoint MUST depend on the web
  confirmation action
- **AND** it MUST no longer depend on a human Room-1 reaction
- **AND** the canonical human cleanup trigger MUST migrate from Matrix reaction
  to the web confirmation action

#### Scenario: NIR confirms final result receipt

- **WHEN** an authenticated `nir` user confirms the final result from the case
  detail page
- **THEN** the system MUST persist the acknowledgment as auditable user action
- **AND** the case MUST continue through the configured logical
  closure/cleanup path only once

#### Scenario: NIR repeats final receipt confirmation

- **WHEN** an authenticated `nir` user retries a final acknowledgment that was
  already accepted
- **THEN** the system MUST behave idempotently
- **AND** it MUST NOT duplicate closure side effects

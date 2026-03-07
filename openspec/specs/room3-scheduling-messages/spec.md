# room3-scheduling-messages Specification

## Purpose

Define o formato, conteúdo e comportamento das mensagens de agendamento no Room-3, incluindo solicitação, template de resposta, confirmação, e mensagens de erro.

## Requirements

### Requirement: Room-3 SHALL Publish Two-Message Scheduling Combo

The system SHALL publish a deterministic two-message combo in Room-3 for each case accepted by a doctor. Message I MUST provide scheduling context with patient information and the name of the doctor who accepted. Message II MUST provide a strict reply template.

#### Scenario: Case enters Room-3 scheduling stage

- **WHEN** a case is accepted by a doctor and transitions to Room-3
- **THEN** the bot MUST post message I with scheduling request containing patient identification
- **AND** message I MUST include `aceito por: <doctor_display_name>` below the requested exam
- **AND** when `doctor_display_name` is not available, the system MUST show `aceito por: não informado`
- **AND** the bot MUST post message II as a reply to message I with the strict scheduling template

### Requirement: Scheduling Template SHALL Use Brazilian Date Format

The scheduling reply template MUST display the date format as `DD/MM/YYYY HH:MM` using forward slashes, which is the standard Brazilian date notation.

#### Scenario: Scheduler views the reply template

- **WHEN** the scheduler opens the reply template message
- **THEN** the `data_hora` field MUST show placeholder `DD/MM/YYYY HH:MM`
- **AND** the template MUST NOT include timezone suffix in the placeholder

### Requirement: Timezone SHALL Be Configurable Via Environment

The system SHALL use a configurable default timezone for parsing and displaying dates, avoiding hardcoded timezone values.

#### Scenario: System starts with valid timezone

- **WHEN** the application starts with `TRIAGE_DEFAULT_TIMEZONE` set to a valid IANA timezone identifier
- **THEN** the system MUST use that timezone for all date/time operations in Room-3
- **AND** if not set, the system MUST default to `America/Bahia` (BRT)

#### Scenario: System starts with invalid timezone

- **WHEN** the application starts with `TRIAGE_DEFAULT_TIMEZONE` set to an invalid timezone
- **THEN** the system MUST fail fast with a clear error message indicating the invalid timezone

### Requirement: Scheduling Messages SHALL Use Correct Portuguese Orthography

All scheduling messages MUST use correct Portuguese orthography, including proper accents and cedillas.

#### Scenario: Scheduler views any Room-3 message

- **WHEN** any Room-3 message is displayed
- **THEN** the word "instruções" MUST be spelled with the correct accent and cedilla
- **AND** all other Portuguese words MUST follow standard orthography rules

### Requirement: Date Parser SHALL Accept Both Hyphen And Slash Formats

The scheduler reply parser MUST accept both `DD-MM-YYYY HH:MM` and `DD/MM/YYYY HH:MM` date formats to maintain backward compatibility.

#### Scenario: Scheduler submits date with slash format

- **WHEN** a scheduler reply contains `data_hora: 15/03/2026 14:30`
- **THEN** the system MUST parse the date successfully
- **AND** the parsed datetime MUST be interpreted in the configured default timezone

#### Scenario: Scheduler submits date with hyphen format (legacy)

- **WHEN** a scheduler reply contains `data_hora: 15-03-2026 14:30`
- **THEN** the system MUST parse the date successfully
- **AND** the parsed datetime MUST be interpreted in the configured default timezone

### Requirement: Scheduling Acknowledgment SHALL Confirm Case Closure

The scheduling acknowledgment message MUST clearly indicate that the reaction confirms awareness of case closure.

#### Scenario: Bot posts acknowledgment message

- **WHEN** the bot posts the Room-3 acknowledgment target message
- **THEN** the message MUST include the text `Reaja com +1 para confirmar ciência do encerramento.`
- **AND** this text MUST replace the previous generic confirmation text

### Requirement: Error Reprompt SHALL Use Brazilian Date Format

When the scheduler submits an invalid reply, the error reprompt message MUST display the correct Brazilian date format in the template.

#### Scenario: Scheduler submits invalid reply

- **WHEN** the scheduler submits a reply that cannot be parsed
- **THEN** the bot MUST reply with an error message containing a correction template
- **AND** the correction template MUST show `data_hora: DD/MM/YYYY HH:MM`
- **AND** the word "instruções" MUST be spelled correctly

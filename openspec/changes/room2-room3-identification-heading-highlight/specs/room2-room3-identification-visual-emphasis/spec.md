# room2-room3-identification-visual-emphasis Delta Specification

## ADDED Requirements

### Requirement: Room-2 First Textual Post SHALL Highlight Human Identification Lines

The system SHALL render `no. ocorrência` and `paciente` with heading-level visual emphasis in the first textual post sent to Room-2 (`room2_case_summary`), while preserving the same semantic values and ordering.

#### Scenario: Room-2 summary message is posted for doctor review

- **WHEN** the bot renders the Room-2 summary message body
- **THEN** `no. ocorrência` MUST be rendered as a Markdown heading line
- **AND** `paciente` MUST be rendered as a Markdown heading line immediately after it
- **AND** the message MUST preserve existing downstream sections (`Resumo clínico`, `Achados críticos`, `Pendências críticas`, `Decisão sugerida`, `Suporte recomendado`, `Motivo objetivo`, `Conduta sugerida`)

#### Scenario: Room-2 summary formatted HTML is posted

- **WHEN** the bot renders `formatted_body` HTML for Room-2 summary
- **THEN** `no. ocorrência` MUST be rendered with heading-level HTML emphasis
- **AND** `paciente` MUST be rendered with heading-level HTML emphasis
- **AND** the message MUST keep existing section hierarchy and content semantics unchanged

### Requirement: Room-3 First Post SHALL Highlight Human Identification Lines

The system SHALL render `no. ocorrência` and `paciente` with heading-level Markdown emphasis in the first scheduling request post sent to Room-3 (`room3_request`).

#### Scenario: Room-3 scheduling request is posted

- **WHEN** the bot renders the Room-3 request message body
- **THEN** `no. ocorrência` MUST be rendered as a Markdown heading line
- **AND** `paciente` MUST be rendered as a Markdown heading line immediately after it
- **AND** existing scheduling context lines (`idade`, `exame solicitado`) and guidance steps MUST remain present

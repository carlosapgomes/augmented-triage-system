# case-thread-monitoring-dashboard Delta Specification

## MODIFIED Requirements

### Requirement: Dashboard SHALL Show Chronological Case Thread Across Rooms

The system SHALL provide a per-case detail view with both `Fluxo por Etapas` and `Histórico Completo`, including the chronological sequence of messages/events across Room-1, Room-2, and Room-3 with visual room identification for authenticated operational users.

#### Scenario: Reader opens a case timeline

- **WHEN** an authenticated `reader` opens the detail view for a case
- **THEN** the system MUST return events ordered chronologically for that case
- **AND** each event MUST include room identifier, timestamp, actor/sender, and event type

#### Scenario: Admin opens a case timeline

- **WHEN** an authenticated `admin` opens the detail view for a case
- **THEN** the system MUST return events ordered chronologically for that case
- **AND** each event MUST include room identifier, timestamp, actor/sender, and event type

#### Scenario: Reader accesses full event content in Histórico Completo

- **WHEN** an authenticated `reader` opens the `Histórico Completo` view for a case with truncated excerpts
- **THEN** the system MUST provide a per-event control to expand and collapse full content text
- **AND** the full content shown MUST use the persisted event transcript/payload for that event

#### Scenario: Fluxo por Etapas shows PDF report toggle in the case details card

- **WHEN** an authenticated operational user opens `Fluxo por Etapas` for a case that has `pdf_report_extracted`
- **THEN** the top `Detalhe do Caso` card MUST show a control labeled to exibir/ocultar relatório PDF extraído
- **AND** the extracted PDF report text MUST start collapsed by default

#### Scenario: User toggles report visibility in Fluxo por Etapas

- **WHEN** the user clicks the report control in the top `Detalhe do Caso` card
- **THEN** the system MUST expand the same card and reveal the full persisted `pdf_report_extracted` text
- **AND** a subsequent click MUST collapse and hide the report text again

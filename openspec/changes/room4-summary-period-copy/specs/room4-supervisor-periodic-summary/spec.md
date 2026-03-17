# Specification Delta

## MODIFIED Requirements

### Requirement: Summary Message SHALL Include Required Window And Metric Fields

The summary message SHALL include a single user-facing local period reference and the minimum required metrics for supervisory operations, combining concluded outcomes for the period with the current operational backlog at the time the summary is emitted.

#### Scenario: Rendering supervisor summary payload

- **WHEN** the worker renders the Room-4 summary message
- **THEN** the message MUST include a single local period reference derived from the configured summary timezone in the format `Período: DD/MM/AAAA HH:MM → DD/MM/AAAA HH:MM`
- **AND** it MUST NOT include a UTC mirror line in the message body
- **AND** it MUST NOT include the textual timezone name in the message body
- **AND** it MUST include concluded-outcome totals for at least:
  - `pacientes recebidos`;
  - `relatórios processados`;
  - `casos avaliados`;
  - `aceitos por agendamento`;
  - `vinda imediata`;
  - `recusados`
- **AND** it MUST include current-backlog totals for at least:
  - `casos em andamento`;
  - `aguardando Sala 2`;
  - `aguardando Sala 3`;
  - `aguardando Sala 1`;
  - `pendentes no ramo vinda imediata`

# room4-supervisor-periodic-summary Delta Specification

## MODIFIED Requirements

### Requirement: Room-4 Periodic Summary SHALL Present a Single Local Period Reference

#### Scenario: Rendering a periodic Room-4 summary message

- **WHEN** the bot renders the Room-4 periodic summary
- **THEN** the message MUST include only metrics that belong to the displayed reporting window
- **AND** it MUST include `Pacientes recebidos`, `Relatórios processados`, `Casos avaliados`, `Aceitos por agendamento`, `Vinda imediata`, and `Recusados`
- **AND** it MUST NOT include backlog snapshot lines such as `Casos em andamento`, `Aguardando Sala 2`, `Aguardando Sala 3`, `Aguardando Sala 1`, or `Pendentes no ramo vinda imediata`

# Web triage workflow migration

## Why

Após decidir pela adoção de uma interface web em Django, o ATS precisa migrar o fluxo operacional humano completo para páginas e formulários, deixando de depender de interação direta por mensagens para NIR, médico e agendamento. Essa migração precisa preservar o backend de orquestração, a rastreabilidade por caso e a auditabilidade individual de quem executou cada etapa.

## What Changes

- Migrar a entrada operacional do NIR para upload web de PDFs e acompanhamento de casos.
- Migrar a decisão médica para fila e formulário web, substituindo a resposta humana via Room-2.
- Migrar a confirmação/negação do agendamento para fila e formulário web, substituindo a resposta humana via Room-3.
- Migrar o recebimento do resultado final pelo NIR para uma confirmação explícita via web, substituindo a confirmação humana por mensagem/reação.
- Preservar os dados de caso, transições de estado, jobs downstream e trilha de auditoria já existente, alterando apenas a superfície de interação humana.
- Registrar no histórico do caso tanto eventos automáticos quanto ações humanas originadas da nova web app.
- Eliminar a necessidade de convivência operacional entre interface web e interface por mensagens para esses perfis.
- Assumir explicitamente um hard refactor sem compatibilidade legada nem operação paralela do sistema antigo durante a implantação da versão web.

## Capabilities

### New Capabilities

- `nir-web-intake`: superfície NIR para envio de PDF, criação de caso e visualização básica da fila de encaminhamentos.
- `doctor-web-decision`: fila médica web e formulário estruturado para decisão clínica do caso.
- `scheduler-web-confirmation`: fila do agendador e formulário web para confirmar ou negar agendamento.
- `nir-web-case-tracking`: acompanhamento NIR do progresso do caso, visualização do resultado final e confirmação explícita de recebimento/fechamento.

### Modified Capabilities

- `runtime-orchestration`: o fluxo operacional humano deixa de depender das interações diretas por mensagens de Room-1/Room-2/Room-3 e passa a aceitar entrada/decisão/confirmação humanas via web, preservando a máquina de estados e os jobs clínicos.
- `full-transcript-persistence`: o histórico auditável do caso passa a incluir também ações humanas originadas da web app, além de PDF, LLM e eventos de sistema.
- `case-thread-monitoring-dashboard`: o histórico cronológico do caso precisa refletir ações web humanas nas etapas NIR, médica e de agendamento, mantendo ordenação auditável.
- `manual-e2e-readiness`: o runbook manual precisa validar o fluxo operacional web completo no lugar dos passos humanos por mensagens.

## Impact

- Código afetado:
  - novo app Django operacional
  - serviços de aplicação ligados a intake, decisão médica, agendamento e fechamento
  - persistência de auditoria/transcritos do caso
  - dashboards e detalhes de caso
- Banco de dados:
  - possível extensão de tabelas e/ou novas projeções para registrar ações web e filas por papel
- UI:
  - novas páginas para NIR, médico e agendador baseadas nos mocks de `demo/`
- Runtime:
  - **BREAKING**: perfis operacionais humanos deixam de executar o fluxo principal via mensagens e passam a operar exclusivamente pela web app
- Testes:
  - necessidade de cobertura TDD por slice para páginas, formulários, persistência e continuidade do fluxo clínico

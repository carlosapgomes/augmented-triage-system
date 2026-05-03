# Slice 1.1 - Shared workflow projections

## Goal

Criar as projeções/queries compartilhadas que sustentam filas e cards operacionais para NIR, médico e agendador, e fixar o contrato mínimo dos eventos humanos web que entrarão na timeline do caso.

## Context

Este slice prepara a base de leitura do novo fluxo web. Ainda não implementa páginas funcionais completas, apenas os dados necessários para sustentá-las de forma consistente.

## Scope boundaries

**Included:** consultas/projeções de leitura por etapa do workflow, testes focados de ordenação e filtros, contratos mínimos para cards/detalhes, e contrato físico/lógico mínimo dos eventos web (`origem`, `ator`, `timestamp`, `payload textual resumido`, `case_id`).

**Excluded:** upload NIR, formulários médicos/agendamento, confirmação final do NIR.

## Tests to write FIRST (TDD)

- casos aguardando médico aparecem na projeção médica;
- casos aguardando agendamento aparecem na projeção do scheduler;
- casos recentes/progresso aparecem na projeção NIR;
- ordenação e campos mínimos são determinísticos;
- o contrato mínimo dos eventos web do caso fica explícito e consistente para reuso nos slices seguintes.

## Success criteria

- existe base estável para as filas web por papel;
- leituras não redesenham a máquina de estados;
- contratos de card/detalhe são reutilizáveis;
- o contrato mínimo da timeline para eventos web fica travado cedo e evita divergência nos slices seguintes.

## Mandatory report file

- Write the implementation report to: `/tmp/web-triage-workflow-migration-01-shared-workflow-projections-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: web-triage-workflow-migration
Task file: openspec/changes/web-triage-workflow-migration/tasks/01-shared-workflow-projections.md
Implement only this slice.
Use strict TDD.
Do not create full pages or mutate workflow state yet.
Keep logic in application/domain, not in adapters.
Make the web-event timeline contract explicit and reusable.
Run gates, update checklist, commit, push, and stop.
Include SNP before/after in the report.
Write the full implementation report to `/tmp/web-triage-workflow-migration-01-shared-workflow-projections-report.md`.
In your final response, provide the exact report file path.
```

# Slice 3.1 - Doctor queue

## Goal

Implementar a fila médica web baseada em casos aguardando decisão.

## Context

O NIR já cria e acompanha casos. Agora o médico precisa receber uma fila web enxuta com resumo suficiente para decidir.

## Scope boundaries

**Included:** página de fila médica, cards/resumos de caso, filtros mínimos se necessários, autorização por papel.

**Excluded:** submissão da decisão, agendamento, ack final NIR.

## Tests to write FIRST (TDD)

- casos em `WAIT_DOCTOR` aparecem na fila;
- casos fora do estágio não aparecem;
- somente `doctor` acessa a fila médica.

## Success criteria

- médico enxerga apenas trabalho pendente da sua etapa;
- a fila é derivada deterministicamente do estado do caso.

## Mandatory report file

- Write the implementation report to: `/tmp/web-triage-workflow-migration-04-doctor-queue-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: web-triage-workflow-migration
Task file: openspec/changes/web-triage-workflow-migration/tasks/04-doctor-queue.md
Implement only this slice.
Use strict TDD.
Do not implement the decision submission yet.
Keep summaries aligned with the approved doctor mock where feasible.
Run gates, update checklist, commit, push, and stop.
Include SNP before/after.
```

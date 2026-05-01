# Slice 4.1 - Scheduler queue

## Goal

Implementar a fila web do agendador para casos aguardando ação de agendamento.

## Context

As decisões médicas web já foram concluídas. Agora os casos aceitos que seguem para agendamento precisam aparecer para o perfil `scheduler`.

## Scope boundaries

**Included:** listagem de pendências do agendador, resumo operacional do caso, autorização por papel.

**Excluded:** submissão do formulário de agendamento, ack final NIR.

## Tests to write FIRST (TDD)

- casos em `WAIT_APPT` aparecem na fila;
- casos fora do estágio não aparecem;
- somente `scheduler` acessa a fila.

## Success criteria

- o agendador vê apenas os casos corretos;
- a fila deriva do estado real do workflow.

## Mandatory report file

- Write the implementation report to: `/tmp/web-triage-workflow-migration-06-scheduler-queue-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: web-triage-workflow-migration
Task file: openspec/changes/web-triage-workflow-migration/tasks/06-scheduler-queue.md
Implement only this slice.
Use TDD.
Do not implement the confirmation form yet.
Keep UI close to the approved scheduler mock where practical.
Run gates, update checklist, commit, push, and stop.
Report SNP before/after.
Write the full implementation report to `/tmp/web-triage-workflow-migration-06-scheduler-queue-report.md`.
In your final response, provide the exact report file path.
```

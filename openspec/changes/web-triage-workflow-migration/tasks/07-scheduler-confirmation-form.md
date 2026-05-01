# Slice 4.2 - Scheduler confirmation form

## Goal

Implementar o formulário web de confirmação/negação do agendamento.

## Context

A fila do agendador já existe. Agora o perfil `scheduler` precisa confirmar ou negar agendamento pela web, sem template humano em Room-3.

## Scope boundaries

**Included:** formulário de confirmação/negação, validações de data/hora/motivo, persistência da ação, continuação do workflow.

**Excluded:** confirmação final do NIR, ajustes de manager/admin.

## Tests to write FIRST (TDD)

- confirmação válida persiste data/hora e progride o caso;
- negativa válida persiste motivo e progride o caso;
- payload inválido é rejeitado sem mutação;
- ação do agendador fica auditável.

## Success criteria

- o agendamento humano passa a ocorrer exclusivamente via web;
- regras do ramo confirmado/negado são preservadas.

## Mandatory report file

- Write the implementation report to: `/tmp/web-triage-workflow-migration-07-scheduler-confirmation-form-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: web-triage-workflow-migration
Task file: openspec/changes/web-triage-workflow-migration/tasks/07-scheduler-confirmation-form.md
Implement only this slice.
Use strict TDD.
Prefer reusing existing scheduler semantics/contracts.
Run gates, update checklist, commit, push, and stop.
Include SNP before/after.
```

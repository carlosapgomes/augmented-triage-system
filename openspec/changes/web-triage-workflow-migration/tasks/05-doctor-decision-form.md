# Slice 3.2 - Doctor decision form

## Goal

Implementar o formulário web de decisão médica reutilizando a semântica clínica já existente.

## Context

A fila médica já existe. Agora o médico precisa enviar `accept`/`deny`, `support_flag`, `admission_flow` e `reason` pela web, sem reply manual em Room-2.

## Scope boundaries

**Included:** página/formulário de decisão, validações por branch, persistência da ação humana, continuação do workflow.

**Excluded:** fila do scheduler, ack final NIR.

## Tests to write FIRST (TDD)

- aceitar com campos válidos progride para o próximo ramo esperado;
- negar com motivo válido segue ramo de negativa;
- payload inválido é rejeitado sem mutação;
- ação fica auditável e cronologicamente visível.

## Success criteria

- decisão médica web substitui a interação humana por mensagem;
- semântica clínica existente é preservada;
- transições inválidas não passam.

## Mandatory report file

- Write the implementation report to: `/tmp/web-triage-workflow-migration-05-doctor-decision-form-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: web-triage-workflow-migration
Task file: openspec/changes/web-triage-workflow-migration/tasks/05-doctor-decision-form.md
Implement only this slice.
Use strict TDD.
Prefer reusing existing decision services/contracts instead of inventing a parallel rule path.
Run gates, update checklist, commit, push, and stop.
Include detailed report with SNP before/after.
Write the full implementation report to `/tmp/web-triage-workflow-migration-05-doctor-decision-form-report.md`.
In your final response, provide the exact report file path.
```

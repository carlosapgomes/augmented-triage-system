# Slice 5.2 - Web workflow audit visibility

## Goal

Atualizar timeline/dashboard/runbook manual para refletir ações web humanas no fluxo completo.

## Context

O workflow web já está funcional. Este slice consolida a visibilidade auditável das novas ações humanas e ajusta a documentação/manual E2E.

## Scope boundaries

**Included:** timeline/detalhe do caso, ajustes de dashboard relacionados à nova origem dos eventos, runbook manual e espelhos bilíngues quando necessário.

**Excluded:** novas features operacionais fora da visibilidade/auditoria.

## Implementation guardrail

- Não acessar atributos protegidos/internos de services a partir de views/adapters (por exemplo: `_case_repository`, `_audit_repository`, `_job_queue`).
- Se a view precisar de dados adicionais, expor método público explícito no application layer.

## Tests to write FIRST (TDD)

- timeline mostra ações NIR/doctor/scheduler web em ordem cronológica;
- origem/ator dos eventos web é distinguível;
- documentação/manual cobre o fluxo web completo.

## Success criteria

- o caso continua explicável ponta a ponta no histórico;
- o runbook manual reflete a nova operação web.

## Mandatory report file

- Write the implementation report to: `/tmp/web-triage-workflow-migration-09-web-workflow-audit-visibility-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: web-triage-workflow-migration
Task file: openspec/changes/web-triage-workflow-migration/tasks/09-web-workflow-audit-visibility.md
Implement only this slice.
Use TDD where code behavior changes.
If docs are changed, keep bilingual mirrors in sync and run the doc guards.
Do not access protected/internal service attributes from views/adapters; add explicit public application-layer methods if needed.
Run gates, update checklist, commit, push, and stop.
Report SNP before/after.
Write the full implementation report to `/tmp/web-triage-workflow-migration-09-web-workflow-audit-visibility-report.md`.
In your final response, provide the exact report file path.
```

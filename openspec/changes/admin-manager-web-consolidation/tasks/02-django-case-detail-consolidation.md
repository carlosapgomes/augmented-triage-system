# Slice 1.2 - Django case detail consolidation

## Goal

Consolidar o detalhe de caso no Django com timeline auditável para `manager` e `admin`.

## Context

A listagem do dashboard já está consolidada. Agora a supervisão precisa abrir o detalhe do caso com resumo operacional e timeline preservada.

## Scope boundaries

**Included:** detalhe do caso, timeline, resumo operacional, autorização `manager`/`admin`.

**Excluded:** usuários, prompts, navegação final completa.

## Tests to write FIRST (TDD)

- `manager` acessa detalhe do caso;
- timeline auditável continua visível;
- controles admin-only não aparecem para `manager`.

## Success criteria

- detalhe consolidado mantém auditabilidade;
- leitura por `manager` é segura e suficiente.

## Mandatory report file

- Write the implementation report to: `/tmp/admin-manager-web-consolidation-02-django-case-detail-consolidation-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: admin-manager-web-consolidation
Task file: openspec/changes/admin-manager-web-consolidation/tasks/02-django-case-detail-consolidation.md
Implement only this slice.
Use TDD.
Do not begin users/prompts consolidation yet.
Run gates, update checklist, commit, push, and stop.
Report SNP before/after.
Write the full implementation report to `/tmp/admin-manager-web-consolidation-02-django-case-detail-consolidation-report.md`.
In your final response, provide the exact report file path.
```

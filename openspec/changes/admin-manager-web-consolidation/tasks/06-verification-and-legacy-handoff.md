# Slice 4.1 - Verification and legacy handoff

## Goal

Atualizar auditoria, runbook manual, testes de autorização e handoff da superfície antiga após a consolidação `manager`/`admin`.

## Context

Dashboard, shell e áreas administrativas já foram consolidados. Este slice fecha o change com verificação e preparação para desativação controlada da superfície antiga.

A partir deste handoff, as superfícies humanas/admin em FastAPI e Matrix devem ser tratadas explicitamente como legado a ser retirado, não como baseline de convivência.

## Scope boundaries

**Included:** documentação/manual E2E, testes finais de autorização, checklist OpenSpec, notas de handoff legado e instruções explícitas de hard cutover para a superfície Django consolidada.

**Excluded:** novas features funcionais.

## Tests to write FIRST (TDD)

- somente quando houver lacuna real de verificação final identificada.

## Success criteria

- matriz `manager` vs `admin` está documentada e verificada;
- existe handoff claro para desativação da superfície antiga;
- a documentação final deixa explícito que não há requisito de compatibilidade legada após o cutover.

## Mandatory report file

- Write the implementation report to: `/tmp/admin-manager-web-consolidation-06-verification-and-legacy-handoff-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: admin-manager-web-consolidation
Task file: openspec/changes/admin-manager-web-consolidation/tasks/06-verification-and-legacy-handoff.md
Implement only this slice.
Do not add new product features.
Focus on verification, documentation sync, and explicit legacy retirement handoff.
Document the Django surface as the final supported human/admin interface for this scope.
Run gates, update checklist, commit, push, and stop.
Report SNP before/after.
Write the full implementation report to `/tmp/admin-manager-web-consolidation-06-verification-and-legacy-handoff-report.md`.
In your final response, provide the exact report file path.
```

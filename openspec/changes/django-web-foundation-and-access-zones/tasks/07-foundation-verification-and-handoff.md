# Slice 5.1 - Foundation verification and handoff

## Goal

Fechar o change de fundação com verificação integrada, documentação necessária e handoff claro para o próximo change de migração funcional.

## Context

Todos os slices anteriores da fundação Django já foram implementados. Este slice apenas consolida, valida e prepara a transição para o change seguinte.

## Scope boundaries

**Included:** testes integrados focados, ajustes finais de documentação, atualização de checklist OpenSpec, handoff para `web-triage-workflow-migration`.

**Excluded:** novas features funcionais.

## Tests to write FIRST (TDD)

- somente se houver lacuna real de verificação integrada identificada no fechamento.

## Success criteria

- fundação Django validada end-to-end no escopo aprovado;
- artefatos OpenSpec atualizados;
- documentação mínima de operação/handoff pronta.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: django-web-foundation-and-access-zones
Task file: openspec/changes/django-web-foundation-and-access-zones/tasks/07-foundation-verification-and-handoff.md
Implement only this slice.
Do not start the workflow migration change.
Focus on verification, documentation sync, and explicit handoff quality.
Run all relevant gates, commit, push, and stop.
Include a detailed report with SNP before/after for any final changes.
```

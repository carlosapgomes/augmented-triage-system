# Slice 1.1 - Django dashboard consolidation

## Goal

Consolidar a listagem principal de dashboard no Django para `manager` e `admin`.

## Context

Os fluxos operacionais já foram migrados para a web. Este slice só deve começar depois do slice `openspec/changes/web-triage-workflow-migration/tasks/09-web-workflow-audit-visibility.md`, para garantir que a timeline web completa já esteja estabilizada. Agora a supervisão precisa consumir esses dados no Django de forma consolidada e read-only para `manager`.

## Scope boundaries

**Included:** dashboard list, filtros/totais necessários, autorização `manager`/`admin`, testes HTTP e de dados.

**Excluded:** detalhe completo do caso, usuários, prompts.

## Tests to write FIRST (TDD)

- `manager` acessa dashboard consolidado;
- `admin` acessa dashboard consolidado;
- papéis sem permissão são rejeitados;
- listagem mantém ordenação e totais esperados.

## Success criteria

- dashboard consolidado funciona no Django;
- `manager` permanece read-only;
- paridade funcional mínima com a visão operacional existente.

## Mandatory report file

- Write the implementation report to: `/tmp/admin-manager-web-consolidation-01-django-dashboard-consolidation-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: admin-manager-web-consolidation
Task file: openspec/changes/admin-manager-web-consolidation/tasks/01-django-dashboard-consolidation.md
Implement only this slice.
Use strict TDD.
Do not start case detail or admin surfaces yet.
Keep manager read-only.
Run gates, update checklist, commit, push, and stop.
Include SNP before/after.
```

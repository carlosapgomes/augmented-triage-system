# Slice 2.2 - NIR dashboard and case detail

## Goal

Implementar a listagem NIR e o detalhe inicial do caso com progresso operacional.

## Context

O NIR já consegue criar casos pela web. Agora precisa acompanhar o andamento e visualizar o histórico/progresso do encaminhamento.

## Scope boundaries

**Included:** página NIR de casos, detalhe do caso, indicadores de progresso, uso das projeções compartilhadas.

**Excluded:** confirmação final de recebimento, decisão médica, agendamento.

## Tests to write FIRST (TDD)

- NIR vê seus casos relevantes na listagem;
- detalhe mostra progresso e timeline adequada;
- acesso por papel é respeitado.

## Success criteria

- NIR consegue acompanhar os casos pela web;
- o detalhe torna o estado atual compreensível;
- o slice usa dados reais do workflow já persistido.

## Mandatory report file

- Write the implementation report to: `/tmp/web-triage-workflow-migration-03-nir-dashboard-and-case-detail-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: web-triage-workflow-migration
Task file: openspec/changes/web-triage-workflow-migration/tasks/03-nir-dashboard-and-case-detail.md
Implement only this slice.
Use TDD.
Do not add final-ack behavior yet.
Keep UI close to the approved NIR demo where practical.
Run gates, update checklist, commit, push, and stop.
Report SNP before/after.
Write the full implementation report to `/tmp/web-triage-workflow-migration-03-nir-dashboard-and-case-detail-report.md`.
In your final response, provide the exact report file path.
```

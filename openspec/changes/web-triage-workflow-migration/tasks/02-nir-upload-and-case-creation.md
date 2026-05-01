# Slice 2.1 - NIR upload and case creation

## Goal

Implementar o upload PDF do NIR e a criação do caso via web com auditoria individual.

## Context

A projeção compartilhada já existe. Agora o NIR precisa iniciar o caso pela web, substituindo a entrada humana original por mensagens.

## Scope boundaries

**Included:** formulário/upload NIR, validação de PDF, estratégia de storage temporário/persistência do arquivo, criação de caso, evidência auditável da ação web, disparo do job inicial já existente e estado operacional visível no NIR quando houver falha downstream.

**Excluded:** dashboard NIR completo, fila médica, agendador, confirmação final.

## Tests to write FIRST (TDD)

- upload PDF válido cria caso;
- upload sem arquivo é rejeitado;
- upload de não-PDF é rejeitado;
- ação do usuário NIR fica auditável;
- downstream inicial é disparado normalmente;
- falha downstream relevante deixa estado operacional visível para o NIR.

## Success criteria

- o caso passa a nascer pela web app NIR;
- a ação humana fica atribuída ao usuário autenticado;
- o pipeline clínico continua a partir da nova entrada;
- a persistência/storage do PDF e o estado operacional de erro ficam explícitos.

## Mandatory report file

- Write the implementation report to: `/tmp/web-triage-workflow-migration-02-nir-upload-and-case-creation-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: web-triage-workflow-migration
Task file: openspec/changes/web-triage-workflow-migration/tasks/02-nir-upload-and-case-creation.md
Implement only this slice.
Use strict TDD.
Do not implement the full NIR dashboard yet.
Preserve workflow semantics after case creation.
Make storage/persistence and downstream-failure visibility explicit in the implementation.
Run gates, update checklist, commit, push, and stop.
Include a detailed report with SNP before/after.
Write the full implementation report to `/tmp/web-triage-workflow-migration-02-nir-upload-and-case-creation-report.md`.
In your final response, provide the exact report file path.
```

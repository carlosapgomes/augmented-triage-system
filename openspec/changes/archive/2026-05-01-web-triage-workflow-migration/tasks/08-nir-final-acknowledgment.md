# Slice 5.1 - NIR final acknowledgment

## Goal

Implementar a visualização do resultado final no NIR e a confirmação explícita de recebimento/fechamento.

## Context

Depois da decisão médica e da resposta do agendador, o NIR precisa receber o resultado final pela web e concluir a ciência do caso sem usar reação em mensagem. Este slice muda explicitamente o checkpoint humano canônico de fechamento: ele deixa de ser a reação humana em Room-1 e passa a ser a confirmação web do NIR.

## Scope boundaries

**Included:** ação final de confirmação pelo NIR, idempotência, persistência auditável, migração explícita do checkpoint humano de fechamento para a confirmação web e avanço para fechamento lógico uma única vez.

**Excluded:** painéis manager/admin.

## Implementation guardrail

- Não acessar atributos protegidos/internos de services a partir de views/adapters (por exemplo: `_case_repository`, `_audit_repository`, `_job_queue`).
- Se a view precisar de dados adicionais, expor método público explícito no application layer.

## Tests to write FIRST (TDD)

- resultado final aparece para o NIR;
- confirmação válida é persistida;
- repetição da confirmação é idempotente;
- efeitos de fechamento não duplicam.

## Success criteria

- o ciclo humano do caso fecha integralmente pela web;
- o ack final continua determinístico e auditável;
- o fechamento humano canônico deixa explicitamente de depender da reação Matrix em Room-1.

## Mandatory report file

- Write the implementation report to: `/tmp/web-triage-workflow-migration-08-nir-final-acknowledgment-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: web-triage-workflow-migration
Task file: openspec/changes/web-triage-workflow-migration/tasks/08-nir-final-acknowledgment.md
Implement only this slice.
Use strict TDD.
Do not redesign clinical branch semantics, but do implement the approved migration of the canonical human closure checkpoint from Room-1 Matrix reaction to the NIR web confirmation action.
Do not access protected/internal service attributes from views/adapters; add explicit public application-layer methods if needed.
Run gates, update checklist, commit, push, and stop.
Include detailed report with SNP before/after.
Write the full implementation report to `/tmp/web-triage-workflow-migration-08-nir-final-acknowledgment-report.md`.
In your final response, provide the exact report file path.
```

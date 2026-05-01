# Slice 1.2 - Ansible stack consolidation

## Goal

Ajustar a automação Ansible/rootless para o stack consolidado no mesmo host.

## Context

A composição oficial de runtime já foi atualizada. Agora a automação de deploy precisa convergir esse stack sem perder idempotência.

## Scope boundaries

**Included:** playbooks/roles/vars relevantes, validações pós-deploy, testes/checks focados de automação.

**Excluded:** troubleshooting detalhado de publicação e runbooks finais.

## Tests to write FIRST (TDD)

- deploy converge o stack consolidado como usuário dedicado;
- rerun continua idempotente;
- validações pós-deploy cobrem o novo serviço web.

## Success criteria

- Ansible suporta o stack consolidado;
- baseline rootless e idempotência foram preservados.

## Mandatory report file

- Write the implementation report to: `/tmp/same-host-deployment-and-hardening-02-ansible-stack-consolidation-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: same-host-deployment-and-hardening
Task file: openspec/changes/same-host-deployment-and-hardening/tasks/02-ansible-stack-consolidation.md
Implement only this slice.
Use TDD where automation behavior is testable.
Do not expand into full runbook/troubleshooting yet.
Run gates, update checklist, commit, push, and stop.
Include detailed report with SNP before/after.
Write the full implementation report to `/tmp/same-host-deployment-and-hardening-02-ansible-stack-consolidation-report.md`.
In your final response, provide the exact report file path.
```

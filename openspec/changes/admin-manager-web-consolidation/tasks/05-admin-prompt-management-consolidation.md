# Slice 3.2 - Admin prompt management consolidation

## Goal

Consolidar a superfície de gestão de prompts no Django para `admin`.

## Context

A gestão de usuários já está consolidada. Agora a gestão de prompts precisa seguir a mesma estratégia, permanecendo exclusiva de `admin`.

## Scope boundaries

**Included:** página/rotas Django de prompts, autorização `admin`, negativas para `manager`, reutilização das regras existentes.

**Excluded:** novas políticas de prompt fora do escopo atual.

## Tests to write FIRST (TDD)

- `admin` acessa e muta prompts;
- `manager` é negado;
- auditoria de prompt continua preservada.

## Success criteria

- gestão de prompts está consolidada no Django;
- paridade de autorização foi preservada.

## Mandatory report file

- Write the implementation report to: `/tmp/admin-manager-web-consolidation-05-admin-prompt-management-consolidation-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: admin-manager-web-consolidation
Task file: openspec/changes/admin-manager-web-consolidation/tasks/05-admin-prompt-management-consolidation.md
Implement only this slice.
Use strict TDD.
Reuse existing prompt-management rules and audit semantics.
Run gates, update checklist, commit, push, and stop.
Include SNP before/after.
```

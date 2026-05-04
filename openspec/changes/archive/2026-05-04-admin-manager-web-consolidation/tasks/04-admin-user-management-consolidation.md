# Slice 3.1 - Admin user management consolidation

## Goal

Consolidar a superfície de gestão de usuários no Django para `admin`, cobrindo criação e mudança de role para `nir`, `doctor`, `scheduler`, `manager` e `admin`.

## Context

A separação visual entre `manager` e `admin` já existe. Agora a gestão de usuários precisa residir no Django final, preservando todas as invariantes de segurança existentes e fechando a migração conceitual `reader -> manager` / `admin -> admin`.

## Scope boundaries

**Included:** página/rotas Django de gestão de usuários, autorização `admin`, negativas para `manager`, reutilização das regras existentes.

**Excluded:** gestão de prompts.

## Tests to write FIRST (TDD)

- `admin` acessa a superfície consolidada;
- `manager` recebe `403`;
- `admin` consegue criar qualquer um dos cinco papéis suportados;
- `admin` consegue mudar o role de um usuário para outro papel suportado;
- ações continuam respeitando invariantes já existentes.

## Success criteria

- gestão de usuários está consolidada no Django;
- regras de segurança não regrediram;
- o modelo final de papéis está explícito e operacional.

## Mandatory report file

- Write the implementation report to: `/tmp/admin-manager-web-consolidation-04-admin-user-management-consolidation-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: admin-manager-web-consolidation
Task file: openspec/changes/admin-manager-web-consolidation/tasks/04-admin-user-management-consolidation.md
Implement only this slice.
Use strict TDD.
Reuse existing user-management rules; do not redesign them.
Run gates, update checklist, commit, push, and stop.
Include detailed report with SNP before/after.
Write the full implementation report to `/tmp/admin-manager-web-consolidation-04-admin-user-management-consolidation-report.md`.
In your final response, provide the exact report file path.
```

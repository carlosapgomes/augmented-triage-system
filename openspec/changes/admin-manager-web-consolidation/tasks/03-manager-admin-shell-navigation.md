# Slice 2.1 - Manager admin shell navigation

## Goal

Ajustar a navegação final do shell para separar claramente `manager` e `admin`.

## Context

Dashboard e detalhe já estão consolidados. Agora o shell precisa refletir visualmente e funcionalmente a diferença entre supervisão read-only e administração do sistema.

## Scope boundaries

**Included:** navegação role-aware final, visibilidade de itens por papel, testes de autorização/visibilidade.

**Excluded:** implementação interna das páginas de usuários/prompts se ainda não existirem.

## Tests to write FIRST (TDD)

- [x] `manager` vê apenas dashboard/relatórios;
- [x] `admin` vê dashboard + áreas administrativas;
- [x] links/admin routes permanecem negados para `manager`.

## Success criteria

- a navegação final deixa os limites de permissão claros;
- não há descoberta indevida de superfícies administrativas por `manager`.

## Mandatory report file

- Write the implementation report to: `/tmp/admin-manager-web-consolidation-03-manager-admin-shell-navigation-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: admin-manager-web-consolidation
Task file: openspec/changes/admin-manager-web-consolidation/tasks/03-manager-admin-shell-navigation.md
Implement only this slice.
Use strict TDD.
Do not expand scope beyond shell/navigation behavior.
Run gates, update checklist, commit, push, and stop.
Include SNP before/after.
```

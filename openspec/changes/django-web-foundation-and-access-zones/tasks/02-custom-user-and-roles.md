# Slice 2.1 - Custom user and roles

## Goal

Adicionar o modelo de usuário custom do Django com contas individuais e papéis `nir`, `doctor`, `scheduler`, `manager` e `admin`.

## Context

A fundação Django já existe. Agora o sistema precisa de uma base de identidade local que preserve rastreabilidade individual e suporte autorização por papel.

## Scope boundaries

**Included:** enum/modelo de papéis, user model custom, migração inicial, testes de persistência e validação de role.

**Excluded:** login/logout, redirecionamento por papel, restrições de intranet, PWA.

## Tests to write FIRST (TDD)

- usuário é persistido com um papel suportado;
- papel inválido é rejeitado deterministicamente;
- e-mail normalizado/único é preservado conforme desenho adotado.

## Success criteria

- o app Django possui user model custom funcional;
- os cinco papéis aprovados existem e são testados;
- a base suporta uma conta por pessoa.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: django-web-foundation-and-access-zones
Task file: openspec/changes/django-web-foundation-and-access-zones/tasks/02-custom-user-and-roles.md
Implement only this slice.
Write failing tests first.
Do not implement login, session, PWA, or network restrictions.
Keep migrations deterministic and reversible.
Update task tracking, run gates, commit, push, and stop.
Report SNP before/after.
```

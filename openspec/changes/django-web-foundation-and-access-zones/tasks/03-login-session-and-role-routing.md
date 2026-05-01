# Slice 2.2 - Login session and role routing

## Goal

Implementar login/logout/sessão no Django com redirecionamento pós-login específico por papel.

## Context

O modelo de usuário custom e os cinco papéis já existem. Agora a fundação precisa de autenticação web real para permitir entrada role-aware nas próximas superfícies.

## Scope boundaries

**Included:** formulário HTML de login, autenticação, logout, sessão, redirects por papel, testes HTTP.

**Excluded:** restrição de intranet, PWA, páginas funcionais completas por papel.

## Tests to write FIRST (TDD)

- login válido cria sessão;
- login inválido retorna erro HTML sem sessão;
- logout encerra sessão;
- cada papel é redirecionado para sua rota inicial.

## Success criteria

- autenticação web local funciona no Django;
- logout é explícito e determinístico;
- os cinco papéis possuem destino inicial definido.

## Mandatory report file

- Write the implementation report to: `/tmp/django-web-foundation-and-access-zones-03-login-session-and-role-routing-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: django-web-foundation-and-access-zones
Task file: openspec/changes/django-web-foundation-and-access-zones/tasks/03-login-session-and-role-routing.md
Implement only this slice.
Use strict TDD.
Do not add intranet restrictions or PWA yet.
Use minimal placeholder pages if needed only to satisfy redirects.
Run gates, update checklist, commit, push, and stop.
Include detailed report with SNP before/after.
Write the full implementation report to `/tmp/django-web-foundation-and-access-zones-03-login-session-and-role-routing-report.md`.
In your final response, provide the exact report file path.
```

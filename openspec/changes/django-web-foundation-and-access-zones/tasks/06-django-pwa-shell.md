# Slice 4.1 - Django PWA shell

## Goal

Entregar o shell mínimo do novo app Django, com PWA online-only apenas para `doctor`, `manager` e `admin`, e páginas iniciais mínimas por papel.

## Context

A equipe já usa o dashboard em modo instalável. O novo app precisa preservar essa experiência desde a fundação para os perfis remotos `doctor`, `manager` e `admin`, sem introduzir suporte offline. `nir` e `scheduler` continuam apenas em browser desktop na intranet.

## Scope boundaries

**Included:** manifest, service worker online-only, metadata installável, shell base, páginas mínimas por papel.

**Excluded:** fluxos completos NIR/Doctor/Scheduler/Admin/Manager.

## Tests to write FIRST (TDD)

- páginas autenticadas publicam metadata PWA;
- manifest responde com conteúdo válido;
- service worker não serve conteúdo clínico offline;
- app instalado preserva entrada role-aware com sessão ativa.

## Success criteria

- novo shell Django é instalável como PWA;
- comportamento permanece online-only;
- páginas mínimas por papel já existem como base navegável.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: django-web-foundation-and-access-zones
Task file: openspec/changes/django-web-foundation-and-access-zones/tasks/06-django-pwa-shell.md
Implement only this slice.
Use TDD.
Do not build the full operational workflows yet; only the shell/PWA foundation.
Keep offline support disabled.
Run gates, commit, push, and stop.
Report with SNP before/after.
```

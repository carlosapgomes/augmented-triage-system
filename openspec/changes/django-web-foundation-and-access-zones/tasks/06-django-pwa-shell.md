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

## Mandatory report file

- Write the implementation report to: `/tmp/django-web-foundation-and-access-zones-06-django-pwa-shell-report.md`
- In the final response, include the exact file path above so the user can copy it.

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
In the report, list the exact commands executed for pytest, ruff, mypy, and markdownlint.
Do not use `uv run ruff check .`; run ruff only on changed Python paths.
If any Markdown files are changed, run markdownlint on those exact paths and report the command.
If any files under `docs/*.md` are changed, also run and report `uv run pytest tests/unit/test_readme_bilingual_baseline.py tests/unit/test_docs_bilingual_mirror.py -q`.
Write the full implementation report to `/tmp/django-web-foundation-and-access-zones-06-django-pwa-shell-report.md`.
In your final response, provide the exact report file path.
```

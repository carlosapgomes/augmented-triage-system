# Slice 2.2 - Zone hardening and troubleshooting

## Goal

Adicionar hardening operacional, checklist de zona por papel e troubleshooting de primeira linha.

## Context

A topologia já está definida. Agora é preciso garantir que os caminhos certos estejam permitidos/negados para cada papel e que a operação saiba diagnosticar desvios.

## Scope boundaries

**Included:** checklist por papel/zona, hardening operacional documentado, troubleshooting inicial, critérios de escalonamento.

**Excluded:** redesign de autorização da aplicação.

## Tests to write FIRST (TDD)

- quando houver checagens automatizadas de configuração/topologia;
- para conteúdo operacional, produzir passos determinísticos verificáveis.

## Success criteria

- `nir`/`scheduler` têm validação explícita de negação fora da intranet;
- `doctor`/`manager`/`admin` têm validação explícita de acesso remoto aprovado;
- troubleshooting inicial está claro.

## Mandatory report file

- Write the implementation report to: `/tmp/same-host-deployment-and-hardening-04-zone-hardening-and-troubleshooting-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: same-host-deployment-and-hardening
Task file: openspec/changes/same-host-deployment-and-hardening/tasks/04-zone-hardening-and-troubleshooting.md
Implement only this slice.
Use TDD for any executable behavior changes.
Do not redesign app-level access control.
Focus on operational hardening and diagnostics.
Run gates, update checklist, commit, push, and stop.
Include SNP before/after where relevant.
In the report, list the exact commands executed for pytest, ruff, mypy, and markdownlint.
Do not use `uv run ruff check .`; run ruff only on changed Python paths.
If any Markdown files are changed, run markdownlint on those exact paths and report the command.
If any files under `docs/*.md` are changed, also run and report `uv run pytest tests/unit/test_readme_bilingual_baseline.py tests/unit/test_docs_bilingual_mirror.py -q`.
Write the full implementation report to `/tmp/same-host-deployment-and-hardening-04-zone-hardening-and-troubleshooting-report.md`.
In your final response, provide the exact report file path.
```

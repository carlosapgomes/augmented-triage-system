# Slice 2.1 - Publication topology

## Goal

Documentar e validar a topologia interna vs externa no mesmo host.

## Context

O stack consolidado já sobe no host. Agora é preciso definir claramente os caminhos suportados de acesso interno e remoto.

## Scope boundaries

**Included:** topologia suportada, critérios objetivos de publicação interna/externa, checks operacionais de validação.

**Excluded:** troubleshooting detalhado e mudanças de auth da aplicação.

## Tests to write FIRST (TDD)

- quando houver comportamento automatizado verificável sobre publicação/configuração;
- se o slice for majoritariamente documental, priorizar validações/runbook determinísticos.

## Success criteria

- existe topologia oficial clara para acesso interno e remoto;
- critérios de validação são objetivos.

## Mandatory report file

- Write the implementation report to: `/tmp/same-host-deployment-and-hardening-03-publication-topology-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: same-host-deployment-and-hardening
Task file: openspec/changes/same-host-deployment-and-hardening/tasks/03-publication-topology.md
Implement only this slice.
If behavior changes, use TDD; if mostly docs/automation contracts, keep validations deterministic.
Do not add troubleshooting sprawl beyond the topology definition.
Run gates, update checklist, commit, push, and stop.
Include SNP before/after where relevant.
In the report, list the exact commands executed for pytest, ruff, mypy, and markdownlint.
Do not use `uv run ruff check .`; run ruff only on changed Python paths.
If any Markdown files are changed, run markdownlint on those exact paths and report the command.
If any files under `docs/*.md` are changed, also run and report `uv run pytest tests/unit/test_readme_bilingual_baseline.py tests/unit/test_docs_bilingual_mirror.py -q`.
Write the full implementation report to `/tmp/same-host-deployment-and-hardening-03-publication-topology-report.md`.
In your final response, provide the exact report file path.
```

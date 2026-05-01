# Slice 3.1 - Final ops verification

## Goal

Atualizar runbooks/manuais e verificar o baseline operacional final do stack consolidado.

## Context

Runtime, deploy, topologia e hardening já foram tratados. Este slice fecha o change com verificação operacional integrada.

## Scope boundaries

**Included:** runbooks finais, checklists manuais, checklist OpenSpec, verificação integrada do baseline.

**Excluded:** novas features de produto.

## Tests to write FIRST (TDD)

- somente se houver lacuna real de comportamento verificável identificada no fechamento.

## Success criteria

- baseline operacional final está documentado e verificável;
- handoff para operação/infra está claro.

## Mandatory report file

- Write the implementation report to: `/tmp/same-host-deployment-and-hardening-05-final-ops-verification-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: same-host-deployment-and-hardening
Task file: openspec/changes/same-host-deployment-and-hardening/tasks/05-final-ops-verification.md
Implement only this slice.
Focus on verification and documentation sync.
Do not add new product behavior.
Run gates, update checklist, commit, push, and stop.
Report SNP before/after.
In the report, list the exact commands executed for pytest, ruff, mypy, and markdownlint.
Do not use `uv run ruff check .`; run ruff only on changed Python paths.
If any Markdown files are changed, run markdownlint on those exact paths and report the command.
If any files under `docs/*.md` are changed, also run and report `uv run pytest tests/unit/test_readme_bilingual_baseline.py tests/unit/test_docs_bilingual_mirror.py -q`.
Write the full implementation report to `/tmp/same-host-deployment-and-hardening-05-final-ops-verification-report.md`.
In your final response, provide the exact report file path.
```

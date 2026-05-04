# Slice 1.1 - Runtime composition update

## Goal

Atualizar a composição suportada de runtime para incluir a web app Django no mesmo host.

## Context

Os changes anteriores consolidaram a aplicação web. Agora a composição oficial de runtime precisa refletir o novo stack suportado.

## Scope boundaries

**Included:** entrypoints/composição suportada, documentação técnica de runtime, testes/verificações focadas de composição.

**Excluded:** hardening de publicação, troubleshooting operacional detalhado.

## Tests to write FIRST (TDD)

- composição suportada inclui o novo serviço web quando aplicável;
- startup path local e compose continuam coerentes.

## Success criteria

- runtime oficial do projeto descreve o stack consolidado;
- não há caminho suportado ambíguo entre velho e novo stack.

## Mandatory report file

- Write the implementation report to: `/tmp/same-host-deployment-and-hardening-01-runtime-composition-update-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: same-host-deployment-and-hardening
Task file: openspec/changes/same-host-deployment-and-hardening/tasks/01-runtime-composition-update.md
Implement only this slice.
Use TDD where executable behavior changes.
Do not begin publication hardening yet.
Run gates, update checklist, commit, push, and stop.
Include SNP before/after.
```

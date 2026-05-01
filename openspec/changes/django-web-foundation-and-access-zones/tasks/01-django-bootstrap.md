# Slice 1.1 - Django bootstrap

## Goal

Introduzir o projeto Django mínimo no repositório, com entrypoint executável e uma rota simples de smoke/health para validar boot sem tocar no fluxo clínico existente.

## Context

Este é o primeiro slice da fundação Django. O runtime FastAPI atual continua existindo; o objetivo aqui é apenas adicionar a nova aplicação web separada e verificável.

## Scope boundaries

**Included:** estrutura inicial Django, configuração mínima, URL/view de smoke, testes de boot.

**Excluded:** modelo de usuário custom, login, PWA, restrições de intranet, páginas por papel.

## Files to create or modify

- projeto/app Django novo no repositório
- arquivo de entrypoint/ASGI/WSGI necessário
- testes focados de bootstrap
- `openspec/changes/django-web-foundation-and-access-zones/tasks.md`

## Tests to write FIRST (TDD)

- app Django sobe com settings válidas no repositório;
- rota de smoke/health responde com sucesso;
- boot Django não depende do runtime FastAPI atual.

## Implementation steps

1. Escrever os testes de bootstrap e smoke route.
2. Confirmar falha inicial (RED).
3. Criar a estrutura mínima do projeto Django.
4. Implementar a rota/view mínima de smoke.
5. Fazer os testes passarem (GREEN).
6. Refatorar sem ampliar escopo.

## Success criteria

- existe um app Django executável no repositório;
- a rota de smoke responde com sucesso;
- nenhum comportamento clínico existente é alterado.

## Mandatory gates

- `uv run pytest <targeted-tests>`
- `uv run ruff check <changed-paths>`
- `uv run mypy <changed-paths-or-package>`
- `markdownlint-cli2 "openspec/changes/django-web-foundation-and-access-zones/**/*.md"`

## Mandatory report file

- Write the implementation report to: `/tmp/django-web-foundation-and-access-zones-01-django-bootstrap-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: django-web-foundation-and-access-zones
Task file: openspec/changes/django-web-foundation-and-access-zones/tasks/01-django-bootstrap.md
Implement only this slice.
Follow AGENTS.md strictly.
Use strict TDD (RED -> GREEN -> REFACTOR).
Do not introduce login, roles, PWA, or intranet logic yet.
Keep architecture boundaries clean and changes minimal.
Update the task checklist after implementation, run required gates, commit, push, and stop.
Produce a detailed implementation report with SNP before/after snippets.
```

## Mandatory implementation report

- gravar o relatório completo em `/tmp/django-web-foundation-and-access-zones-01-django-bootstrap-report.md`;
- incluir o caminho exato do arquivo na resposta final;
- resumo do slice;
- arquivos criados/alterados;
- testes escritos primeiro;
- evidência RED -> GREEN;
- comandos/gates executados;
- critérios de sucesso atendidos;
- SNP before/after.

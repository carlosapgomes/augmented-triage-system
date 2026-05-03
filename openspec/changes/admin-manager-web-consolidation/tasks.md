# Tasks

## Phase 1 - Dashboard consolidation

- [x] 1.1 Consolidar o dashboard operacional no Django para `manager` e `admin`.
  - Slice file: `openspec/changes/admin-manager-web-consolidation/tasks/01-django-dashboard-consolidation.md`
- [x] 1.2 Consolidar o detalhe de caso no Django com timeline auditável para `manager` e `admin`.
  - Slice file: `openspec/changes/admin-manager-web-consolidation/tasks/02-django-case-detail-consolidation.md`

## Phase 2 - Role-aware shell consolidation

- [ ] 2.1 Ajustar o shell final para separar claramente navegação de `manager` e `admin`.
  - Slice file: `openspec/changes/admin-manager-web-consolidation/tasks/03-manager-admin-shell-navigation.md`

## Phase 3 - Admin surfaces

- [ ] 3.1 Consolidar a superfície de gestão de usuários no Django para `admin`.
  - Slice file: `openspec/changes/admin-manager-web-consolidation/tasks/04-admin-user-management-consolidation.md`
- [ ] 3.2 Consolidar a superfície de gestão de prompts no Django para `admin`.
  - Slice file: `openspec/changes/admin-manager-web-consolidation/tasks/05-admin-prompt-management-consolidation.md`

## Phase 4 - Verification and cutover handoff

- [ ] 4.1 Atualizar auditoria, runbook manual, testes de autorização e handoff de cutover da superfície antiga.
  - Slice file: `openspec/changes/admin-manager-web-consolidation/tasks/06-verification-and-legacy-handoff.md`

## Execution rules for every slice

- Cada slice deve usar o `openspec-apply-change` skill.
- Ler antes de codar:
  1. `AGENTS.md`
  2. `PROJECT_CONTEXT.md`
  3. `openspec/changes/django-web-foundation-and-access-zones/tasks.md`
  4. `openspec/changes/web-triage-workflow-migration/tasks.md`
  5. este `tasks.md`
  6. o arquivo do slice atual
- Aplicar TDD estrito: RED -> GREEN -> REFACTOR.
- Manter `manager` estritamente read-only.
- Manter `admin` como único papel com mutação de usuários/prompts/sistema.
- Atualizar o checklist do change e parar após um slice.

## Mandatory implementation report delivery

- O executor do slice deve gravar o relatório final em um arquivo temporário em `/tmp/`.
- O caminho exato do arquivo temporário deve seguir o valor definido no arquivo do slice.
- A resposta final do executor deve incluir explicitamente o caminho do arquivo para que o usuário possa copiá-lo.

## Mandatory implementation report format for every slice

- resumo do slice;
- arquivos alterados/criados;
- testes adicionados/alterados;
- evidência RED -> GREEN;
- comandos executados e resultados;
- critérios de sucesso atendidos/não atendidos;
- riscos, desvios e pendências;
- SNP before/after.

## Mandatory gates for every slice

- `uv run pytest <targeted-tests>`
- `uv run ruff check <changed-paths>`
- `uv run mypy <changed-paths-or-package>`
- `markdownlint-cli2 "<changed-markdown-paths>"`

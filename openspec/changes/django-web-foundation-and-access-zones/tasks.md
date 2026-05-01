# Tasks

## Phase 1 - Django bootstrap

- [x] 1.1 Criar o projeto Django mínimo no repositório, com entrypoint executável, health/smoke route e testes iniciais de boot.
  - Slice file: `openspec/changes/django-web-foundation-and-access-zones/tasks/01-django-bootstrap.md`

## Phase 2 - Identity and role model

- [x] 2.1 Implementar modelo de usuário custom com contas individuais e papéis `nir`, `doctor`, `scheduler`, `manager`, `admin`.
  - Slice file: `openspec/changes/django-web-foundation-and-access-zones/tasks/02-custom-user-and-roles.md`
- [ ] 2.2 Implementar login/logout/sessão e redirecionamento pós-login específico por papel.
  - Slice file: `openspec/changes/django-web-foundation-and-access-zones/tasks/03-login-session-and-role-routing.md`

## Phase 3 - Access zones

- [ ] 3.1 Implementar resolução confiável do IP de origem atrás de proxy/túnel, com testes positivos e negativos.
  - Slice file: `openspec/changes/django-web-foundation-and-access-zones/tasks/04-client-ip-resolution.md`
- [ ] 3.2 Implementar restrição app-level para `nir` e `scheduler`, limitada à intranet, com auditoria de acesso negado.
  - Slice file: `openspec/changes/django-web-foundation-and-access-zones/tasks/05-intranet-role-restrictions.md`

## Phase 4 - PWA shell foundation

- [ ] 4.1 Implementar shell PWA Django online-only com metadata instalável e páginas iniciais mínimas por papel.
  - Slice file: `openspec/changes/django-web-foundation-and-access-zones/tasks/06-django-pwa-shell.md`

## Phase 5 - Verification and handoff

- [ ] 5.1 Executar verificação integrada da fundação Django, atualizar documentação afetada e preparar handoff para o change de migração do fluxo operacional.
  - Slice file: `openspec/changes/django-web-foundation-and-access-zones/tasks/07-foundation-verification-and-handoff.md`

## Execution rules for every slice

- Cada slice deve ser implementado por um LLM com contexto zero usando o `openspec-apply-change` skill.
- Ler antes de codar:
  1. `AGENTS.md`
  2. `PROJECT_CONTEXT.md`
  3. este `tasks.md`
  4. o arquivo do slice correspondente
- Aplicar TDD estrito: RED -> GREEN -> REFACTOR.
- Manter type hints e docstrings em todo código novo/alterado.
- Respeitar a direção arquitetural `adapters -> application -> domain -> infrastructure`.
- Parar ao final do slice, atualizar checklist e aguardar aprovação.

## Mandatory implementation report delivery

- O executor do slice deve gravar o relatório final em um arquivo temporário em `/tmp/`.
- O caminho exato do arquivo temporário deve seguir o valor definido no arquivo do slice.
- A resposta final do executor deve incluir explicitamente o caminho do arquivo para que o usuário possa copiá-lo.

## Mandatory implementation report format for every slice

O relatório entregue pelo executor do slice deve incluir:

- resumo objetivo do que foi implementado;
- arquivos alterados/criados;
- testes adicionados/alterados;
- comandos executados e resultado dos gates;
- critérios de sucesso atendidos/não atendidos;
- riscos, desvios ou pendências;
- SNP before/after com trechos relevantes do código alterado.

## Mandatory gates for every slice

- `uv run pytest <targeted-tests>`
- `uv run ruff check <changed-paths>`
- `uv run mypy <changed-paths-or-package>`
- `markdownlint-cli2 "<changed-markdown-paths>"`

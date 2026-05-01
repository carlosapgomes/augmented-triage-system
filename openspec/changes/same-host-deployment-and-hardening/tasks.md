# Tasks

## Phase 1 - Runtime and deploy composition

- [x] 1.1 Atualizar a composição suportada de runtime para incluir a web app Django no mesmo host.
  - Slice file: `openspec/changes/same-host-deployment-and-hardening/tasks/01-runtime-composition-update.md`
- [ ] 1.2 Ajustar a automação Ansible/rootless para o stack consolidado.
  - Slice file: `openspec/changes/same-host-deployment-and-hardening/tasks/02-ansible-stack-consolidation.md`

## Phase 2 - Publication topology and zone hardening

- [ ] 2.1 Documentar e validar a topologia interna vs externa no mesmo host.
  - Slice file: `openspec/changes/same-host-deployment-and-hardening/tasks/03-publication-topology.md`
- [ ] 2.2 Adicionar hardening operacional, checklist de zona por papel e troubleshooting.
  - Slice file: `openspec/changes/same-host-deployment-and-hardening/tasks/04-zone-hardening-and-troubleshooting.md`

## Phase 3 - Final verification

- [ ] 3.1 Atualizar runbooks/manuais e verificar o baseline operacional final.
  - Slice file: `openspec/changes/same-host-deployment-and-hardening/tasks/05-final-ops-verification.md`

## Execution rules for every slice

- Cada slice deve usar o `openspec-apply-change` skill.
- Ler antes de codar:
  1. `AGENTS.md`
  2. `PROJECT_CONTEXT.md`
  3. os changes anteriores de fundação/migração/consolidação quando relevantes
  4. este `tasks.md`
  5. o arquivo do slice atual
- Aplicar TDD sempre que houver comportamento automatizado verificável.
- Não redesenhar regras clínicas nem auth da aplicação.
- Atualizar checklist e parar após um slice.

## Mandatory implementation report delivery

- O executor do slice deve gravar o relatório final em um arquivo temporário em `/tmp/`.
- O caminho exato do arquivo temporário deve seguir o valor definido no arquivo do slice.
- A resposta final do executor deve incluir explicitamente o caminho do arquivo para que o usuário possa copiá-lo.

## Mandatory implementation report format for every slice

- resumo do slice;
- arquivos alterados/criados;
- testes adicionados/alterados;
- evidência RED -> GREEN quando aplicável;
- comandos executados e resultados;
- critérios de sucesso atendidos/não atendidos;
- riscos, desvios e pendências;
- SNP before/after.

## Mandatory gates for every slice

- `uv run pytest <targeted-tests>`
- `uv run ruff check <changed-paths>`
- `uv run mypy <changed-paths-or-package>`
- `markdownlint-cli2 "<changed-markdown-paths>"`

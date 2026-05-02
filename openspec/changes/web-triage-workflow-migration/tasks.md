# Tasks

## Phase 1 - Shared workflow projections

- [x] 1.1 Preparar projeções/queries compartilhadas para filas web, cards de caso e detalhes operacionais por papel, fixando cedo o contrato mínimo dos eventos humanos web na timeline.
  - Slice file: `openspec/changes/web-triage-workflow-migration/tasks/01-shared-workflow-projections.md`

## Phase 2 - NIR intake and tracking

- [x] 2.1 Implementar upload PDF NIR e criação do caso via web com auditoria individual.
  - Slice file: `openspec/changes/web-triage-workflow-migration/tasks/02-nir-upload-and-case-creation.md`
- [x] 2.2 Implementar dashboard NIR e detalhe inicial do caso com progresso operacional.
  - Slice file: `openspec/changes/web-triage-workflow-migration/tasks/03-nir-dashboard-and-case-detail.md`

## Phase 3 - Doctor workflow

- [x] 3.1 Implementar fila médica web baseada em casos aguardando decisão.
  - Slice file: `openspec/changes/web-triage-workflow-migration/tasks/04-doctor-queue.md`
- [x] 3.2 Implementar formulário de decisão médica web reutilizando a semântica clínica existente.
  - Slice file: `openspec/changes/web-triage-workflow-migration/tasks/05-doctor-decision-form.md`

## Phase 4 - Scheduler workflow

- [x] 4.1 Implementar fila do agendador web baseada em casos aguardando confirmação.
  - Slice file: `openspec/changes/web-triage-workflow-migration/tasks/06-scheduler-queue.md`
- [ ] 4.2 Implementar formulário web de confirmação/negação do agendamento.
  - Slice file: `openspec/changes/web-triage-workflow-migration/tasks/07-scheduler-confirmation-form.md`

## Phase 5 - Final NIR acknowledgment and visibility

- [ ] 5.1 Implementar visualização do resultado final no NIR e confirmação explícita de recebimento/fechamento, com migração formal do checkpoint humano canônico de Matrix para web.
  - Slice file: `openspec/changes/web-triage-workflow-migration/tasks/08-nir-final-acknowledgment.md`
- [ ] 5.2 Atualizar timeline/dashboard/runbook manual para refletir ações web humanas no fluxo completo.
  - Slice file: `openspec/changes/web-triage-workflow-migration/tasks/09-web-workflow-audit-visibility.md`

## Execution rules for every slice

- Cada slice deve usar o `openspec-apply-change` skill.
- Ler antes de codar:
  1. `AGENTS.md`
  2. `PROJECT_CONTEXT.md`
  3. `openspec/changes/django-web-foundation-and-access-zones/tasks.md` quando precisar de contexto da fundação
  4. este `tasks.md`
  5. o arquivo do slice atual
- Aplicar TDD estrito: RED -> GREEN -> REFACTOR.
- Reutilizar serviços centrais do workflow sempre que possível; não redesenhar a máquina de estados.
- Tratar este change como hard refactor: não assumir compatibilidade legada nem operação paralela do fluxo antigo.
- Atualizar checklist do change ao final do slice.
- Parar após um slice concluído e aguardar aprovação.

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
- SNP before/after com trechos relevantes.

## Mandatory gates for every slice

- `uv run pytest <targeted-tests>`
- `uv run ruff check <changed-paths>`
- `uv run mypy <changed-paths-or-package>`
- `markdownlint-cli2 "<changed-markdown-paths>"`

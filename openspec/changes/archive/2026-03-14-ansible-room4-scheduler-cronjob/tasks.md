# Tasks

## 1. Variáveis e contratos de configuração do cron da Room-4

- [x] 1.1 Adicionar testes unitários de Ansible para exigir novas variáveis de configuração do scheduler cron (enabled, timezone, schedule, log target).
- [x] 1.2 Atualizar `ansible/inventory/group_vars/all.yml` (e defaults aplicáveis) com namespace de configuração do cron da Room-4 e defaults operacionais equivalentes a 07:00/19:00 `America/Bahia` (host UTC: 10:00/22:00).
- [x] 1.3 Definir validações de pré-condição para impedir cron habilitado sem variáveis obrigatórias de resumo (`ROOM4_ID`, `SUPERVISOR_SUMMARY_*`).

## 2. Role de agendamento cron no contexto rootless

- [x] 2.1 Criar testes para a nova role/tarefas de cron garantindo uso do `ats_service_user` e idempotência.
- [x] 2.2 Implementar role para gerenciar entradas de ambiente no crontab (`XDG_RUNTIME_DIR`, `DOCKER_HOST`, `CRON_TZ`) no usuário de serviço.
- [x] 2.3 Implementar entrada de job cron que execute `docker compose ... run --rm --no-deps worker uv run python -m apps.scheduler.main` com redirecionamento de log configurável.
- [x] 2.4 Implementar comportamento de remoção do cron quando `enabled=false`, sem deixar entradas órfãs.

## 3. Wiring nos playbooks oficiais

- [x] 3.1 Adicionar cobertura de testes para wiring da nova role nos playbooks (`deploy.yml`, `upgrade.yml` e decisão explícita para `rollback.yml`).
- [x] 3.2 Integrar execução da role de cron no fluxo de deploy/upgrade após renderização de runtime.
- [x] 3.3 Garantir convergência de estado do cron em reruns idempotentes dos playbooks.

## 4. Documentação operacional e espelhos bilíngues

- [x] 4.1 Atualizar `docs/ansible_ops_runbook.md` com seção de cron gerenciado para Room-4 (modelo operacional, validação e troubleshooting).
- [x] 4.2 Sincronizar `docs/en/ansible_ops_runbook.md` mantendo equivalência funcional da documentação.
- [x] 4.3 Registrar no runbook os comandos de verificação pós-deploy (crontab do usuário, logs do scheduler e evidência de enfileiramento `post_room4_summary`).

## 5. Verificação e fechamento do change

- [x] 5.1 Executar testes-alvo de Ansible e runtime relacionados ao novo cron gerenciado.
- [x] 5.2 Executar `uv run ruff check` e `uv run mypy` nos paths alterados.
- [x] 5.3 Executar `markdownlint-cli2` nos artefatos OpenSpec e docs alterados.
- [x] 5.4 Atualizar este `tasks.md` com evidências de verificação, observações de rollout e estratégia de rollback operacional.

## Evidências de verificação e observações de rollout/rollback

### Evidências de verificação

- Testes-alvo (Ansible + runtime relacionado ao scheduler one-shot):
  - `uv run pytest tests/unit/test_ansible_variables.py tests/unit/test_ansible_app_runtime_role.py tests/unit/test_ansible_room4_scheduler_cron_role.py tests/unit/test_ansible_deploy_role.py tests/unit/test_ansible_upgrade_playbook.py tests/unit/test_ansible_rollback_playbook.py tests/unit/test_ansible_ops_runbook_docs.py tests/unit/test_readme_bilingual_baseline.py tests/unit/test_docs_bilingual_mirror.py tests/unit/test_supervisor_summary_scheduler_main.py tests/integration/test_supervisor_summary_scheduler_runtime.py -q` → `27 passed`
  - Ajuste de baseline UTC do cron + sincronização de docs: `uv run pytest tests/unit/test_ansible_variables.py tests/unit/test_ansible_ops_runbook_docs.py tests/unit/test_ansible_room4_scheduler_cron_role.py tests/unit/test_ansible_*.py tests/unit/test_readme_bilingual_baseline.py tests/unit/test_docs_bilingual_mirror.py -q` → `34 passed`
- Lint e tipagem Python (paths alterados):
  - `uv run ruff check tests/unit/test_ansible_variables.py tests/unit/test_ansible_app_runtime_role.py tests/unit/test_ansible_room4_scheduler_cron_role.py tests/unit/test_ansible_deploy_role.py tests/unit/test_ansible_upgrade_playbook.py tests/unit/test_ansible_rollback_playbook.py tests/unit/test_ansible_ops_runbook_docs.py` → sem erros
  - `uv run mypy tests/unit/test_ansible_variables.py tests/unit/test_ansible_app_runtime_role.py tests/unit/test_ansible_room4_scheduler_cron_role.py tests/unit/test_ansible_deploy_role.py tests/unit/test_ansible_upgrade_playbook.py tests/unit/test_ansible_rollback_playbook.py tests/unit/test_ansible_ops_runbook_docs.py` → sem erros
- Markdown lint (OpenSpec + docs):
  - `markdownlint-cli2 "docs/ansible_ops_runbook.md" "docs/en/ansible_ops_runbook.md" "openspec/changes/ansible-room4-scheduler-cronjob/**/*.md"` → sem erros
- Validação do change:
  - `openspec validate ansible-room4-scheduler-cronjob` → válido

### Observações de rollout

- O cron da Room-4 é convergido por Ansible em `deploy`, `upgrade` e `rollback` via role `room4_scheduler_cron`.
- Execução ocorre no usuário de serviço (`ats_service_user`) com ambiente rootless explícito no crontab (`CRON_TZ`, `XDG_RUNTIME_DIR`, `DOCKER_HOST`).
- Defaults operacionais aplicados (baseline host UTC):
  - `ats_room4_scheduler_cron_enabled: true`
  - `ats_room4_scheduler_cron_timezone: UTC`
  - `ats_room4_scheduler_cron_minute: "0"`
  - `ats_room4_scheduler_cron_hour: "10,22"` (equivalente a 07:00/19:00 `America/Bahia`)
  - `ats_room4_scheduler_cron_log_file: {{ ats_runtime_root }}/logs/room4-scheduler-cron.log`
- Verificação pós-deploy recomendada no runbook:
  - conferir `crontab -u ats -l`
  - checar arquivo de log do scheduler
  - confirmar enfileiramento de `post_room4_summary`

### Estratégia de rollback operacional

- Rollback de versão de aplicação mantém convergência do cron (playbook `rollback.yml` também aplica a role).
- Para interromper agendamentos periódicos sem remover restante do runtime:
  - definir `ats_room4_scheduler_cron_enabled: false` no inventário do host
  - reaplicar `deploy.yml`, `upgrade.yml` ou `rollback.yml`
- A remoção do cron é idempotente e não remove serviços principais (`bot-api`, `bot-matrix`, `worker`).

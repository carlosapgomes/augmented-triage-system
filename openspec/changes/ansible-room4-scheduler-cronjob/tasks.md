# Tasks

## 1. Variáveis e contratos de configuração do cron da Room-4

- [x] 1.1 Adicionar testes unitários de Ansible para exigir novas variáveis de configuração do scheduler cron (enabled, timezone, schedule, log target).
- [x] 1.2 Atualizar `ansible/inventory/group_vars/all.yml` (e defaults aplicáveis) com namespace de configuração do cron da Room-4 e defaults operacionais (07:00/19:00, `America/Bahia`).
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

- [ ] 4.1 Atualizar `docs/ansible_ops_runbook.md` com seção de cron gerenciado para Room-4 (modelo operacional, validação e troubleshooting).
- [ ] 4.2 Sincronizar `docs/en/ansible_ops_runbook.md` mantendo equivalência funcional da documentação.
- [ ] 4.3 Registrar no runbook os comandos de verificação pós-deploy (crontab do usuário, logs do scheduler e evidência de enfileiramento `post_room4_summary`).

## 5. Verificação e fechamento do change

- [ ] 5.1 Executar testes-alvo de Ansible e runtime relacionados ao novo cron gerenciado.
- [ ] 5.2 Executar `uv run ruff check` e `uv run mypy` nos paths alterados.
- [ ] 5.3 Executar `markdownlint-cli2` nos artefatos OpenSpec e docs alterados.
- [ ] 5.4 Atualizar este `tasks.md` com evidências de verificação, observações de rollout e estratégia de rollback operacional.

# Proposal

## Why

Hoje o envio periódico de resumo da Room-4 depende de configuração manual de cron no host, o que aumenta risco de drift entre ambientes e de falha operacional silenciosa após instalação/upgrade. A automação de deploy já é o caminho oficial de operação, então o agendamento do scheduler também deve ser provisionado e mantido pelo Ansible, no mesmo usuário de runtime (`ats`).

## What Changes

- Estender a automação Ansible para configurar e manter o cron de execução do scheduler one-shot da Room-4.
- Garantir que o agendamento rode no usuário de serviço de instalação (`ats_service_user`), alinhado ao runtime rootless já adotado.
- Padronizar execução do scheduler dentro do container da aplicação (imagem já implantada), usando comando canônico `uv run python -m apps.scheduler.main`.
- Incluir no provisionamento as variáveis de ambiente necessárias para execução do comando Docker rootless no contexto de cron do usuário.
- Tornar o agendamento configurável por variáveis de inventário (habilitar/desabilitar, timezone, horários, caminho de log), mantendo defaults operacionais de 07:00 e 19:00 em `America/Bahia`.
- Adicionar cobertura de testes para os novos artefatos Ansible e para validação da configuração de agendamento.
- Atualizar runbook operacional com passos de verificação e troubleshooting do cron gerenciado pelo Ansible.

## Capabilities

### New Capabilities

- `ansible-room4-summary-scheduler-cron`: Provisionamento idempotente de agendamento periódico do scheduler da Room-4 via Ansible, executando no usuário de serviço e acionando o aplicativo dentro do container.

### Modified Capabilities

- `ansible-rootless-runtime-deploy`: passa a incluir, além do deploy dos serviços, a garantia de configuração do agendamento operacional do resumo periódico da Room-4 no contexto rootless.
- `ops-runbook-automation`: passa a documentar validação e suporte de primeiro nível para o cronjob gerenciado por Ansible.

## Impact

- Código afetado (provável):
  - `ansible/inventory/group_vars/all.yml` (novas variáveis de scheduler/cron)
  - nova role/tarefas em `ansible/roles/` para gerenciamento de cron do scheduler
  - `ansible/playbooks/deploy.yml` e possivelmente `upgrade.yml`/`rollback.yml` (wiring da role)
  - testes unitários de Ansible em `tests/unit/test_ansible_*.py`
  - documentação operacional em `docs/ansible_ops_runbook.md` e espelho `docs/en/ansible_ops_runbook.md`
- Operação: elimina passo manual pós-deploy para criação de cron do resumo da Room-4.
- Segurança/execução: mantém princípio de menor privilégio ao executar agendamento no usuário dedicado do runtime rootless.
- Risco funcional: baixo a moderado, concentrado em composição correta do comando Docker rootless em contexto não interativo (cron).

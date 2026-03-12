# Proposal

## Why

O resumo periódico da Room-4 hoje foi desenhado para dois cortes fixos (07:00 e 19:00) com janela fixa de 12 horas. A operação do CHD precisa de três execuções diárias (07:00, 13:00 e 19:00), com janelas variáveis entre cortes consecutivos no timezone configurado, o que não é atendido pelo modelo atual.

## What Changes

- Evoluir o agendamento do resumo da Room-4 de um modelo de dois horários fixos para um modelo global configurável por lista de cortes diários.
- Introduzir configuração canônica de cortes em horas locais (ex.: `7,13,19`) e calcular a janela sempre como **corte anterior -> corte atual** no timezone definido por `SUPERVISOR_SUMMARY_TIMEZONE`.
- Definir novo padrão global de operação em três cortes por dia: `07:00`, `13:00`, `19:00`.
- Manter execução **sem catch-up automático**: cada execução enfileira apenas a janela imediatamente anterior; janelas perdidas por falha não são retroprocessadas automaticamente.
- Reforçar observabilidade do scheduler com logs explícitos da janela resolvida (`window_start`, `window_end`, timezone, cutoff aplicado) e indicação clara do modo sem catch-up.
- Atualizar defaults operacionais de cron (Ansible) para refletir o novo padrão global no baseline UTC.
- Atualizar documentação operacional e cobertura de testes para o novo contrato de configuração e cálculo de janela.

## Capabilities

### New Capabilities

- `room4-supervisor-configurable-cutoff-scheduling`: Permite calcular e enfileirar resumos periódicos da Room-4 a partir de uma lista configurável de cortes diários, com janelas variáveis entre cortes consecutivos e sem catch-up automático.

### Modified Capabilities

- `ansible-rootless-runtime-deploy`: Atualiza o padrão global de agendamento e validações de configuração de runtime para o modelo de três cortes diários.
- `ops-runbook-automation`: Atualiza runbook com novo padrão de horários, validações operacionais e comportamento explícito sem catch-up.

## Impact

- Código afetado (provável):
  - `src/triage_automation/application/services/supervisor_summary_scheduler_service.py` (resolução de janelas por lista de cortes)
  - `src/triage_automation/config/settings.py` (novo contrato de configuração de cutoffs)
  - `apps/scheduler/main.py` (wiring/telemetria do scheduler)
  - `ansible/inventory/group_vars/all.yml`
  - `ansible/roles/room4_scheduler_cron/defaults/main.yml`
  - `ansible/roles/app_runtime/tasks/main.yml`
  - `.env.example`
  - `docs/runtime-smoke.md` e `docs/en/runtime-smoke.md`
  - `docs/ansible_ops_runbook.md` e `docs/en/ansible_ops_runbook.md`
  - testes unitários/integrados de scheduler, settings e Ansible
- Banco de dados: sem mudanças estruturais previstas.
- Operação: passa a exigir convergência global para três execuções diárias e novo padrão de configuração de cortes.
- Risco funcional: moderado, concentrado em cálculo de janela por timezone/cutoff, compatibilidade de configuração e alinhamento entre cron e scheduler.

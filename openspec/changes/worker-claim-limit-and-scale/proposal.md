# Proposal: worker-claim-limit-and-scale

## Why

Quando múltiplos PDFs são enviados quase ao mesmo tempo na Sala 1, o worker único pode reservar vários jobs pesados (`process_pdf_case`) e processá-los de forma sequencial. Isso aumenta a latência percebida para publicações na Sala 2 e causa sensação operacional de travamento.

## What Changes

- Tornar o limite de claim do worker configurável por variável de ambiente.
- Ajustar baseline de runtime para usar `WORKER_CLAIM_LIMIT=1`, reduzindo prefetch por instância.
- Escalar a execução de workers para 3 réplicas no deploy rootless com Docker Compose.
- Preservar encadeamento de mensagens por caso na Sala 2 e sem alterar semântica clínica.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `worker-live-handler-wiring`: adicionar requisito de claim-limit configurável no runtime do worker.
- `ansible-rootless-runtime-deploy`: adicionar requisito de escala explícita de réplicas do worker no comando de deploy.

## Impact

- Código afetado:
  - `src/triage_automation/config/settings.py`
  - `apps/worker/main.py`
  - `.env.example`
  - `ansible/inventory/group_vars/all.yml`
  - `ansible/roles/deploy/defaults/main.yml`
  - `ansible/roles/deploy/tasks/main.yml`
  - testes unitários de settings e deploy ansible
- Sem mudanças de schema de banco.
- Sem mudança de contrato clínico/estados de caso.

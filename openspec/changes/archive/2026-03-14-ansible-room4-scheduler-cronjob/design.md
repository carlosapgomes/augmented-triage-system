# Ansible Room-4 Scheduler Cronjob Design

## Context

O runtime já segue padrão de deploy rootless via Ansible, com serviços `bot-api`, `bot-matrix` e `worker` executando sob usuário dedicado (`ats_service_user`). O resumo periódico da Room-4 já existe no código de aplicação como scheduler *one-shot* (`python -m apps.scheduler.main`), mas o agendamento em produção ainda depende de ação manual no host.

Isso cria risco operacional: ambientes diferentes podem esquecer o cron, ter horários divergentes, ou perder o agendamento após manutenção. O objetivo é mover essa responsabilidade para a automação oficial de deploy, mantendo o scheduler fora do processo principal (conforme arquitetura já definida: scheduler externo/orquestrador).

Restrições principais:

- manter execução sem privilégios de root para rotina de aplicação;
- preservar o modelo atual (`cron` no host chama comando one-shot);
- manter compatibilidade com Docker rootless (ambiente de cron é não interativo);
- não alterar semântica de geração/publicação do resumo (somente automação operacional).

Stakeholders:

- operação/TI hospitalar (instalação e manutenção);
- engenharia (idempotência e confiabilidade do deploy);
- supervisão clínica (garantia de envio periódico no horário).

## Goals / Non-Goals

**Goals:**

- Provisionar cronjob da Room-4 via Ansible de forma idempotente.
- Executar o cron no usuário de instalação (`ats_service_user`).
- Disparar o scheduler de dentro do container da aplicação com comando canônico `uv run python -m apps.scheduler.main`.
- Suportar configuração por inventário para habilitar/desabilitar, timezone, horários e log.
- Garantir que o contexto rootless Docker funcione em cron (variáveis de ambiente necessárias).
- Documentar validação operacional e troubleshooting no runbook.

**Non-Goals:**

- Não mover scheduler para dentro do `worker` ou `bot-api` como loop interno.
- Não adicionar novo serviço long-running dedicado ao scheduler no `docker-compose`.
- Não alterar regras de janela, métricas ou idempotência da Room-4 já implementadas no domínio/aplicação.
- Não substituir `cron` por outro orquestrador nesta mudança.

## Decisions

### Decision 1: Usar cron de sistema (usuário de serviço) como mecanismo oficial de agendamento

- Escolha: gerenciar entrada de cron via Ansible no `crontab` do `ats_service_user`.
- Racional: menor superfície de mudança, aderente ao design atual de scheduler externo, e sem exigir daemon adicional.
- Alternativas consideradas:
  - `systemd --user timer`;
  - container com cron embutido.
- Motivo da rejeição:
  - timer adiciona outra superfície operacional fora do padrão atual do time;
  - cron embutido em container conflita com princípio de um processo principal por container e complica observabilidade.

### Decision 2: Executar scheduler via `docker compose run --rm --no-deps worker ...`

- Escolha: cron invoca container one-shot usando o serviço `worker` como base de imagem/env.
- Comando canônico (forma lógica):
  - `docker compose --project-name <project> --file <compose> run --rm --no-deps worker uv run python -m apps.scheduler.main`
- Racional: mantém execução isolada e independente de `exec` em container já ativo, reutiliza ambiente da aplicação sem criar novo serviço.
- Alternativas consideradas:
  - `docker compose exec -T worker ...`;
  - `docker run` direto com parâmetros manuais.
- Motivo da rejeição:
  - `exec` depende do container `worker` em execução e aumenta acoplamento ao estado do serviço;
  - `docker run` direto replica config de rede/env e aumenta risco de drift.

### Decision 3: Injetar variáveis rootless Docker no próprio cron gerenciado

- Escolha: escrever entradas de ambiente no crontab (ex.: `XDG_RUNTIME_DIR`, `DOCKER_HOST`, `CRON_TZ`) antes do job.
- Racional: cron roda sem shell de login e não herda ambiente rootless automaticamente.
- Alternativas consideradas:
  - wrapper script sourcing profile;
  - confiar em defaults do host.
- Motivo da rejeição:
  - wrapper script adiciona artefato extra e pontos de falha;
  - defaults variam entre distribuições/usuários e quebram determinismo.

### Decision 4: Introduzir variáveis Ansible dedicadas para scheduler cron

- Escolha: adicionar bloco configurável no inventário/defaults com:
  - flag de habilitação,
  - timezone,
  - expressão de horário,
  - arquivo de log,
  - política de remoção quando desabilitado.
- Racional: facilita operação por ambiente sem editar tasks.
- Alternativas consideradas:
  - hardcode dos horários no role;
  - variáveis espalhadas sem namespace.
- Motivo da rejeição:
  - hardcode reduz flexibilidade e manutenção;
  - variáveis dispersas dificultam governança operacional.

### Decision 5: Validar pré-condições de ambiente de resumo no fluxo Ansible

- Escolha: quando cron estiver habilitado, exigir presença de `ROOM4_ID` e parâmetros `SUPERVISOR_SUMMARY_*` no conjunto de env renderizado.
- Racional: evita cron ativo com scheduler falhando por configuração incompleta.
- Alternativas consideradas:
  - deixar falhar apenas em runtime/log.
- Motivo da rejeição:
  - detecção tardia aumenta MTTR e risco de perda de envio.

## Risks / Trade-offs

- [Risk] Cron executa sem conseguir conectar no daemon rootless Docker.
  - Mitigação: declarar `XDG_RUNTIME_DIR` e `DOCKER_HOST` explicitamente no crontab gerenciado e validar no runbook.
- [Risk] Sobreposição de execução caso uma rodada demore além da próxima janela.
  - Mitigação: manter scheduler one-shot curto; idempotência por janela no banco impede postagem duplicada.
- [Risk] Acúmulo de logs em arquivo local.
  - Mitigação: log path configurável e orientação de rotação no runbook.
- [Trade-off] `docker compose run` cria container efêmero a cada execução.
  - Mitigação: frequência baixa (2x/dia) com custo operacional aceitável.
- [Trade-off] Mantemos dependência de cron do host em vez de timer moderno.
  - Mitigação: simplicidade e aderência ao padrão operacional atual.

## Migration Plan

1. Adicionar variáveis de configuração do cron da Room-4 em `group_vars/defaults`.
2. Criar role/tarefas Ansible para:
   - registrar variáveis de ambiente no crontab do usuário de serviço;
   - criar/remover job de scheduler conforme `enabled`.
3. Integrar role no fluxo oficial (`deploy` e `upgrade`; opcionalmente `rollback` para manter estado desejado).
4. Atualizar testes unitários de Ansible para garantir presença e wiring do novo comportamento.
5. Atualizar runbook operacional (PT/EN) com verificação do cron e troubleshooting básico.
6. Rollout: executar `deploy.yml`/`upgrade.yml` e confirmar crontab + logs + enfileiramento.
7. Rollback operacional: desabilitar flag de cron no inventário e reaplicar playbook para remover job.

## Open Questions

- O cron deve ser aplicado também no playbook de `rollback.yml` (estado convergente completo) ou apenas em `deploy/upgrade`?
- O caminho de log padrão deve ficar sob `{{ ats_runtime_root }}` ou sob `/var/log` com política externa de rotação?
- O default de habilitação do cron deve ser `true` (opinião forte) ou `false` (ativação explícita por ambiente)?

# Room-4 Summary Configurable Cutoff Hours Design

## Context

O scheduler da Room-4 foi implementado com dois parâmetros fixos (`morning_hour` e `evening_hour`) e cálculo de janela fixa de 12h. Esse desenho atende 07:00/19:00, mas não atende o novo requisito operacional de três cortes diários (07:00, 13:00, 19:00) com janelas variáveis entre cortes consecutivos.

Restrições e direcionadores para esta mudança:

- Preservar arquitetura atual (`adapters -> application -> domain -> infrastructure`).
- Não alterar semântica de idempotência por janela (`room_id + window_start + window_end`).
- Não introduzir catch-up automático nesta fase.
- Manter timezone orientado por configuração (`SUPERVISOR_SUMMARY_TIMEZONE`).
- Convergir padrão global de operação para três execuções diárias.

Stakeholders principais: supervisão CHD (consumidora dos resumos), operações (Ansible/cron) e desenvolvimento (manutenção do scheduler/worker).

## Goals / Non-Goals

**Goals:**

- Suportar lista configurável de cortes diários para o scheduler da Room-4.
- Calcular a janela como `corte anterior -> corte atual` no timezone configurado.
- Definir padrão global `7,13,19`.
- Manter execução one-shot sem catch-up automático.
- Melhorar observabilidade do scheduler com logs explícitos da janela resolvida e do modo sem catch-up.
- Atualizar defaults de runtime/Ansible/docs/testes para o novo contrato.

**Non-Goals:**

- Não implementar retroprocessamento automático de janelas perdidas.
- Não alterar modelo de métricas do resumo ou formato da mensagem da Room-4.
- Não alterar schema de banco ou estratégia de deduplicação existente.
- Não redesenhar worker, fila, retry/backoff ou fluxo clínico principal.

## Decisions

### Decision 1: Representar cortes por lista canônica configurável

- Escolha: introduzir configuração única de cortes (`SUPERVISOR_SUMMARY_CUTOFF_HOURS`) em formato CSV de horas locais (ex.: `7,13,19`).
- Racional: remove acoplamento do modelo binário manhã/noite e permite expansão futura sem novo redesign.
- Alternativas consideradas:
  - manter `MORNING_HOUR`/`EVENING_HOUR` e adicionar `MIDDAY_HOUR`.
  - manter horários hardcoded no serviço.
- Motivo da rejeição:
  - `MIDDAY_HOUR` mantém desenho rígido e não escala para novas necessidades.
  - hardcode aumenta custo de manutenção e reduz governança operacional.

### Decision 2: Janela resolvida pelo corte imediatamente anterior

- Escolha: para cada execução, resolver `window_end` como o último cutoff `<= run_at_local` e `window_start` como cutoff imediatamente anterior na sequência circular de dias.
- Racional: atende janelas variáveis (12h/6h/6h no padrão 7,13,19) sem lógica adicional de catch-up.
- Alternativas consideradas:
  - manter subtração fixa de 12h.
  - inferir janela com base no horário do cron sem consultar sequência de cutoffs.
- Motivo da rejeição:
  - 12h fixa não atende 13:00/19:00.
  - inferência via cron acopla scheduler a detalhes de operação e reduz robustez.

### Decision 3: Política explícita de não catch-up

- Escolha: manter comportamento one-shot atual: uma execução processa somente a janela imediatamente anterior; falhas são registradas em log, sem enfileiramento retroativo automático.
- Racional: evita aumento relevante de complexidade (detecção de lacunas, ordenação de backlog, limites de replay, concorrência adicional).
- Alternativas consideradas:
  - catch-up automático completo de janelas faltantes.
  - catch-up limitado (ex.: apenas última janela perdida).
- Motivo da rejeição:
  - ambas introduzem ambiguidade operacional e aumento de superfície de falha nesta etapa.

### Decision 4: Observabilidade reforçada no scheduler

- Escolha: registrar em logs, a cada execução, cutoff aplicado, janela local/UTC e marcador explícito `catch_up=false`.
- Racional: permite auditoria operacional clara quando houver falha de cron/infra e explica por que não houve retroprocessamento.
- Alternativa considerada: manter logs atuais mínimos.
- Motivo da rejeição: diagnóstico operacional fica insuficiente para troubleshooting de janelas não processadas.

### Decision 5: Convergência global de defaults operacionais

- Escolha: atualizar padrão global para `7,13,19` em env/docs e para cron UTC equivalente (`10,16,22`) no baseline atual.
- Racional: garante alinhamento entre configuração de aplicação e execução operacional padrão.
- Alternativas consideradas:
  - alterar apenas código de aplicação sem mexer em defaults de operação.
  - alterar apenas cron sem alterar contrato de configuração da aplicação.
- Motivo da rejeição:
  - qualquer alteração parcial cria risco de drift entre comportamento esperado e real.

## Risks / Trade-offs

- [Risk] Configuração inválida de cutoffs (CSV malformado, duplicado, fora de faixa).
  - Mitigação: validação estrita em `Settings` (faixa 0-23, deduplicação/sort, mínimo de dois cutoffs, erro explícito).

- [Risk] Drift entre horário de cron e timezone de aplicação.
  - Mitigação: documentação operacional explícita com mapeamento UTC/Bahia e checklist pós-deploy.

- [Risk] Execução fora dos minutos exatos do cutoff (delay de cron).
  - Mitigação: resolver sempre o último cutoff `<= run_at_local`, preservando determinismo da janela.

- [Trade-off] Sem catch-up automático, falhas geram lacunas de cobertura até próxima intervenção.
  - Mitigação: logs explícitos + runbook com procedimento de reexecução manual controlada.

## Migration Plan

1. Adicionar novo contrato de configuração de cutoffs na aplicação (`SUPERVISOR_SUMMARY_CUTOFF_HOURS`) e resolver janela por sequência de cutoffs.
2. Atualizar wiring do scheduler (`apps/scheduler/main.py`) para usar lista de cutoffs e emitir logs detalhados.
3. Atualizar defaults globais:
   - `.env.example` para `7,13,19`.
   - Ansible runtime env obrigatório para novo campo.
   - Ansible cron default para `10,16,22` em UTC.
4. Atualizar testes unitários/integrados:
   - resolução de janela para 07:00, 13:00 e 19:00;
   - validação de settings;
   - defaults/roles/runbooks Ansible.
5. Atualizar documentação operacional PT/EN (`runtime-smoke`, `ansible_ops_runbook`) com novo padrão e política sem catch-up.
6. Rollout:
   - aplicar deploy/upgrade com novas variáveis;
   - validar crontab, logs de scheduler e enfileiramento `post_room4_summary`.
7. Rollback:
   - reverter para versão anterior e defaults anteriores (07:00/19:00), sem migração de banco.

## Open Questions

- Não há bloqueios técnicos abertos para este artefato.
- Decisão já consolidada no change: migração imediata para `SUPERVISOR_SUMMARY_CUTOFF_HOURS`, sem compatibilidade transitória com os campos legados.

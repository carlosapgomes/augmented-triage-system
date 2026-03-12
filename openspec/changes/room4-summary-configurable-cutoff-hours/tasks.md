# Tasks

## 1. Contrato de configuração de cutoffs no runtime

- [x] 1.1 Adicionar testes unitários (red) para `Settings` cobrindo `SUPERVISOR_SUMMARY_CUTOFF_HOURS` com: normalização/sort (`19,7,13` -> `[7,13,19]`), rejeição de duplicados e rejeição de valores fora de `0..23`.
- [x] 1.2 Implementar migração imediata para contrato único de cutoffs em `src/triage_automation/config/settings.py`, removendo dependência de `SUPERVISOR_SUMMARY_MORNING_HOUR` e `SUPERVISOR_SUMMARY_EVENING_HOUR`.
- [x] 1.3 Atualizar `.env.example` e testes de configuração para novo padrão global `SUPERVISOR_SUMMARY_CUTOFF_HOURS=7,13,19`.

## 2. Resolução de janela no scheduler e observabilidade

- [x] 2.1 Adicionar/ajustar testes unitários do scheduler para janelas `[19:00,07:00)`, `[07:00,13:00)` e `[13:00,19:00)` no timezone configurado.
- [x] 2.2 Ajustar `supervisor_summary_scheduler_service` para resolver `window_end` no último cutoff `<= run_at_local` e `window_start` no cutoff imediatamente anterior (sequência circular diária).
- [x] 2.3 Manter política sem catch-up automático e reforçar logs do scheduler com `window_start/window_end`, timezone, cutoff aplicado e marcador explícito `catch_up=false`.

## 3. Convergência Ansible para baseline global 7,13,19

- [x] 3.1 Atualizar testes de Ansible para exigir `SUPERVISOR_SUMMARY_CUTOFF_HOURS` como pré-requisito do cron da Room-4.
- [x] 3.2 Atualizar `ansible/inventory/group_vars/all.yml` e validações de runtime para refletir o novo contrato de env obrigatório.
- [x] 3.3 Atualizar defaults do cron para baseline UTC equivalente (`ats_room4_scheduler_cron_hour: "10,16,22"`) e ajustar testes/documentação associados.

## 4. Documentação operacional e coerência timezone/cron

- [x] 4.1 Atualizar `docs/runtime-smoke.md` e `docs/en/runtime-smoke.md` com o novo padrão de três execuções e janelas variáveis.
- [x] 4.2 Atualizar `docs/ansible_ops_runbook.md` e `docs/en/ansible_ops_runbook.md` com checklist explícito de coerência entre timezone do app e cron.
- [x] 4.3 Documentar comportamento sem catch-up automático e procedimentos de diagnóstico por logs/evidência de enfileiramento.

## 5. Verificação, validação e fechamento

- [x] 5.1 Executar testes-alvo (`uv run pytest`) para settings, scheduler, runtime scheduler e contratos Ansible alterados.
- [ ] 5.2 Executar `uv run ruff check` e `uv run mypy` nos paths alterados.
- [ ] 5.3 Executar `markdownlint-cli2 "openspec/changes/room4-summary-configurable-cutoff-hours/**/*.md"` e registrar evidências no próprio `tasks.md`.
- [ ] 5.4 Executar `openspec validate room4-summary-configurable-cutoff-hours` antes de iniciar implementação.

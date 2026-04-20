# Tasks

## 1. Fase 1 - Contrato estruturado LLM1

- [x] 1.1 (Slice vertical) Criar testes de validação para novos campos de origem, transfusão binária e exames rastreados com recência em `tests/unit/test_llm1_validation.py`.
- [ ] 1.2 (Slice vertical) Implementar extensão do schema em `src/triage_automation/application/dto/llm1_models.py` para suportar origem, transfusão e exames rastreados.

## 2. Fase 2 - Prompt LLM1 versionado

- [ ] 2.1 (Slice vertical) Criar testes que validem instruções de prompt LLM1 para procedência, recência e transfusão com fallback negativo.
- [ ] 2.2 (Slice vertical) Atualizar `src/triage_automation/application/services/llm1_service.py` com novas instruções do prompt e criar migração Alembic de versão de prompt (`llm1_system`/`llm1_user` v6).

## 3. Fase 3 - Room-2 com origem e transfusão explícitas

- [ ] 3.1 (Slice vertical) Criar testes de template Room-2 (unit + integração) para renderizar origem com fallback `sem evidência no laudo` e linha mandatória `Há relato de transfusão? sim|não`.
- [ ] 3.2 (Slice vertical) Implementar renderização markdown/HTML correspondente em `src/triage_automation/infrastructure/matrix/message_templates.py`.

## 4. Fase 4 - Room-2 com exames marcados como mais recentes

- [ ] 4.1 (Slice vertical) Criar testes de template Room-2 para exames com sufixo `(mais recente)` e fallback `recência indeterminada (sem data no laudo)`.
- [ ] 4.2 (Slice vertical) Implementar renderização dos exames rastreados no template Room-2, com regra de empate por última ocorrência textual.

## 5. Fase 5 - Cliente determinístico e consistência de runtime

- [ ] 5.1 (Slice vertical) Criar/ajustar testes do cliente determinístico para refletir o contrato LLM1 estendido.
- [ ] 5.2 (Slice vertical) Atualizar `src/triage_automation/infrastructure/llm/deterministic_client.py` para gerar payloads com origem, transfusão e exames rastreados.

## 6. Fase 6 - Fechamento e evidências

- [ ] 6.1 (Slice vertical) Consolidar relatório final em `docs/implementation-reports/room2-report-origin-recent-exams-transfusion.md` com checklist por slice, comandos executados, fragmentos de diff e cobertura dos 3 requisitos.
- [ ] 6.2 Revisar com solicitante, registrar pendências/follow-ups e preparar arquivamento do change após aprovação.

# Tasks

## 1. Contratos de extração objetiva no LLM1

- [x] 1.1 Adicionar testes (red) para extração de `exam_type` (`eda|non_eda|unknown`) e campos objetivos de risco/documentação (`has_cardiovascular_disease`, `has_active_respiratory_symptoms`, `has_prior_respiratory_disease`, `has_ecg_report`, `has_chest_xray_report`, `hb_g_dl`, `platelets_per_mm3`, `inr`) com fallback `unknown` quando não houver evidência textual.
- [x] 1.2 Implementar atualização de DTO/schema do LLM1 e prompt de extração para exigir evidência textual e proibir inferência de ASA/Mallampati/OSA.
- [x] 1.3 Adicionar cobertura para `evidence_spans` na saída de extração e persistência de campos necessários para decisão determinística.

## 2. Gate de escopo EDA e roteamento para revisão manual

- [x] 2.1 Adicionar testes (red) garantindo que `non_eda` e `unknown` resultem em `manual_review_required` sem recomendação automática `accept|deny`.
- [x] 2.2 Implementar gate determinístico de escopo antes da recomendação clínica e impedir enfileiramento do fluxo automático de recomendação EDA quando escopo não for EDA.
- [x] 2.3 Implementar mensagem de encerramento no Room-1 para casos fora de escopo/indefinidos com texto de revisão manual obrigatória.
- [x] 2.4 Implementar auditoria determinística para esses casos com `reason_code`, `reason_text` e `evidence_spans`.

## 3. Política determinística de critérios pré-procedimento EDA

- [x] 3.1 Adicionar testes (red) para precedência de cenário local: exclusões (`gastrostomia`, `dilatação esofágica`), exceção de corpo estranho e regras de hemorragia/dor/dispepsia.
- [x] 3.2 Implementar regras determinísticas de hemorragia/dor/dispepsia: negar com `hb <= 7`, `platelets <= 100000`, `inr >= 1.5` e ausência de ECG.
- [ ] 3.3 Implementar fallback baseline CHD para demais EDA (`hb < 7`, `platelets < 50000`, `inr > 2`).
- [ ] 3.4 Implementar negação para todas as EDA quando houver risco relatado sem exame obrigatório correspondente:
- [ ] 3.5 doença cardiovascular relatada + sem ECG -> `missing_ecg_with_cardiovascular_disease`.
- [ ] 3.6 sintoma respiratório ativo ou patologia respiratória prévia + sem RX tórax -> `missing_chest_xray_with_respiratory_risk`.
- [ ] 3.7 Implementar sinalização pediátrica (`age < 16`) no output explicável.

## 4. Contrato de saída explicável e integração com mensagens

- [ ] 4.1 Adicionar testes (red) para contrato de saída determinística com `decision`, `reason_code`, `reason_text`, `evidence_spans` e bloco compatível (`preop_gate`) sem quebrar consumidores legados de `suggestion`.
- [ ] 4.2 Implementar serialização/persistência do bloco `preop_gate` e reason codes aprovados no design.
- [ ] 4.3 Implementar regra de não publicação de resumo de recomendação no Room-2 quando o caso for `manual_review_required` por escopo.
- [ ] 4.4 Implementar explicação textual concisa no Room-2 para negações por ausência de ECG/RX em contexto de risco.

## 5. Qualidade, validação e documentação operacional

- [ ] 5.1 Atualizar documentação operacional e runbook manual E2E para cenários de escopo `non_eda|unknown`, revisão manual no Room-1 e negações determinísticas por ausência de ECG/RX.
- [ ] 5.2 Executar validações obrigatórias do change: `uv run pytest` (alvos), `uv run ruff check` (paths alterados), `uv run mypy` (paths alterados) e `markdownlint-cli2` nos artefatos OpenSpec alterados.
- [ ] 5.3 Registrar evidências de verificação e observações de rollout/rollback neste `tasks.md` após conclusão da implementação.

## Notes

- Slice 1.1 (red) executado com:
  - `uv run pytest tests/unit/test_llm1_validation.py -k preop_screening -q` -> 2 falhas esperadas (`preop_screening` ainda não aceito no schema atual).
  - `uv run ruff check tests/unit/test_llm1_validation.py` -> sem erros.
  - `uv run mypy tests/unit/test_llm1_validation.py` -> sem erros.
- Slice 1.2 (green) executado com:
  - `uv run pytest tests/unit/test_llm1_validation.py -q` -> 10 passed.
  - `uv run pytest tests/unit/test_llm2_validation.py -q` -> 2 passed.
  - `uv run pytest tests/integration/test_llm_prompt_loading_runtime.py -q` -> 3 passed.
  - `uv run pytest tests/integration/test_prompt_management_admin_endpoints.py -q` -> 13 passed.
  - `uv run pytest tests/integration/test_process_pdf_case_llm1.py -q` -> 2 passed.
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -q` -> 3 passed.
  - `uv run pytest tests/integration/test_worker_runtime_service_wiring.py -q` -> 3 passed.
  - `uv run pytest tests/integration/test_post_room2_widget.py -q` -> 2 passed.
  - `uv run pytest tests/e2e/test_full_case_flow.py -q` -> 2 passed.
  - `uv run ruff check <paths alterados>` -> sem erros.
  - `uv run mypy src/triage_automation/application/dto/llm1_models.py src/triage_automation/application/services/llm1_service.py src/triage_automation/infrastructure/llm/deterministic_client.py` -> sem erros.
- Slice 1.3 (red->green) executado com:
  - `uv run pytest tests/unit/test_llm1_validation.py -k evidence_spans -q` -> 1 falha esperada (schema sem `evidence_spans`).
  - `uv run pytest tests/integration/test_process_pdf_case_llm1.py -q` -> 1 falha esperada + 1 passed antes da implementação (payload com `evidence_spans` rejeitado).
  - `uv run pytest tests/unit/test_llm1_validation.py -q` -> 11 passed.
  - `uv run pytest tests/integration/test_process_pdf_case_llm1.py -q` -> 2 passed.
  - `uv run pytest tests/unit/test_llm2_validation.py tests/integration/test_llm_prompt_loading_runtime.py tests/integration/test_process_pdf_case_llm2.py tests/integration/test_worker_runtime_service_wiring.py tests/integration/test_post_room2_widget.py tests/e2e/test_full_case_flow.py -q` -> 15 passed.
  - `uv run ruff check src/triage_automation/application/dto/llm1_models.py src/triage_automation/application/services/llm1_service.py src/triage_automation/infrastructure/llm/deterministic_client.py tests/unit/test_llm1_validation.py tests/integration/test_process_pdf_case_llm1.py` -> sem erros.
  - `uv run mypy src/triage_automation/application/dto/llm1_models.py src/triage_automation/application/services/llm1_service.py src/triage_automation/infrastructure/llm/deterministic_client.py` -> sem erros.
- Slice 2.1 (red) executado com:
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -k "scope_requires_manual_review" -q` -> 2 falhas esperadas (ainda sem gate determinístico para `non_eda|unknown`).
  - `uv run ruff check tests/integration/test_process_pdf_case_llm2.py` -> sem erros.
  - `uv run mypy tests/integration/test_process_pdf_case_llm2.py` -> sem erros.
- Slice 2.2 (green) executado com:
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -k "scope_requires_manual_review" -q` -> 2 passed.
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py tests/integration/test_worker_runtime_service_wiring.py tests/integration/test_process_pdf_case_llm1.py tests/unit/test_llm1_validation.py tests/unit/test_llm2_validation.py -q` -> 23 passed.
  - `uv run ruff check src/triage_automation/application/services/process_pdf_case_service.py tests/integration/test_process_pdf_case_llm2.py` -> sem erros.
  - `uv run mypy src/triage_automation/application/services/process_pdf_case_service.py tests/integration/test_process_pdf_case_llm2.py` -> sem erros.
- Slice 2.3 (red->green) executado com:
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -k "scope_requires_manual_review" tests/integration/test_room1_final_reply_jobs.py -q` -> falhas esperadas (job `post_room1_final_scope_manual_review` não enfileirado e tipo de job ainda não suportado no serviço Room-1 final).
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -k "scope_requires_manual_review" -q` -> 2 passed.
  - `uv run pytest tests/integration/test_room1_final_reply_jobs.py tests/unit/test_worker_main.py -q` -> 8 passed.
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py tests/integration/test_worker_runtime_service_wiring.py tests/e2e/test_full_case_flow.py -q` -> 10 passed.
  - `uv run ruff check src/triage_automation/application/services/process_pdf_case_service.py src/triage_automation/application/services/post_room1_final_service.py src/triage_automation/infrastructure/matrix/message_templates.py apps/worker/main.py tests/integration/test_process_pdf_case_llm2.py tests/integration/test_room1_final_reply_jobs.py tests/unit/test_worker_main.py` -> sem erros.
  - `uv run mypy src/triage_automation/application/services/process_pdf_case_service.py src/triage_automation/application/services/post_room1_final_service.py src/triage_automation/infrastructure/matrix/message_templates.py tests/integration/test_process_pdf_case_llm2.py tests/integration/test_room1_final_reply_jobs.py tests/unit/test_worker_main.py` -> sem erros.
  - `uv run mypy -m apps.worker.main` -> sem erros.
- Slice 2.4 (red->green) executado com:
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -k "scope_requires_manual_review" -q` -> 2 falhas esperadas (evento de auditoria `EDA_SCOPE_GATED_MANUAL_REVIEW` ainda não persistido).
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -k "scope_requires_manual_review" -q` -> 2 passed.
  - `uv run pytest tests/integration/test_room1_final_reply_jobs.py -q` -> 1 passed.
  - `uv run pytest tests/unit/test_worker_main.py tests/integration/test_process_pdf_case_llm2.py tests/integration/test_worker_runtime_service_wiring.py tests/e2e/test_full_case_flow.py -q` -> 17 passed.
  - `uv run ruff check src/triage_automation/application/services/process_pdf_case_service.py src/triage_automation/application/services/post_room1_final_service.py src/triage_automation/infrastructure/matrix/message_templates.py apps/worker/main.py tests/integration/test_process_pdf_case_llm2.py tests/integration/test_room1_final_reply_jobs.py tests/unit/test_worker_main.py` -> sem erros.
  - `uv run mypy src/triage_automation/application/services/process_pdf_case_service.py src/triage_automation/application/services/post_room1_final_service.py src/triage_automation/infrastructure/matrix/message_templates.py tests/integration/test_process_pdf_case_llm2.py tests/integration/test_room1_final_reply_jobs.py tests/unit/test_worker_main.py` -> sem erros.
  - `uv run mypy -m apps.worker.main` -> sem erros.
- Slice 3.1 (red) executado com:
  - `uv run pytest tests/unit/test_eda_preop_policy.py -q` -> 7 falhas esperadas (`triage_automation.domain.policy.eda_preop_policy` ainda inexistente neste ponto).
  - `uv run ruff check tests/unit/test_eda_preop_policy.py` -> sem erros.
  - `uv run mypy tests/unit/test_eda_preop_policy.py` -> sem erros.
- Slice 3.2 (red->green) executado com:
  - `uv run pytest tests/unit/test_eda_preop_policy.py -q` -> 9 falhas esperadas após ampliar cobertura (`platelets <= 100000` e `inr >= 1.5`) enquanto módulo ainda não existia.
  - `uv run pytest tests/unit/test_eda_preop_policy.py -q` -> 9 passed após implementar `eda_preop_policy`.
  - `uv run ruff check src/triage_automation/domain/policy/eda_preop_policy.py tests/unit/test_eda_preop_policy.py` -> sem erros.
  - `uv run mypy src/triage_automation/domain/policy/eda_preop_policy.py tests/unit/test_eda_preop_policy.py` -> sem erros.

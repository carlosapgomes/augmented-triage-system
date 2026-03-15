# EDA decision rulebook rewrite tasks

## 1. LLM1 contract and extraction inputs

- [x] 1.1 Update the LLM1 schema models to represent the rewritten EDA scope and subtype set (`standard`, `gastrostomy`, `esophageal_dilation`, `foreign_body`) and add the structured fields required by the new rulebook.
- [x] 1.2 Update the LLM1 prompts and validation rules to allow practical ASA estimation (`I-II`, `III ou mais`, insufficient-data fallback) and to capture the evidence model required for minimum exams, conditional exams, and pediatric context.
- [x] 1.3 Add or update deterministic/adaptor fixtures and validation tests for the new LLM1 schema, including supported EDA subtypes, ASA estimate outputs, and evidence-insufficient cases.

## 2. EDA scope classification and clinical policy rewrite

- [x] 2.1 Refactor scope classification so `gastrostomy`, `esophageal_dilation`, and `foreign_body` remain inside supported EDA flow while true `non_eda` and unresolved `unknown` requests continue to `manual_review_required`.
- [x] 2.2 Rewrite the deterministic EDA pre-procedure policy to enforce the new minimum-exam set, qualitative evidence equivalences, contraindication thresholds, and foreign-body bypass behavior.
- [x] 2.3 Implement explicit handling for ECG, chest X-ray, and echocardiogram completeness gates, including the requirement for minimal reported findings rather than simple mention of exam existence.
- [x] 2.4 Add targeted unit tests for the rewritten clinical policy covering: missing minimum exams, qualitative evidence acceptance, hepatopathy thresholds, cardiopathy thresholds, combined hepatopathy+cardiopathy thresholds, respiratory/ECG/ECO gates, and foreign-body bypass.

## 3. Recommendation synthesis, ASA, and support mapping

- [x] 3.1 Update recommendation synthesis/reconciliation so the persisted recommendation reflects the rewritten rulebook instead of the legacy operational-vs-non-operational split.
- [x] 3.2 Implement practical ASA propagation and support mapping to `none`, `anesthesist`, and `anesthesist_icu`, including the explicit insufficient-data fallback.
- [x] 3.3 Add or adjust integration tests for the pipeline (`process_pdf_case`, recommendation persistence, and Room-2 inputs) to validate the new rulebook outputs and support mapping.

## 4. Room-2 clinical summary and context propagation

- [x] 4.1 Update Room-2 message rendering to display the canonical requested procedure for supported EDA subtypes and the contextual marker `paciente pediátrico: sim` when applicable.
- [x] 4.2 Add the explicit `ASA estimado` block to the Room-2 summary in the agreed order (`Decisão sugerida`, `Suporte recomendado`, `ASA estimado`, `Motivo objetivo`).
- [x] 4.3 Rewrite Room-2 objective-reason rendering to explain the new denial causes coherently, including missing minimum exams, missing ECG/RX/ECO evidence, and contraindication thresholds.
- [x] 4.4 Update unit and integration tests for Room-2 summary rendering to cover ASA display, pediatric marker propagation, supported subtype wording, and new objective-reason precedence.

## 5. Documentation and bilingual mirrors

- [x] 5.1 Update `docs/decision-engine-and-rulebook.md` to describe the rewritten EDA rulebook, supported subtypes, evidence rules, contraindication thresholds, practical ASA estimate, and support semantics.
- [x] 5.2 Update `docs/en/decision-engine-and-rulebook.md` as the required English mirror of the rulebook documentation change.
- [x] 5.3 Update `docs/manual_e2e_runbook.md` to cover the new supported EDA subtypes, foreign-body bypass, new denial scenarios, explicit ASA block, and revised manual validation expectations.
- [ ] 5.4 Update `docs/en/manual_e2e_runbook.md` as the required English mirror of the manual E2E runbook change.
- [ ] 5.5 Run markdown and bilingual documentation checks for all changed documentation files and record the command results in this task file.

## 6. Verification and change bookkeeping

- [ ] 6.1 Run targeted pytest coverage for the rewritten EDA policy, scope gating, Room-2 summary rendering, and affected integration flows.
- [ ] 6.2 Run `ruff` and `mypy` against all changed Python paths for this change.
- [ ] 6.3 Update this `tasks.md` with completed checkboxes and verification notes as implementation slices land.

## Notes

- Slice 1.1 verification executed successfully:
  - `uv run pytest tests/unit/test_llm1_validation.py tests/unit/test_llm2_validation.py tests/integration/test_process_pdf_case_llm1.py -q`
  - `uv run ruff check src/triage_automation/application/dto/llm1_models.py tests/unit/test_llm1_validation.py`
  - `uv run mypy src/triage_automation/application/dto/llm1_models.py`
  - `markdownlint-cli2 "openspec/changes/eda-decision-rulebook-rewrite/tasks.md"`
- Slice 1.2 verification executed successfully:
  - `uv run pytest tests/unit/test_llm1_validation.py tests/integration/test_llm_prompt_loading_runtime.py tests/integration/test_process_pdf_case_llm1.py tests/integration/test_prompt_management_admin_endpoints.py tests/integration/test_migration_prompt_templates.py -q`
  - `uv run ruff check src/triage_automation/application/dto/llm1_models.py src/triage_automation/application/services/llm1_service.py alembic/versions/0016_prompt_templates_llm1_ptbr_v5.py tests/unit/test_llm1_validation.py tests/integration/test_llm_prompt_loading_runtime.py tests/integration/test_prompt_management_admin_endpoints.py`
  - `uv run mypy src/triage_automation/application/dto/llm1_models.py src/triage_automation/application/services/llm1_service.py`
- Slice 1.3 verification executed successfully:
  - `uv run pytest tests/unit/test_deterministic_llm_client.py tests/integration/test_process_pdf_case_llm1.py tests/integration/test_worker_runtime_service_wiring.py -q`
  - `uv run ruff check src/triage_automation/infrastructure/llm/deterministic_client.py tests/unit/test_deterministic_llm_client.py tests/integration/test_process_pdf_case_llm1.py tests/integration/test_worker_runtime_service_wiring.py`
  - `uv run mypy src/triage_automation/infrastructure/llm/deterministic_client.py`
- Slice 2.1 verification executed successfully:
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py -q`
  - `uv run ruff check src/triage_automation/application/services/process_pdf_case_service.py tests/integration/test_process_pdf_case_llm2.py`
  - `uv run mypy src/triage_automation/application/services/process_pdf_case_service.py`
- Slice 2.2 verification executed successfully:
  - `uv run pytest tests/unit/test_eda_preop_policy.py tests/unit/test_eda_policy_crosscheck.py tests/integration/test_process_pdf_case_llm2.py -q`
  - `uv run ruff check src/triage_automation/domain/policy/eda_preop_policy.py tests/unit/test_eda_preop_policy.py tests/integration/test_process_pdf_case_llm2.py`
  - `uv run mypy src/triage_automation/domain/policy/eda_preop_policy.py`
- Slice 2.3 verification executed successfully:
  - `uv run pytest tests/unit/test_eda_preop_policy.py tests/unit/test_eda_policy_crosscheck.py tests/integration/test_process_pdf_case_llm2.py -q`
  - `uv run ruff check src/triage_automation/domain/policy/eda_preop_policy.py tests/unit/test_eda_preop_policy.py tests/integration/test_process_pdf_case_llm2.py`
  - `uv run mypy src/triage_automation/domain/policy/eda_preop_policy.py`
- Slice 2.4 verification executed successfully:
  - `uv run pytest tests/unit/test_eda_preop_policy.py tests/unit/test_eda_policy_crosscheck.py -q`
  - `uv run ruff check tests/unit/test_eda_preop_policy.py`
  - `uv run mypy src/triage_automation/domain/policy/eda_preop_policy.py`
- Slice 3.1 verification executed successfully:
  - `uv run pytest tests/unit/test_llm2_validation.py tests/integration/test_process_pdf_case_llm2.py -q`
  - `uv run ruff check src/triage_automation/application/services/llm2_service.py src/triage_automation/application/services/process_pdf_case_service.py tests/integration/test_process_pdf_case_llm2.py`
  - `uv run mypy src/triage_automation/application/services/llm2_service.py src/triage_automation/application/services/process_pdf_case_service.py`
- Slice 3.2 verification executed successfully:
  - `uv run pytest tests/unit/test_eda_recommendation_synthesis.py tests/integration/test_process_pdf_case_llm2.py -q`
  - `uv run ruff check src/triage_automation/domain/policy/eda_recommendation_synthesis.py src/triage_automation/application/services/process_pdf_case_service.py tests/unit/test_eda_recommendation_synthesis.py tests/integration/test_process_pdf_case_llm2.py`
  - `uv run mypy src/triage_automation/domain/policy/eda_recommendation_synthesis.py src/triage_automation/application/services/process_pdf_case_service.py`
- Slice 3.3 verification executed successfully:
  - `uv run pytest tests/integration/test_process_pdf_case_llm2.py tests/integration/test_post_room2_widget.py -q`
  - `uv run ruff check src/triage_automation/application/services/post_room2_widget_service.py tests/integration/test_post_room2_widget.py tests/integration/test_process_pdf_case_llm2.py`
  - `uv run mypy src/triage_automation/application/services/post_room2_widget_service.py`
- Slice 4.1 verification executed successfully:
  - `uv run pytest tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py -q`
  - `uv run ruff check src/triage_automation/infrastructure/matrix/message_templates.py tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py`
  - `uv run mypy src/triage_automation/infrastructure/matrix/message_templates.py`
- Slice 4.2 verification executed successfully:
  - `uv run pytest tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py -q`
  - `uv run ruff check src/triage_automation/infrastructure/matrix/message_templates.py tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py`
  - `uv run mypy src/triage_automation/infrastructure/matrix/message_templates.py`
- Slice 4.3 verification executed successfully:
  - `uv run pytest tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py -q`
  - `uv run ruff check src/triage_automation/infrastructure/matrix/message_templates.py tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py`
  - `uv run mypy src/triage_automation/infrastructure/matrix/message_templates.py`
  - `markdownlint-cli2 "openspec/changes/eda-decision-rulebook-rewrite/tasks.md"`
- Slice 4.4 verification executed successfully:
  - `uv run pytest tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py -q`
  - `uv run ruff check tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py`
  - `uv run mypy tests/unit/test_room2_message_templates.py tests/integration/test_post_room2_widget.py`
  - `markdownlint-cli2 "openspec/changes/eda-decision-rulebook-rewrite/tasks.md"`
- Slice 5.1 verification executed successfully:
  - `markdownlint-cli2 "docs/decision-engine-and-rulebook.md"`
  - `markdownlint-cli2 "openspec/changes/eda-decision-rulebook-rewrite/tasks.md"`
  - Exceção registrada de sincronização bilíngue: `docs/en/decision-engine-and-rulebook.md` será atualizado no slice 5.2 para respeitar a regra de uma tarefa por sessão.
  - Guardas bilíngues não executados neste slice porque o espelho em inglês ainda não foi atualizado.
- Slice 5.2 verification executed successfully:
  - `markdownlint-cli2 "docs/decision-engine-and-rulebook.md" "docs/en/decision-engine-and-rulebook.md"`
  - `uv run pytest tests/unit/test_readme_bilingual_baseline.py tests/unit/test_docs_bilingual_mirror.py -q`
  - `markdownlint-cli2 "openspec/changes/eda-decision-rulebook-rewrite/tasks.md"`
- Slice 5.3 verification executed successfully:
  - `markdownlint-cli2 --fix "docs/manual_e2e_runbook.md"`
  - `markdownlint-cli2 "docs/manual_e2e_runbook.md"`
  - `markdownlint-cli2 "openspec/changes/eda-decision-rulebook-rewrite/tasks.md"`
  - Exceção registrada de sincronização bilíngue: `docs/en/manual_e2e_runbook.md` será atualizado no slice 5.4 para respeitar a regra de uma tarefa por sessão.
  - Guardas bilíngues não executados neste slice porque o espelho em inglês ainda não foi atualizado.

# Tasks

## 1. Contratos de extração objetiva no LLM1

- [ ] 1.1 Adicionar testes (red) para extração de `exam_type` (`eda|non_eda|unknown`) e campos objetivos de risco/documentação (`has_cardiovascular_disease`, `has_active_respiratory_symptoms`, `has_prior_respiratory_disease`, `has_ecg_report`, `has_chest_xray_report`, `hb_g_dl`, `platelets_per_mm3`, `inr`) com fallback `unknown` quando não houver evidência textual.
- [ ] 1.2 Implementar atualização de DTO/schema do LLM1 e prompt de extração para exigir evidência textual e proibir inferência de ASA/Mallampati/OSA.
- [ ] 1.3 Adicionar cobertura para `evidence_spans` na saída de extração e persistência de campos necessários para decisão determinística.

## 2. Gate de escopo EDA e roteamento para revisão manual

- [ ] 2.1 Adicionar testes (red) garantindo que `non_eda` e `unknown` resultem em `manual_review_required` sem recomendação automática `accept|deny`.
- [ ] 2.2 Implementar gate determinístico de escopo antes da recomendação clínica e impedir enfileiramento do fluxo automático de recomendação EDA quando escopo não for EDA.
- [ ] 2.3 Implementar mensagem de encerramento no Room-1 para casos fora de escopo/indefinidos com texto de revisão manual obrigatória.
- [ ] 2.4 Implementar auditoria determinística para esses casos com `reason_code`, `reason_text` e `evidence_spans`.

## 3. Política determinística de critérios pré-procedimento EDA

- [ ] 3.1 Adicionar testes (red) para precedência de cenário local: exclusões (`gastrostomia`, `dilatação esofágica`), exceção de corpo estranho e regras de hemorragia/dor/dispepsia.
- [ ] 3.2 Implementar regras determinísticas de hemorragia/dor/dispepsia: negar com `hb <= 7`, `platelets <= 100000`, `inr >= 1.5` e ausência de ECG.
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

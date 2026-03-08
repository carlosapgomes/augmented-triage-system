# Motor de Decisão e Rulebook

Idioma: **Português (BR)** | [English](en/decision-engine-and-rulebook.md)

## Objetivo

Este documento descreve como o ATS toma decisões ao longo do fluxo de triagem,
com foco em previsibilidade para manutenção futura.

A intenção é evitar ambiguidades comuns, como assumir que a decisão clínica é
“do prompt”. No ATS, o prompt orienta extração e sugestão, mas as regras
operacionais críticas são determinísticas em código e a decisão clínica final
continua com o médico.

## Princípios do motor de decisão

1. Prompts são contrato de extração/estrutura, não autoridade final de regra.
2. Regras determinísticas são codificadas em serviços/políticas de domínio.
3. Toda saída crítica deve ser auditável (`reason_code`, `reason_text`, evidências).
4. Decisão médica final permanece humana (resposta estruturada Matrix na Room-2).

## Fluxo geral (narrativa)

1. **Coleta e extração inicial**
   - O caso entra via Room-1 com PDF.
   - O worker executa extração textual e chama LLM1 para estruturar os dados.

1. **Pré-processamento determinístico de escopo**
   - O sistema avalia `preop_screening.exam_type`.
   - Se `non_eda|unknown`, encerra em `manual_review_required` com fechamento na
     Room-1 e auditoria; não segue para recomendação automática Room-2.

1. **Sugestão LLM2 e reconciliação**
   - Para `eda`, o sistema chama LLM2 para sugestão (`accept|deny`).
   - Em seguida aplica reconciliação determinística de política (hard-rules) para
     impedir inconsistências entre sugestão e regras obrigatórias.

1. **Gate pré-procedimento determinístico (`preop_gate`)**
   - A política EDA determinística calcula decisão explicável (`decision`,
     `reason_code`, `reason_text`, `evidence_spans`, `pediatric_flag`).
   - O bloco é persistido em `suggested_action_json.preop_gate` sem quebrar
     consumidores legados de `suggestion`.

1. **Publicação para revisão médica na Room-2**
   - Apenas casos elegíveis são publicados com resumo técnico e template estrito
     de resposta.

1. **Decisão médica e finalização**
   - Médico responde via Matrix structured reply na Room-2.
   - O sistema valida contrato, aplica transição de estado e executa jobs de
     finalização (Room-3/Room-1 conforme o caso).

## Fluxo geral (tabela)

| Etapa | Entrada | Componente principal | Saída principal |
| --- | --- | --- | --- |
| Intake + extração | PDF Room-1 | `process_pdf_case_service` + LLM1 | `structured_data_json` |
| Gate de escopo | `structured_data_json.preop_screening.exam_type` | `process_pdf_case_service` | `manual_review_required` (se `non_eda\|unknown`) |
| Sugestão clínica | `structured_data_json` (EDA) | `llm2_service` | `suggested_action_json.suggestion` |
| Reconciliação hard-rule | precheck + sugestão LLM2 | `domain/policy/eda_policy.py` | sugestão reconciliada |
| Gate determinístico EDA | `structured_data_json` | `domain/policy/eda_preop_policy.py` | `preop_gate` explicável |
| Revisão médica Room-2 | mensagem I/II/III + template | `room2_reply_service` | decisão médica aplicada |
| Encerramento operacional | decisão humana + estado | serviços de post final/jobs | resposta final + auditoria + cleanup |

## Domínio EDA (primeiro domínio suportado)

Atualmente, o fluxo automático aplica regras determinísticas para EDA e trata
`non_eda|unknown` como revisão manual obrigatória.

As regras EDA estão separadas em dois blocos:

- **Regras pré-procedimento explicáveis:** `eda_preop_policy.py` (`preop_gate`).
- **Regras de reconciliação da sugestão LLM2:** `eda_policy.py`.

## Rulebook EDA (precedência determinística)

A ordem abaixo é a referência para interpretação do comportamento atual.

| Prioridade | Condição | Saída | `reason_code` principal |
| --- | --- | --- | --- |
| 0 | `exam_type` = `non_eda` | `manual_review_required` | `non_eda_request` |
| 0 | `exam_type` = `unknown` | `manual_review_required` | `unknown_exam_type` |
| 1 | `eda.exclusion_type = gastrostomy` | `excluded` | `excluded_gastrostomy` |
| 1 | `eda.exclusion_type = esophageal_dilation` | `excluded` | `excluded_esophageal_dilation` |
| 2 | Risco cardiovascular relatado + sem ECG | `deny` | `missing_ecg_with_cardiovascular_disease` |
| 2 | Risco respiratório relatado + sem RX tórax | `deny` | `missing_chest_xray_with_respiratory_risk` |
| 3 | EDA operacional (`bleeding`, `abdominal_pain`, `dyspepsia`) + `hb <= 7` | `deny` | `hb_below_threshold` |
| 3 | EDA operacional + `platelets <= 100000` | `deny` | `platelets_below_threshold` |
| 3 | EDA operacional + `inr >= 1.5` | `deny` | `inr_above_threshold` |
| 3 | EDA operacional + ECG ausente | `deny` | `missing_ecg_with_cardiovascular_disease` |
| 4 | EDA não operacional + `hb < 7` | `deny` | `hb_below_threshold` |
| 4 | EDA não operacional + `platelets < 50000` | `deny` | `platelets_below_threshold` |
| 4 | EDA não operacional + `inr > 2` | `deny` | `inr_above_threshold` |
| 5 | `eda.indication_category = foreign_body` | `accept` | `foreign_body_exception` |
| 6 | Sem gatilhos de negação/exclusão | `accept` | `criteria_met` |

## Catálogo prático de `reason_code`

| `reason_code` | Significado operacional | Consumidor principal |
| --- | --- | --- |
| `non_eda_request` | Escopo não EDA: revisão manual obrigatória | runtime + Room-1 final |
| `unknown_exam_type` | Tipo de exame indefinido: revisão manual obrigatória | runtime + Room-1 final |
| `excluded_gastrostomy` | Solicitação excluída do fluxo automático EDA | `preop_gate` |
| `excluded_esophageal_dilation` | Solicitação excluída do fluxo automático EDA | `preop_gate` |
| `missing_ecg_with_cardiovascular_disease` | Risco cardiovascular sem ECG | `preop_gate` + resumo Room-2 |
| `missing_chest_xray_with_respiratory_risk` | Risco respiratório sem RX tórax | `preop_gate` + resumo Room-2 |
| `hb_below_threshold` | Hb abaixo do limiar do cenário | `preop_gate` |
| `platelets_below_threshold` | Plaquetas abaixo do limiar do cenário | `preop_gate` |
| `inr_above_threshold` | INR acima do limiar do cenário | `preop_gate` |
| `manual_review_required_insufficient_data` | Fallback defensivo para payload incompleto | serialização `preop_gate` |
| `foreign_body_exception` | Exceção de corpo estranho (aceite sem gate lab de rotina) | `preop_gate` |
| `criteria_met` | Critérios determinísticos atendidos | `preop_gate` |

## Mapa de extensão de regras (onde mexer)

| Mudança desejada | Arquivo principal | Testes mínimos esperados |
| --- | --- | --- |
| Novo gate ou limiar determinístico EDA | `src/triage_automation/domain/policy/eda_preop_policy.py` | `tests/unit/test_eda_preop_policy.py` |
| Alterar roteamento de escopo (`non_eda\|unknown`) | `src/triage_automation/application/services/process_pdf_case_service.py` | `tests/integration/test_process_pdf_case_llm2.py` |
| Alterar texto objetivo da negativa no Room-2 | `src/triage_automation/infrastructure/matrix/message_templates.py` | `tests/unit/test_room2_message_templates.py` + `tests/integration/test_post_room2_widget.py` |
| Alterar parser/contrato de decisão médica Room-2 | `src/triage_automation/domain/doctor_decision_parser.py` | testes unitários do parser + integração de reply |

## Onde as regras vivem no código

- Orquestração do pipeline: `src/triage_automation/application/services/process_pdf_case_service.py`
- Política determinística EDA (`preop_gate`): `src/triage_automation/domain/policy/eda_preop_policy.py`
- Reconciliação hard-rule da sugestão LLM2: `src/triage_automation/domain/policy/eda_policy.py`
- Captura de decisão médica (Room-2):
  - `src/triage_automation/application/services/room2_reply_service.py`
  - `src/triage_automation/application/services/handle_doctor_decision_service.py`

## Playbook de evolução de regras (add/remove/change)

### Fluxo recomendado por mudança

1. **Defina o impacto funcional antes de codificar**
   - Atualize OpenSpec (design/spec/tasks) quando houver mudança de contrato,
     precedência ou novo `reason_code`.
   - Declare explicitamente se a mudança afeta apenas EDA ou o motor geral.

2. **Escreva testes RED primeiro (contrato + comportamento)**
   - Política determinística: teste unitário no módulo de policy.
   - Orquestração/runtime: teste de integração para estado, jobs e auditoria.
   - Mensagens/UX: teste unitário de template + integração do post na Room-2.

3. **Implemente no módulo certo (sem espalhar regra)**
   - Regra clínica determinística: `eda_preop_policy.py`.
   - Gate de escopo/roteamento de fluxo: `process_pdf_case_service.py`.
   - Texto objetivo para médico: `message_templates.py`.

4. **Garanta explicabilidade e compatibilidade**
   - Toda saída relevante deve carregar `reason_code`, `reason_text` e, quando
     aplicável, `evidence_spans`.
   - Preserve `suggestion` legada e mantenha `preop_gate` como bloco explicável.

5. **Atualize documentação no mesmo slice**
   - Atualize este rulebook (PT-BR) e espelho `docs/en/...`.
   - Atualize runbook operacional quando o comportamento observado mudar.

6. **Rode validações e registre evidência**
   - Execute testes/lint/types e registre comandos/resultados em `tasks.md` do
     change correspondente.

### Checklist anti-regressão (obrigatório)

- [ ] A regra continua determinística no código (não movida para prompt).
- [ ] `reason_code` novo/alterado está mapeado nos consumidores relevantes.
- [ ] `preop_gate` permanece serializado sem quebrar consumidores de `suggestion`.
- [ ] Casos `non_eda|unknown` continuam sem `accept|deny` automático.
- [ ] Room-2 não publica resumo para `manual_review_required` por escopo.
- [ ] Parser de decisão médica da Room-2 mantém contrato estrito.

### Comandos mínimos de validação

```bash
uv run pytest tests/unit/test_eda_preop_policy.py tests/integration/test_process_pdf_case_llm2.py tests/integration/test_post_room2_widget.py tests/unit/test_room2_message_templates.py -q
uv run ruff check src/triage_automation/domain/policy/eda_preop_policy.py src/triage_automation/application/services/process_pdf_case_service.py src/triage_automation/infrastructure/matrix/message_templates.py
uv run mypy src/triage_automation/domain/policy/eda_preop_policy.py src/triage_automation/application/services/process_pdf_case_service.py src/triage_automation/infrastructure/matrix/message_templates.py
markdownlint-cli2 "docs/decision-engine-and-rulebook.md" "docs/en/decision-engine-and-rulebook.md"
```

## Referências

- `docs/manual_e2e_runbook.md`
- `openspec/changes/eda-preop-criteria-and-eda-scope-gating/design.md`
- `openspec/changes/eda-preop-criteria-and-eda-scope-gating/specs/`

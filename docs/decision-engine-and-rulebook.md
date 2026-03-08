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

## Onde as regras vivem no código

- Orquestração do pipeline: `src/triage_automation/application/services/process_pdf_case_service.py`
- Política determinística EDA (`preop_gate`): `src/triage_automation/domain/policy/eda_preop_policy.py`
- Reconciliação hard-rule da sugestão LLM2: `src/triage_automation/domain/policy/eda_policy.py`
- Captura de decisão médica (Room-2):
  - `src/triage_automation/application/services/room2_reply_service.py`
  - `src/triage_automation/application/services/handle_doctor_decision_service.py`

## Evolução de regras (guia curto)

Para adicionar/remover/modificar regras com segurança:

1. Atualize OpenSpec (design/spec/tasks) antes de codificar mudança relevante.
2. Escreva testes RED no nível certo (unit policy + integration runtime/message).
3. Implemente regra determinística no módulo de política apropriado.
4. Garanta saída explicável com `reason_code`/`reason_text` e, quando aplicável,
   `evidence_spans`.
5. Atualize documentação operacional (runbook) e espelho em inglês.
6. Rode quality gates completos (`pytest`, `ruff`, `mypy`, `markdownlint`).

## Referências

- `docs/manual_e2e_runbook.md`
- `openspec/changes/eda-preop-criteria-and-eda-scope-gating/design.md`
- `openspec/changes/eda-preop-criteria-and-eda-scope-gating/specs/`

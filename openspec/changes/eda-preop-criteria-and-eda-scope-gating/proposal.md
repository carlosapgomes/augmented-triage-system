# EDA Preop Criteria and EDA Scope Gating Proposal

## Why

O fluxo atual pode emitir recomendação automática mesmo quando o relatório não é de EDA ou quando faltam exames mínimos em cenários de risco clínico relevante. Isso aumenta risco operacional e reduz confiança médica na automação.

## What Changes

- Adicionar gate determinístico de escopo do exame:
  - quando o tipo de exame estiver `unknown` ou diferente de EDA, o sistema NÃO deve recomendar `accept/deny` e deve sinalizar revisão manual obrigatória.
- Consolidar critérios pré-procedimento de EDA com prioridade para regras locais CHD:
  - preservar critérios da planilha e refinamentos operacionais da equipe CHD;
  - manter regra local para anticoagulantes;
  - aplicar regras explícitas para ausência de ECG/RX em contexto de risco relatado (ex.: doença cardiovascular sem ECG; sintoma respiratório/patologia respiratória prévia sem RX).
- Tornar a decisão explicável com motivo clínico determinístico:
  - emitir `reason_code`, `reason_text` e evidências textuais que sustentam a recomendação.
- Expandir extração objetiva do LLM1 apenas com sinais observáveis no documento (sem inferências de ASA/Mallampati/OSA).
- **BREAKING**: casos fora de escopo EDA ou com tipo de exame não confirmado deixam de receber recomendação automática e passam a `manual_review_required`.

## Capabilities

### New Capabilities

- `eda-preop-deterministic-criteria`: aplica critérios determinísticos de pré-procedimento para EDA com prioridade para baseline CHD e justificativa explícita de decisão.
- `eda-request-scope-gating`: bloqueia recomendação automática quando o exame não é EDA (ou quando não pode ser confirmado) e encaminha para revisão manual.

### Modified Capabilities

- `runtime-orchestration`: altera o comportamento do fluxo para suportar roteamento determinístico de `manual_review_required` em casos fora de escopo EDA e para respeitar gates clínicos pré-procedimento antes da recomendação final.
- `room2-concise-medical-opinion-message`: exige que recomendações negativas por falta de pré-requisito clínico (ex.: ausência de ECG/RX em cenário de risco) tragam justificativa explícita e consistente com os critérios determinísticos.
- `manual-e2e-readiness`: adiciona validações manuais para cenários fora de escopo EDA, tipo de exame indefinido, e negações por falta de exame em presença de risco clínico.

## Impact

- Código potencialmente afetado:
  - `src/triage_automation/application/dto/llm1_models.py`
  - `src/triage_automation/application/services/llm1_service.py`
  - `src/triage_automation/application/services/llm2_service.py`
  - `src/triage_automation/domain/policy/eda_policy.py`
  - `src/triage_automation/application/services/process_pdf_case_service.py`
  - `src/triage_automation/application/services/post_room2_widget_service.py`
  - templates/mensagens de Room-2 e eventos de auditoria relacionados
- Impacto de produto:
  - menos recomendações automáticas fora de escopo;
  - maior rastreabilidade clínica por motivo explícito;
  - maior segurança operacional para casos com dados incompletos críticos.
- Dependências e operação:
  - sem dependência de novas integrações externas neste change;
  - sem adoção de classificação ASA/Mallampati/OSA por falta de dados confiáveis nos PDFs de origem.

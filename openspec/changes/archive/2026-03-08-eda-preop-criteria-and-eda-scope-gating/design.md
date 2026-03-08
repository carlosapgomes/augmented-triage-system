# EDA Preop Criteria and EDA Scope Gating Design

## Context

O fluxo atual (`process_pdf_case`) assume recomendação automática `accept|deny` para todos os relatórios processados, com base na cadeia `LLM1 -> LLM2 -> reconcile_eda_policy`. Isso é insuficiente para dois cenários operacionais críticos:

1. relatórios fora de escopo EDA (ou sem tipo de exame confirmável);
2. relatórios EDA com sinais de risco cardiorrespiratório, mas sem exames mínimos documentados (ex.: doença cardiovascular sem ECG; sintoma respiratório ativo/prévio sem RX tórax).

Além disso, os PDFs de origem são heterogêneos (hospital, PA, atenção primária), com baixa disponibilidade de dados para classificações formais de anestesia (ASA/Mallampati/OSA). Portanto, o desenho deve usar apenas sinais observáveis no texto e regras determinísticas explicáveis.

Stakeholders principais:

- equipe CHD (protocolo local como fonte prioritária);
- médicos que consomem recomendação no Room-2;
- operação (auditoria, rastreabilidade e segurança).

Restrições:

- preservar critérios locais CHD como autoridade;
- não substituir protocolo local de anticoagulantes neste change;
- evitar redesign de máquina de estados além do necessário para rotear `manual_review_required`.

## Goals / Non-Goals

**Goals:**

- Aplicar gate determinístico de escopo para emitir `manual_review_required` quando o exame não for EDA ou for `unknown`.
- Consolidar critérios EDA locais com precedência explícita por cenário clínico.
- Negar de forma determinística quando houver risco relatado e ausência de exame obrigatório (ECG/RX), com motivo textual explícito.
- Tornar a decisão auditável por `reason_code`, `reason_text` e `evidence_spans`.
- Expandir extração do LLM1 com campos objetivos observáveis no documento, retornando `unknown` quando não houver evidência.

**Non-Goals:**

- Inferir ASA, Mallampati ou risco OSA a partir de evidência incompleta.
- Substituir regras locais de anticoagulantes por diretrizes externas.
- Redesenhar o workflow clínico completo do produto.
- Automatizar decisão para exames não EDA.

## Decisions

### Decision 1: Gate de escopo antes de qualquer recomendação clínica

- **Escolha:** introduzir um classificador determinístico de escopo com saída:
  - `eda`
  - `non_eda`
  - `unknown`
- **Comportamento:**
  - `non_eda` ou `unknown` -> não produzir recomendação `accept|deny`; produzir `manual_review_required`.
  - `eda` -> seguir para avaliação pré-procedimento determinística.
- **Racional:** evita recomendações indevidas fora do escopo contratado.
- **Alternativa considerada:** tratar `unknown` como `deny`.
- **Motivo da rejeição:** confunde falta de escopo com contraindicação clínica e reduz interpretabilidade.

### Decision 2: Precedência explícita entre fontes locais CHD

- **Escolha:** aplicar regras por prioridade de cenário:
  1. exclusões de escopo local (gastrostomia, dilatação esofágica);
  2. exceção corpo estranho (sem laboratório obrigatório de rotina);
  3. EDA por hemorragia/dor abdominal/dispepsia com critérios operacionais da equipe CHD (HB > 7, plaquetas > 100.000, INR < 1,5, laudo ECG obrigatório);
  4. demais EDA: baseline da planilha CHD (HB < 7, plaquetas < 50.000, INR > 2 como contraindicações).
- **Racional:** resolve divergência aparente entre artefatos locais sem sobrescrever protocolo institucional.
- **Alternativa considerada:** usar apenas a planilha CHD.
- **Motivo da rejeição:** perderia refinamentos operacionais usados na prática do CHD.

### Decision 3: Sem ASA/Mallampati/OSA no contrato automático

- **Escolha:** remover do fluxo automático campos/classificações de ASA/Mallampati/OSA.
- **Racional:** baixa disponibilidade e baixa confiabilidade da fonte documental; risco de indução a erro clínico.
- **Alternativa considerada:** manter campos como opcionais (`unknown`).
- **Motivo da rejeição:** simples presença desses campos na UI aumenta risco de interpretação indevida de classificação formal.

### Decision 4: Negação determinística por ausência de exame em risco relatado

- **Escolha:** quando risco clínico relevante é detectado no texto, ausência de exame associado gera `deny` com motivo específico:
  - doença cardiovascular relatada + ausência de ECG/laudo ECG -> `deny`;
  - sintoma respiratório ativo ou patologia respiratória prévia + ausência de RX tórax/laudo -> `deny`.
- **Racional:** atende exigência operacional de segurança e torna o motivo auditável.
- **Alternativa considerada:** converter ausências sempre para `manual_review_required`.
- **Motivo da rejeição:** regra operacional solicitada é negativa explícita nesses cenários.

### Decision 5: Contrato de extração do LLM1 orientado a evidência

- **Escolha:** ampliar schema do LLM1 com sinais objetivos e trilha de evidência, por exemplo:
  - `indication_category`
  - `age_years`
  - `has_cardiovascular_disease`
  - `has_active_respiratory_symptoms`
  - `has_prior_respiratory_disease`
  - `hb_g_dl`, `platelets_per_mm3`, `inr`
  - `has_ecg_report`, `has_chest_xray_report`, `has_echo_report`
  - `evidence_spans[]`
- **Regra de extração:** se não houver evidência textual, retornar `unknown`.
- **Racional:** minimiza alucinação e melhora explicabilidade.
- **Alternativa considerada:** inferência livre com narrativa clínica.
- **Motivo da rejeição:** baixa reprodutibilidade e risco regulatório.

### Decision 6: Política determinística dedicada para pré-procedimento EDA

- **Escolha:** criar módulo de política dedicado (ex.: `eda_preop_policy`) separado da reconciliação atual do LLM2 (`reconcile_eda_policy`).
- **Racional:** separa claramente:
  - regras de elegibilidade/escopo pré-procedimento;
  - reconciliação de sugestão LLM2.
- **Alternativa considerada:** adicionar toda lógica no `reconcile_eda_policy` existente.
- **Motivo da rejeição:** mistura responsabilidades e aumenta risco de regressão em comportamento já consolidado.

### Decision 7: Contrato de decisão explicável unificado

- **Escolha:** toda saída determinística deve incluir:
  - `decision`: `accept|deny|manual_review_required|excluded`
  - `reason_code`
  - `reason_text`
  - `evidence_spans`
- **Racional:** padroniza auditoria e comunicação no Room-2/dashboard.
- **Alternativa considerada:** manter apenas texto livre.
- **Motivo da rejeição:** inviabiliza testes estáveis e rastreabilidade robusta.

## Risks / Trade-offs

- **[Risco]** Aumento de casos negativos por documentação incompleta, não por contraindicação real.  
  **Mitigação:** mensagens explícitas de "negação por ausência de exame obrigatório em cenário de risco" com evidência textual.

- **[Risco]** Falsos positivos no detector de "doença cardiovascular" ou "sintoma respiratório".  
  **Mitigação:** exigir `evidence_spans` e testes com corpus de variações linguísticas reais.

- **[Risco]** Divergência entre baseline da planilha e refinamentos operacionais CHD.  
  **Mitigação:** codificar precedência por cenário e documentar em spec/README operacional.

- **[Trade-off]** Mais segurança e explicabilidade em troca de menor automação.  
  **Mitigação:** monitorar taxa de `manual_review_required` e motivos mais frequentes para calibração posterior.

## Migration Plan

1. Expandir DTO/schema do LLM1 com campos objetivos + `unknown` como default seguro.
2. Implementar política determinística `eda_preop_policy` (escopo, exceções, gates clínicos, reason codes).
3. Integrar política em `process_pdf_case` após LLM1 e antes da recomendação final persistida.
4. Ajustar payload persistido (`suggested_action_json` ou bloco equivalente) para suportar `manual_review_required` e `reason_code`.
5. Atualizar mensagens e visualização para exibir justificativa determinística, incluindo aviso de encerramento no Room-1 para casos `manual_review_required` fora de escopo EDA ou com exame indefinido.
6. Adicionar cobertura de testes:
   - fora de escopo EDA;
   - tipo de exame `unknown`;
   - cardio sem ECG;
   - respiratório sem RX;
   - corpo estranho (exceção);
   - critérios laboratoriais por cenário CHD.
7. Rollout em duas etapas:
   - etapa A: modo observabilidade (registrar motivo sem alterar decisão automática);
   - etapa B: enforcement completo das regras.

### Rollback

- Desligar enforcement e retornar para decisão anterior mantendo logging das novas extrações.
- Reverter apenas módulo de política nova sem alterar persistência histórica de auditoria.

## Resolved Decisions for Specs

- Casos `non_eda` ou `unknown` devem:
  - gerar auditoria;
  - **não** emitir recomendação clínica `accept|deny`;
  - publicar mensagem no Room-1: "esse relatório não é de solicitação de endoscopia digestiva alta, ou não detectamos qual exame é; precisa de revisão manual".
- Critérios operacionais (HB > 7, plaquetas > 100.000, INR < 1,5, ECG obrigatório) aplicam-se ao cenário de hemorragia digestiva/dor abdominal/dispepsia.
- Regra de `deny` por ausência de ECG/RX em contexto de risco vale para **todas** as EDA:
  - doença cardiovascular relatada + sem ECG -> `deny`;
  - sintoma respiratório ativo ou patologia respiratória prévia + sem RX tórax -> `deny`.
- ECO não será gate duro universal; em ausência de ECO com necessidade clínica contextual, usar `manual_review_required`.
- Persistência deve manter compatibilidade com consumidores atuais por bloco separado `preop_gate` (sem quebrar `suggestion` existente).
- Vocabulário inicial de `reason_code` aprovado:
  - `non_eda_request`
  - `unknown_exam_type`
  - `excluded_gastrostomy`
  - `excluded_esophageal_dilation`
  - `missing_ecg_with_cardiovascular_disease`
  - `missing_chest_xray_with_respiratory_risk`
  - `hb_below_threshold`
  - `platelets_below_threshold`
  - `inr_above_threshold`
  - `manual_review_required_insufficient_data`

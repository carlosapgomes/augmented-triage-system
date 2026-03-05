# EDA Preop Criteria — CHD Base + Refinamento Operacional

## Objetivo

Consolidar critérios para EDA preservando a base local (CHD) e adicionando regras determinísticas apenas para pontos vagos, com justificativa explícita no relatório de decisão.

## Fonte local consolidada

Este documento considera duas fontes internas complementares:

1. Planilha CHD (`CHD-Criterios.xlsx`) — baseline institucional.
2. Mensagem operacional da equipe CHD (critérios de borda e priorização prática).

## Princípio de governança

- **Não sobrescrever critério local.**
- Quando houver aparente diferença entre artefatos locais, aplicar **regra mais específica por cenário clínico** e registrar no motivo da decisão.
- Critérios de anticoagulante seguem protocolo local CHD.

## Critérios locais (preservados)

### Baseline da planilha CHD para EDA

- Exames mínimos: HB/HT, plaquetas, TTPA, TP, ureia, creatinina.
- Contraindicações: HB < 7; plaquetas < 50.000; INR > 2.
- ECG/ECO: "ver com anestesia".
- RX tórax: se sintomas respiratórios ou patologia respiratória prévia.

### Refinamentos operacionais informados pela equipe CHD

- EDA por hemorragia digestiva, dor abdominal ou dispepsia:
  - HB > 7
  - Plaquetas > 100.000
  - INR < 1,5
  - Laudo de ECG obrigatório
- Sinalizar pediátrico: idade < 16 anos.
- Excluir da avaliação EDA quando solicitação for para:
  - confecção de gastrostomia
  - dilatação esofágica
- EDA para retirada de corpo estranho:
  - não exige exames laboratoriais obrigatórios
- Avaliar risco cardiovascular com idade, comorbidades, laboratório, ECG, ECO e RX tórax.

## Regras determinísticas propostas (sem ASA/Mallampati/OSA)

> Decisão sempre com justificativa textual explícita no relatório.

## 1) Exclusão por escopo

- Se indicação for "gastrostomia" ou "dilatação esofágica" -> `EXCLUDED_FROM_EDA_FLOW`.

## 2) Exceção de corpo estranho

- Se indicação for "retirada de corpo estranho" -> não exigir laboratório obrigatório de rotina para gate.

## 3) Gate de indicação clínica principal (hemorragia/dor/dispepsia)

- Se indicação for hemorragia digestiva, dor abdominal ou dispepsia:
  - negar se HB <= 7
  - negar se plaquetas <= 100.000
  - negar se INR >= 1,5
  - negar se não houver laudo de ECG

## 4) Gate cardiorrespiratório por completude mínima

- Se houver doença cardiovascular relatada e não houver ECG/laudo ECG -> negar.
- Se houver sintoma respiratório ativo ou patologia respiratória prévia e não houver RX tórax/laudo -> negar.
- Se houver sinais compatíveis com insuficiência cardíaca descompensada e não houver avaliação cardíaca mínima documentada (ECG; e ECO quando mencionado como necessário no texto clínico) -> negar.

## 5) Sinalização pediátrica

- Se idade < 16 -> marcar `PEDIATRIC_FLAG=true` e destacar no relatório.

## 6) Anticoagulantes

- Manter regra local CHD (não substituir por diretriz externa neste ciclo).

## Saída de decisão e explicabilidade

Padronizar motivo com estrutura:

- `decision`: `accept|deny|excluded`
- `reason_code`: código estável (ex.: `missing_ecg_with_cardiovascular_disease`)
- `reason_text`: frase clínica direta para o médico
- `evidence_spans`: trechos do documento de origem

### Exemplos de motivo

- "Recomenda-se negar: paciente com doença cardiovascular relatada e ausência de laudo de ECG no documento."
- "Recomenda-se negar: há sintoma respiratório ativo e não foi identificado laudo de RX tórax."

## Como adaptar no sistema

## Mudanças no LLM1 (extração objetiva)

Extrair apenas campos observáveis no documento, sem inferências de ASA/Mallampati/OSA:

- `indication_category` (ex.: bleeding, abdominal_pain, dyspepsia, foreign_body, gastrostomy, esophageal_dilation, other)
- `age_years`
- `has_cardiovascular_disease` (`yes|no|unknown`)
- `has_active_respiratory_symptoms` (`yes|no|unknown`)
- `has_prior_respiratory_disease` (`yes|no|unknown`)
- `has_decompensated_heart_failure_signs` (`yes|no|unknown`)
- `hb_g_dl`, `platelets_per_mm3`, `inr`
- `has_ecg_report` (`yes|no|unknown`)
- `has_echo_report` (`yes|no|unknown`)
- `has_chest_xray_report` (`yes|no|unknown`)
- `source_evidence[]` (trechos literais)

Regra de prompt: se não houver evidência textual, retornar `unknown`.

## Mudanças na política determinística (domínio)

Adicionar regras de negação explícita por ausência de exame quando há risco relatado:

- cardio + sem ECG -> negar
- respiratório ativo/prévio + sem RX tórax -> negar
- IC descompensada sinalizada + sem avaliação cardíaca mínima -> negar

## Mudanças no relatório/UX

Exibir checklist determinístico:

- Critério acionado
- Evidência encontrada
- Exame ausente que motivou negação
- Mensagem clínica em português claro

## Referências usadas apenas para complementar critérios vagos

- [R1] ASGE. Routine laboratory testing before endoscopic procedures (2014).  
  [PDF](https://www.asge.org/docs/default-source/education/practice_guidelines/doc-2014_routine-laboratory-testing-before-endoscopic-procedures.pdf)
- [R2] ESGE/ESGENA. Non-anesthesiologist administration of propofol for GI endoscopy (2015 update).  
  [PDF](https://www.esge.com/assets/downloads/pdfs/guidelines/2015_s_0034_1393414.pdf)
- [R3] BSG. Guidelines on sedation in gastrointestinal endoscopy (2023).  
  [PDF](https://www.bsg.org.uk/getattachment/dfb6942c-3482-49fe-afc0-1df88891f7fc/BSG-Guidelines-on-Sedation-in-Gastrointestinal-Endoscopy-2023.pdf)
- [R4] NICE NG45. Routine preoperative tests for elective surgery.  
  [Guideline](https://www.nice.org.uk/guidance/ng45)
- [R5] ASA. Practice Advisory for Preanesthesia Evaluation (updated report).  
  [PDF](https://www.asahq.org/~/media/sites/asahq/files/public/resources/standards-guidelines/practice-advisory-for-preanesthesia-evaluation.pdf)

## Conclusão

Sim, é viável unir todo o conteúdo discutido nesta sessão com a mensagem original da equipe CHD, mantendo aderência local e adicionando gates determinísticos objetivos com justificativa explícita.

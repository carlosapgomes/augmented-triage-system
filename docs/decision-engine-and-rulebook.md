# Motor de Decisão e Rulebook

Idioma: **Português (BR)** | [English](en/decision-engine-and-rulebook.md)

## Objetivo

Este documento descreve como o ATS toma decisões ao longo do fluxo de triagem,
com foco em previsibilidade, auditabilidade e evolução segura do rulebook.

A intenção é evitar uma ambiguidade comum: assumir que a decisão clínica vem do
prompt. No ATS, o prompt orienta extração e sugestão, mas as regras críticas do
fluxo automático são determinísticas em código. A decisão clínica final continua
sendo humana, registrada pelo médico na Room-2.

## Princípios do motor de decisão

1. Prompts são contrato de extração e estrutura, não autoridade final de regra.
2. Regras determinísticas são implementadas em políticas e serviços de domínio.
3. Toda saída crítica deve ser auditável com `reason_code`, `reason_text` e,
   quando houver, `evidence_spans`.
4. A decisão médica final permanece humana e explícita na Room-2.
5. Mudanças de rulebook devem preservar compatibilidade com consumidores de
   `suggestion`, sem perder explicabilidade adicional em `preop_gate`.

## Fluxo geral (narrativa)

1. **Coleta e extração inicial**
   - O caso entra via Room-1 com PDF.
   - O worker extrai texto e chama LLM1 para estruturar os dados clínicos.

2. **Gate determinístico de escopo**
   - O sistema avalia `preop_screening.exam_type`.
   - Se `non_eda` ou `unknown`, o caso vai para `manual_review_required`, com
     fechamento operacional na Room-1, auditoria e sem publicação de resumo na
     Room-2.

3. **Sugestão LLM2 e reconciliação**
   - Para casos `eda`, o sistema chama LLM2 para produzir uma sugestão clínica.
   - Em seguida aplica reconciliação determinística para alinhar a sugestão ao
     rulebook vigente.

4. **Gate pré-procedimento determinístico (`preop_gate`)**
   - A política EDA determinística calcula um bloco explicável com `decision`,
     `reason_code`, `reason_text`, `evidence_spans` e `pediatric_flag`.
   - Esse bloco é persistido em `suggested_action_json.preop_gate`.

5. **Síntese de ASA prático e suporte**
   - O sistema deriva `ASA estimado` prático (`I-II`, `III ou mais` ou fallback
     por dados insuficientes).
   - A mesma síntese define o suporte recomendado (`none`, `anesthesist` ou
     `anesthesist_icu`).

6. **Publicação para revisão médica na Room-2**
   - Apenas casos elegíveis são publicados com resumo técnico, contexto do
     procedimento e template estrito de resposta.

7. **Decisão médica e finalização**
   - O médico responde via mensagem estruturada na Room-2.
   - O sistema valida o contrato, aplica transições de estado e executa os jobs
     de finalização nas demais salas.

## Fluxo geral (tabela)

| Etapa | Entrada | Componente principal | Saída principal |
| --- | --- | --- | --- |
| Intake + extração | PDF Room-1 | `process_pdf_case_service` + LLM1 | `structured_data_json` |
| Gate de escopo | `structured_data_json.preop_screening.exam_type` | `process_pdf_case_service` | `manual_review_required` (para `non_eda\|unknown`) |
| Sugestão clínica | `structured_data_json` (EDA suportada) | `llm2_service` | `suggested_action_json.suggestion` |
| Gate determinístico EDA | `structured_data_json` | `domain/policy/eda_preop_policy.py` | `preop_gate` explicável |
| Síntese de ASA/suporte | `structured_data_json` | `domain/policy/eda_recommendation_synthesis.py` | `asa` + `support_recommendation` |
| Revisão médica Room-2 | mensagem I/II/III + template | `post_room2_widget_service` + `room2_reply_service` | decisão médica aplicada |
| Encerramento operacional | decisão humana + estado | serviços finais/jobs | resposta final + auditoria + cleanup |

## Domínio EDA suportado

O rulebook reescrito abandona a divisão legada entre EDA “operacional” e “não
operacional” como eixo principal da decisão automática. Agora o fluxo suporta um
único domínio clínico EDA com subtipos explícitos e critérios locais do CHD.

### Subtipos suportados dentro do fluxo automático

| Subtipo | Descrição | Comportamento no fluxo |
| --- | --- | --- |
| `standard` | EDA padrão | segue regra completa |
| `gastrostomy` | EDA para gastrostomia | segue a mesma regra mínima de `standard` |
| `esophageal_dilation` | EDA para dilatação esofágica | segue a mesma regra mínima de `standard` |
| `foreign_body` | EDA para retirada de corpo estranho | bypass de exames mínimos e gates condicionais |

### Escopo não suportado

- `non_eda`: revisão manual obrigatória.
- `unknown`: revisão manual obrigatória.

## Rulebook EDA reescrito

A política determinística segue a prioridade abaixo.

### 1. Gate de escopo

| Prioridade | Condição | Saída | `reason_code` |
| --- | --- | --- | --- |
| 0 | `exam_type = non_eda` | `manual_review_required` | `non_eda_request` |
| 0 | `exam_type = unknown` | `manual_review_required` | `unknown_exam_type` |

### 2. Exceção de corpo estranho

| Prioridade | Condição | Saída | `reason_code` |
| --- | --- | --- | --- |
| 1 | subtipo `foreign_body` | `accept` | `foreign_body_exception` |

Para `foreign_body`, o sistema faz bypass de:

- exames mínimos obrigatórios;
- gates condicionais de ECG, RX de tórax e ecocardiograma.

Ainda assim, o caso pode receber recomendação de suporte com base no restante do
contexto clínico e no ASA prático.

### 3. Exames mínimos obrigatórios

Para `standard`, `gastrostomy` e `esophageal_dilation`, o aceite automático só é
possível quando há evidência mínima de:

- `Hb/Ht`;
- plaquetas;
- `TP|INR|RNI` com evidência numérica;
- `TTPa`;
- ureia;
- creatinina.

#### Regras de evidência

- `Hb` isolada satisfaz o requisito `Hb/Ht`.
- Textos genéricos como `hemograma normal`, `coagulograma sem alterações` ou
  `exames laboratoriais sem alterações` **não** satisfazem os requisitos
  numéricos de Hb, plaquetas ou `TP|INR|RNI`.
- Evidência qualitativa pode satisfazer:
  - `TTPa` quando houver texto como `TTPa normal`;
  - ureia e creatinina quando houver `função renal preservada` ou equivalente;
  - `coagulograma normal` satisfaz `TTPa` apenas se `TP|INR|RNI` já estiver
    documentado com valor numérico.

#### `reason_code` de exames mínimos

| Falha | `reason_code` |
| --- | --- |
| Hb/Ht ausente | `missing_minimum_exam_hb_or_ht` |
| Plaquetas ausentes | `missing_minimum_exam_platelets` |
| TP/INR/RNI ausente | `missing_minimum_exam_tp_inr_rni` |
| TTPa ausente | `missing_minimum_exam_ttpa` |
| Ureia ausente | `missing_minimum_exam_urea` |
| Creatinina ausente | `missing_minimum_exam_creatinine` |

### 4. Limiares de contraindicação

Quando os exames mínimos estão presentes, o sistema aplica limiares de negação
conforme o perfil clínico explicitamente documentado.

| Perfil clínico | Hb | Plaquetas | RNI/INR |
| --- | --- | --- | --- |
| Geral (sem hepatopatia/cardiopatia explícitas) | `< 7` | `< 100000` | `> 1.5` |
| Hepatopatia explícita | `< 7` | `< 50000` | `> 1.5` |
| Cardiopatia explícita | `< 8` | `< 100000` | `> 1.5` |
| Hepatopatia + cardiopatia explícitas | `< 8` | `< 50000` | `> 1.5` |

#### `reason_code` de contraindicação

| Falha | `reason_code` |
| --- | --- |
| Hb abaixo do limiar | `hb_below_threshold` |
| Plaquetas abaixo do limiar | `platelets_below_threshold` |
| INR/RNI acima do limiar | `inr_above_threshold` |

## Gates condicionais de completude cardiorrespiratória

Após os exames mínimos e antes do aceite, o rulebook exige laudo mínimo quando
certos gatilhos clínicos estiverem presentes.

### ECG

ECG com achado minimamente reportável é obrigatório se houver pelo menos um dos
seguintes sinais:

- idade acima de 40 anos;
- doença cardiovascular conhecida;
- dor torácica recente;
- dispneia recente;
- palpitações;
- síncope;
- múltiplas comorbidades;
- uso de medicações que prolongam QT;
- diabetes mellitus;
- obesidade explícita.

Se o critério existe e só há menção de existência do exame, sem laudo mínimo,
a decisão é `deny` com:

- `reason_code`: `missing_ecg_with_cardiovascular_disease`.

### RX de tórax

RX de tórax com achado minimamente reportável é obrigatório se houver:

- sintomas respiratórios ativos; ou
- doença respiratória prévia.

Se faltar laudo mínimo, a decisão é `deny` com:

- `reason_code`: `missing_chest_xray_with_respiratory_risk`.

### Ecocardiograma

Ecocardiograma com achado minimamente reportável é obrigatório se houver:

- dispneia inexplicada;
- sinais de insuficiência cardíaca;
- sopro novo ou não avaliado;
- valvulopatia moderada/grave sem eco recente;
- cardiomiopatia em piora;
- hipertensão pulmonar;
- IAM prévio;
- cirurgia de revascularização prévia;
- angioplastia coronária prévia.

Se faltar laudo mínimo, a decisão é `deny` com:

- `reason_code`: `missing_echocardiogram_with_structural_heart_risk`.

### Observações de completude

- Mencionar que o exame “existe” ou foi “solicitado” não satisfaz a regra.
- O laudo precisa trazer achado mínimo reportável, por exemplo `ECG sem
  alterações` ou `RX de tórax normal`.
- Suspeita isolada, sem evidência clínica explícita, não cria gatilho duro para
  os gates condicionais.

## Sinalização pediátrica

Casos com idade abaixo de 16 anos são marcados explicitamente como pediátricos.
Esse sinal é preservado para consumidores downstream e aparece na Room-2 como:

- `paciente pediátrico: sim`.

## ASA prático e semântica de suporte

O sistema deriva um ASA prático conservador e independente da decisão final.
Esse valor é apresentado na Room-2 e também direciona a recomendação de suporte.

### Buckets de ASA prático

| Valor persistido | Exibição |
| --- | --- |
| `I-II` | `I-II` |
| `III ou mais` | `III ou mais` |
| `insufficient_data` | `não foi possível estimar com os dados apresentados` |

### Mapeamento de suporte

| Contexto | `support_recommendation` | Interpretação prática |
| --- | --- | --- |
| ASA prático `I-II` e sem alto risco cardiovascular | `none` | sedação pelo endoscopista, sem suporte adicional obrigatório |
| ASA prático `III ou mais` | `anesthesist` | necessidade mínima de anestesista |
| ASA prático + risco cardiovascular `moderate_high` | `anesthesist_icu` | suporte anestésico com contexto compatível com UTI |
| ASA insuficiente, sem sinais que escalem suporte | derivado do restante da evidência confirmada | fallback conservador sem inventar classe ASA formal |

## Saída auditável persistida

Para casos EDA suportados, a persistência precisa manter contexto suficiente
para recomendação, auditoria e Room-2.

### Campos clínicos mínimos esperados

- `suggestion`;
- `decision`;
- `reason_code`;
- `reason_text`;
- `support_recommendation`;
- `asa.bucket` e `asa.display_text`;
- `preop_gate.decision`;
- `preop_gate.reason_code`;
- `preop_gate.reason_text`;
- `preop_gate.evidence_spans`;
- sinalização de subtipo e pediatria no contexto estruturado.

## Renderização da Room-2

A mensagem técnica da Room-2 agora segue um layout fixo de sete blocos:

1. `Resumo clínico`
2. `Achados críticos`
3. `Pendências críticas`
4. `Decisão sugerida`
5. `Suporte recomendado`
6. `ASA estimado`
7. `Motivo objetivo`

### Regras de texto objetivo

- Em `accept`, o motivo deve ser curto e alinhado ao suporte.
- Em `deny`, o motivo deve listar causas objetivas do rulebook reescrito.
- A prioridade do motivo objetivo em `deny` é:
  1. exame mínimo obrigatório ausente;
  2. laudo mínimo ausente em ECG/RX/ECO quando aplicável;
  3. contraindicação por limiar excedido;
  4. causa defensiva de segurança.
- Se houver mais de duas causas objetivas, a Room-2 mostra no máximo duas e
  adiciona marcador compacto equivalente a `e outras pendências críticas`.
- O resumo também explicita:
  - procedimento canônico do subtipo suportado;
  - marcador pediátrico quando aplicável;
  - `ASA estimado` em bloco próprio.

## Catálogo prático de `reason_code`

| `reason_code` | Significado operacional | Consumidor principal |
| --- | --- | --- |
| `non_eda_request` | Escopo não EDA: revisão manual obrigatória | runtime + Room-1 final |
| `unknown_exam_type` | Tipo de exame indefinido: revisão manual obrigatória | runtime + Room-1 final |
| `foreign_body_exception` | Exceção de corpo estranho com bypass de gates mínimos | `preop_gate` + síntese final |
| `missing_minimum_exam_hb_or_ht` | Hb/Ht mínimo ausente | `preop_gate` + Room-2 |
| `missing_minimum_exam_platelets` | Plaquetas mínimas ausentes | `preop_gate` + Room-2 |
| `missing_minimum_exam_tp_inr_rni` | TP/INR/RNI mínimo ausente | `preop_gate` + Room-2 |
| `missing_minimum_exam_ttpa` | TTPa mínimo ausente | `preop_gate` + Room-2 |
| `missing_minimum_exam_urea` | Ureia mínima ausente | `preop_gate` + Room-2 |
| `missing_minimum_exam_creatinine` | Creatinina mínima ausente | `preop_gate` + Room-2 |
| `missing_ecg_with_cardiovascular_disease` | Gate cardiovascular sem laudo mínimo de ECG | `preop_gate` + Room-2 |
| `missing_chest_xray_with_respiratory_risk` | Gate respiratório sem laudo mínimo de RX de tórax | `preop_gate` + Room-2 |
| `missing_echocardiogram_with_structural_heart_risk` | Gate estrutural cardíaco sem laudo mínimo de ECO | `preop_gate` + Room-2 |
| `hb_below_threshold` | Hb abaixo do limiar aplicável ao perfil | `preop_gate` + Room-2 |
| `platelets_below_threshold` | Plaquetas abaixo do limiar aplicável ao perfil | `preop_gate` + Room-2 |
| `inr_above_threshold` | INR/RNI acima do limiar aplicável ao perfil | `preop_gate` + Room-2 |
| `criteria_met` | Critérios determinísticos atendidos | `preop_gate` |
| `manual_review_required_insufficient_data` | Fallback defensivo para payload incompleto | serialização `preop_gate` |

## Mapa de extensão de regras (onde mexer)

| Mudança desejada | Arquivo principal | Testes mínimos esperados |
| --- | --- | --- |
| Novo exame mínimo, gate condicional ou limiar EDA | `src/triage_automation/domain/policy/eda_preop_policy.py` | `tests/unit/test_eda_preop_policy.py` |
| Alterar síntese de ASA prático ou suporte | `src/triage_automation/domain/policy/eda_recommendation_synthesis.py` | `tests/unit/test_eda_recommendation_synthesis.py` |
| Alterar roteamento de escopo (`non_eda\|unknown`) | `src/triage_automation/application/services/process_pdf_case_service.py` | `tests/integration/test_process_pdf_case_llm2.py` |
| Alterar texto objetivo, ASA ou contexto do resumo Room-2 | `src/triage_automation/infrastructure/matrix/message_templates.py` | `tests/unit/test_room2_message_templates.py` + `tests/integration/test_post_room2_widget.py` |
| Alterar parser/contrato de decisão médica Room-2 | `src/triage_automation/domain/doctor_decision_parser.py` | testes unitários do parser + integração de reply |

## Onde as regras vivem no código

- Orquestração do pipeline:
  `src/triage_automation/application/services/process_pdf_case_service.py`
- Política determinística EDA (`preop_gate`):
  `src/triage_automation/domain/policy/eda_preop_policy.py`
- Síntese de ASA prático e suporte:
  `src/triage_automation/domain/policy/eda_recommendation_synthesis.py`
- Publicação e renderização da Room-2:
  `src/triage_automation/application/services/post_room2_widget_service.py`
  e `src/triage_automation/infrastructure/matrix/message_templates.py`
- Captura de decisão médica (Room-2):
  `src/triage_automation/application/services/room2_reply_service.py` e
  `src/triage_automation/application/services/handle_doctor_decision_service.py`

## Playbook de evolução de regras (add/remove/change)

### Fluxo recomendado por mudança

1. **Defina o impacto funcional antes de codificar**
   - Atualize OpenSpec quando houver mudança de contrato, precedência, novo
     subtipo suportado, novo `reason_code` ou mudança de semântica do suporte.
   - Declare explicitamente se a mudança afeta apenas EDA ou o motor geral.

2. **Escreva testes RED primeiro**
   - Política determinística: testes unitários no módulo de policy.
   - Orquestração/runtime: testes de integração para estado, jobs e auditoria.
   - Mensagens/UX: testes de template e integração de publicação na Room-2.

3. **Implemente no módulo certo**
   - Regra clínica determinística: `eda_preop_policy.py`.
   - Síntese de ASA/suporte: `eda_recommendation_synthesis.py`.
   - Gate de escopo: `process_pdf_case_service.py`.
   - Texto para revisão médica: `message_templates.py`.

4. **Garanta explicabilidade e compatibilidade**
   - Preserve `reason_code`, `reason_text` e `evidence_spans`.
   - Preserve `suggestion` legada e mantenha `preop_gate` como bloco explicável.

5. **Atualize documentação operacional**
   - Atualize este rulebook e o espelho em inglês.
   - Atualize runbook manual quando o comportamento observado na Room-2 ou no
     fechamento operacional mudar.

6. **Rode validações e registre evidência**
   - Execute lint/testes aplicáveis e registre comandos/resultados no `tasks.md`
     do change correspondente.

### Checklist anti-regressão (obrigatório)

- [ ] A regra continua determinística em código.
- [ ] Novos `reason_code` estão documentados e mapeados nos consumidores.
- [ ] `preop_gate` permanece serializado sem quebrar consumidores de
  `suggestion`.
- [ ] Casos `non_eda|unknown` continuam sem `accept|deny` automático.
- [ ] `foreign_body` continua em fluxo EDA suportado com bypass explícito.
- [ ] Room-2 continua explicitando subtipo, ASA e contexto pediátrico quando
  aplicável.

### Comandos mínimos de validação

```bash
uv run pytest tests/unit/test_eda_preop_policy.py tests/unit/test_eda_recommendation_synthesis.py tests/integration/test_process_pdf_case_llm2.py tests/integration/test_post_room2_widget.py tests/unit/test_room2_message_templates.py -q
uv run ruff check src/triage_automation/domain/policy/eda_preop_policy.py src/triage_automation/domain/policy/eda_recommendation_synthesis.py src/triage_automation/application/services/process_pdf_case_service.py src/triage_automation/infrastructure/matrix/message_templates.py
uv run mypy src/triage_automation/domain/policy/eda_preop_policy.py src/triage_automation/domain/policy/eda_recommendation_synthesis.py src/triage_automation/application/services/process_pdf_case_service.py src/triage_automation/infrastructure/matrix/message_templates.py
markdownlint-cli2 "docs/decision-engine-and-rulebook.md" "docs/en/decision-engine-and-rulebook.md"
```

## Referências

- `docs/manual_e2e_runbook.md`
- `openspec/changes/eda-decision-rulebook-rewrite/specs/eda-preop-deterministic-criteria/spec.md`
- `openspec/changes/eda-decision-rulebook-rewrite/specs/room2-concise-medical-opinion-message/spec.md`

# EDA decision rulebook rewrite proposal

## Why

O rulebook atual de recomendação para EDA deixou de refletir a diretriz clínica desejada: ele ainda depende de distinções herdadas (como EDA “operacional” vs. “não operacional”), exclui gastrostomia e dilatação antes da Sala 2, não cobre adequadamente os novos exames mínimos e não contempla estimativa prática de ASA. Isso gera desalinhamento entre a automação e a forma como a equipe quer raciocinar o caso clínico antes da decisão médica.

A mudança é necessária agora para substituir integralmente a lógica atual por um novo rulebook que preserve o papel do sistema como recomendador explicável, mantenha o médico da Sala 2 como autoridade final e prepare a base clínica para mudanças operacionais posteriores sem misturar, neste primeiro change, o novo fluxo de `vinda_imediata` ou os ajustes de dashboard.

## What Changes

- **BREAKING**: substituir integralmente o rulebook atual de recomendação EDA por um novo conjunto de regras clínicas e semânticas, removendo a distinção herdada entre EDA “operacional” e “não operacional” e aposentando os limiares antigos que não correspondem mais à decisão desejada.
- Redefinir o escopo automático suportado para incluir:
  - EDA padrão;
  - EDA para gastrostomia;
  - EDA para dilatação esofágica;
  - EDA para retirada de corpo estranho;
  - mantendo `non_eda` e `unknown` como revisão manual obrigatória fora da Sala 2.
- Reescrever os critérios clínicos de recomendação para EDA com base no novo rulebook consolidado:
  - exames mínimos obrigatórios (`Hb/Ht`, plaquetas, `TP/INR/RNI`, `TTPa`, ureia, creatinina);
  - critérios condicionais de RX de tórax, ECG e ecocardiograma com exigência de laudo mínimo no relatório;
  - matriz de contraindicação para hepatopata, cardiopata, demais pacientes e combinação hepatopata + cardiopata;
  - regra explícita de bypass completo para corpo estranho.
- Formalizar semântica de evidência clínica suficiente vs. insuficiente:
  - valores numéricos obrigatórios para critérios com limiares de contraindicação;
  - aceitação de evidência qualitativa apenas onde foi explicitamente autorizado (`TTPa`, função renal/ureia/creatinina, `coagulograma normal` condicionado ao critério numérico de `TP` já satisfeito);
  - sugestão de `negar` quando faltar exame mínimo aplicável, sem impedir a decisão final do médico.
- Introduzir estimativa prática e conservadora de ASA para uso na recomendação clínica:
  - `I-II`;
  - `III ou mais`;
  - `não foi possível estimar com os dados apresentados`.
- Recalibrar a recomendação de suporte com base no novo modelo clínico:
  - `nenhum`;
  - `anestesista`;
  - `anestesista_uti`;
  - permitindo recomendação de suporte mesmo no cenário de corpo estranho, embora sem exigir exames mínimos.
- Atualizar o resumo técnico da Sala 2 para refletir o novo rulebook:
  - exibir ASA estimado em bloco explícito;
  - mostrar causas objetivas de recomendação coerentes com os novos exames e contraindicações;
  - propagar corretamente o procedimento solicitado e o marcador `paciente pediátrico: sim`;
  - destacar incerteza clínica sem presumir critério não comprovado.
- Atualizar a documentação funcional e operacional do sistema como parte deste change, incluindo:
  - rulebook/documentação de decisão;
  - runbook manual E2E;
  - sincronização dos arquivos espelho obrigatórios em inglês sob `docs/en/` quando `docs/` for alterado.
- Delimitar explicitamente que este change **não** altera ainda:
  - o contrato estruturado da resposta médica da Sala 2;
  - o fluxo operacional de `vinda_imediata`;
  - outcomes, filtros e métricas de dashboard/Room-4 relacionados a `VINDA_IMEDIATA`.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `eda-preop-deterministic-criteria`: substitui os critérios determinísticos atuais por um novo rulebook clínico para EDA, incluindo exames mínimos obrigatórios, critérios condicionais de RX/ECG/ECO, exceção de corpo estranho, nova matriz de contraindicação e saída explicável alinhada ao novo comportamento esperado.
- `eda-request-scope-gating`: altera a classificação de escopo para tratar gastrostomia, dilatação esofágica e retirada de corpo estranho como subtipos suportados do fluxo EDA, mantendo `non_eda` e `unknown` em revisão manual obrigatória.
- `room2-concise-medical-opinion-message`: atualiza o resumo técnico da Sala 2 para refletir o novo rulebook, incluindo contexto de procedimento solicitado, sinalização pediátrica, bloco explícito de ASA estimado e novos motivos objetivos coerentes com a recomendação.
- `manual-e2e-readiness`: atualiza as validações manuais e o runbook operacional para cobrir o novo rulebook EDA, os novos casos suportados no fluxo automático e os novos critérios de evidência clínica/documental.

## Impact

- Código potencialmente afetado:
  - `src/triage_automation/application/dto/llm1_models.py`
  - `src/triage_automation/application/services/llm1_service.py`
  - `src/triage_automation/application/services/llm2_service.py`
  - `src/triage_automation/domain/policy/eda_preop_policy.py`
  - `src/triage_automation/domain/policy/eda_policy.py`
  - `src/triage_automation/application/services/process_pdf_case_service.py`
  - `src/triage_automation/application/services/post_room2_widget_service.py`
  - `src/triage_automation/application/services/patient_context.py`
  - `src/triage_automation/infrastructure/matrix/message_templates.py`
- Testes e validação potencialmente afetados:
  - políticas determinísticas e reconciliação da recomendação EDA;
  - publicação do resumo da Sala 2;
  - classificação de escopo e roteamento para revisão manual;
  - smoke/manual E2E para os novos cenários clínicos.
- Documentação potencialmente afetada:
  - `docs/decision-engine-and-rulebook.md`
  - `docs/en/decision-engine-and-rulebook.md`
  - `docs/manual_e2e_runbook.md`
  - `docs/en/manual_e2e_runbook.md`
- Dependências e operação:
  - pode exigir revisão do papel relativo entre LLM1, LLM2 e regras determinísticas para sustentar o novo rulebook, mas sem assumir, neste proposal, uma simplificação arquitetural obrigatória;
  - não introduz novas integrações externas;
  - não muda ainda o contrato da decisão médica estruturada, o fluxo de `vinda_imediata` nem os desfechos agregados de dashboard.

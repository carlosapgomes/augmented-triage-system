# EDA decision rulebook rewrite design

## Context

O fluxo atual de triagem EDA foi construído em camadas sucessivas de regra: extração via
LLM1, sugestão via LLM2, reconciliação determinística, gate de escopo e mensagens para
Sala 2. Essa base já oferece explicabilidade parcial, mas o rulebook atualmente codificado
não corresponde mais à política clínica desejada.

Os principais desalinhamentos do estado atual são:

- distinção herdada entre EDA “operacional” e “não operacional”, que deve ser removida;
- exclusão precoce de `gastrostomia` e `dilatação esofágica`, que agora devem seguir para
  avaliação médica na Sala 2 como subtipos suportados do fluxo EDA;
- tratamento parcial de `corpo estranho`, que precisa virar exceção explícita de bypass
  completo dos exames mínimos e dos exames adicionais condicionais;
- ausência de suporte formal para o novo conjunto de exames mínimos (`TTPa`, ureia,
  creatinina e equivalências qualitativas permitidas);
- ausência de estimativa prática de ASA, agora desejada como componente do resumo clínico
  e da recomendação de suporte;
- resumo da Sala 2 ainda modelado em torno de causas e precedências do rulebook antigo.

Ao mesmo tempo, há restrições importantes já definidas:

- o médico da Sala 2 continua sendo a autoridade final da decisão;
- este change não deve introduzir ainda o novo contrato de resposta médica da Sala 2 nem
  o fluxo operacional de `vinda_imediata`;
- `non_eda` e `unknown` continuam fora do fluxo automático, com revisão manual na Sala 1;
- mudanças em `docs/` exigem atualização síncrona dos espelhos em `docs/en/`;
- a arquitetura deve continuar priorizando comportamento determinístico quando a regra for
  objetivamente codificável, usando LLM apenas onde interpretação semântica for realmente
  necessária.

Stakeholders principais:

- equipe clínica CHD, que define o novo rulebook;
- médicos que consomem o resumo da Sala 2;
- operação, que depende de mensagens explicáveis e runbook claro;
- manutenção futura dos proposals 2 e 3, que dependerão deste change como base clínica.

## Goals / Non-Goals

**Goals:**

- Substituir integralmente o rulebook clínico atual de recomendação EDA.
- Reclassificar o escopo suportado para incluir EDA padrão, gastrostomia, dilatação
  esofágica e retirada de corpo estranho.
- Formalizar exames mínimos obrigatórios, critérios condicionais de RX/ECG/ECO e matriz de
  contraindicação conforme as decisões consolidadas.
- Tratar evidência suficiente e insuficiente de forma explícita, inclusive com regras de
  equivalência qualitativa autorizadas.
- Introduzir estimativa prática e conservadora de ASA sem alterar ainda o contrato da
  resposta médica da Sala 2.
- Recalibrar a recomendação de suporte (`nenhum`, `anestesista`, `anestesista_uti`) com
  base no novo rulebook e na estimativa ASA.
- Atualizar o resumo técnico da Sala 2 para mostrar ASA estimado, contexto pediátrico,
  procedimento solicitado e motivos coerentes com o novo comportamento.
- Atualizar documentação funcional e operacional do sistema, incluindo os espelhos em
  inglês sob `docs/en/`.

**Non-Goals:**

- Implementar o novo campo `fluxo de admissão` na resposta médica da Sala 2.
- Implementar o fluxo operacional de `vinda_imediata`.
- Alterar state machine e outcomes agregados para suportar `VINDA_IMEDIATA`.
- Mudar dashboard, filtros, métricas da Sala 4 ou queries agregadas de desfecho.
- Introduzir compatibilidade com contratos futuros ainda não implementados.
- Redesenhar o produto para abandonar necessariamente o LLM2 neste change.

## Decisions

### Decision 1: Preservar o pipeline atual, mas substituir o rulebook clínico interno

- **Escolha:** manter a arquitetura geral `LLM1 -> LLM2 -> reconciliação/política -> Sala 2`,
  substituindo o conteúdo do rulebook e o contrato interno dos sinais clínicos usados na
  recomendação.
- **Racional:** o objetivo primário não é simplificar arquitetura, e sim substituir a regra
  clínica sem introduzir mudança operacional desnecessária no mesmo change. Manter o
  pipeline reduz risco de regressão no fluxo entre salas e permite concentrar este change
  na camada clínica.
- **Alternativas consideradas:**
  - remover o LLM2 já neste proposal;
  - mover toda decisão para uma política determinística única sem etapa semântica.
- **Motivo da rejeição:** a nova regra ainda depende de interpretação semântica em pontos
  como `múltiplas comorbidades`, ASA prático e algumas leituras contextuais. Forçar uma
  simplificação arquitetural neste momento misturaria problemas demais em um único change.

### Decision 2: Reposicionar `gastrostomia`, `dilatação esofágica` e `corpo estranho` como subtipos suportados de EDA

- **Escolha:** tratar os três casos como parte do escopo automático suportado do fluxo EDA,
  com semânticas clínicas distintas.
- **Comportamento:**
  - `gastrostomia` e `dilatação esofágica` passam a seguir as mesmas regras da EDA padrão;
  - `corpo estranho` segue para a Sala 2, mas com bypass completo de exames mínimos e
    exames adicionais condicionais.
- **Racional:** isso resolve o principal desacoplamento entre o comportamento atual do código
  e a decisão clínica desejada, sem antecipar ainda o fluxo futuro de `vinda_imediata`.
- **Alternativas consideradas:**
  - manter gastrostomia/dilatação fora do fluxo e tratá-las em Proposal 2;
  - tratar `corpo estranho` apenas como exceção de mensagens.
- **Motivo da rejeição:** o escopo suportado e a semântica clínica desses casos são parte do
  rulebook e precisam ser resolvidos antes do proposal operacional.

### Decision 3: Redesenhar o contrato de extração do LLM1 para capturar o novo rulebook, inclusive ASA prático

- **Escolha:** expandir o schema do LLM1 com sinais suficientes para sustentar o novo
  rulebook e incorporar um campo explícito de estimativa prática de ASA ou equivalente
  estruturado para `I-II`, `III ou mais` e `insufficient_data`.
- **Racional:** o estado atual do LLM1 explicitamente proíbe estimativa de ASA e não coleta
  vários sinais agora necessários. Como este change já altera o rulebook clínico, ele deve
  alinhar o contrato de extração para reduzir heurísticas frágeis espalhadas no backend.
- **Alternativas consideradas:**
  - manter o schema atual e derivar tudo por inspeção textual ad hoc no backend;
  - calcular ASA apenas no LLM2 sem qualquer materialização no payload do LLM1.
- **Motivo da rejeição:** a primeira opção espalha lógica semântica difícil de testar; a
  segunda enfraquece auditabilidade e torna a UI dependente de texto livre. O desenho mais
  robusto é capturar explicitamente os sinais e a estimativa prática no contrato estruturado.

### Decision 4: Dividir a nova política clínica em três blocos de responsabilidade

- **Escolha:** separar internamente a lógica em três responsabilidades, ainda dentro do
  Proposal 1:
  1. **classificação de escopo e subtipo EDA**;
  2. **avaliação determinística de exames mínimos, exames adicionais e contraindicações**;
  3. **síntese de recomendação clínica e suporte**, usando ASA estimado + sinais objetivos.
- **Racional:** isso evita concentrar toda a complexidade em um único módulo e preserva a
  direção arquitetural do repositório. Também facilita testes unitários mais focalizados.
- **Alternativas consideradas:**
  - manter tudo em `eda_preop_policy.py`;
  - empurrar a síntese inteira para `llm2_service`.
- **Motivo da rejeição:** a primeira opção tornaria a política opaca e difícil de evoluir;
  a segunda reduziria controle determinístico justamente no momento em que o rulebook está
  sendo endurecido.

### Decision 5: Tratar ausência de exame aplicável como causa de recomendação negativa, não como bloqueio pré-médico

- **Escolha:** quando faltar exame mínimo ou exame adicional aplicável, o sistema deve
  sugerir `deny`, registrar causa explícita e ainda encaminhar o caso à Sala 2.
- **Racional:** isso preserva a decisão final do médico e mantém a distinção entre
  recomendação automática e decisão humana.
- **Alternativas consideradas:**
  - negar automaticamente antes da Sala 2;
  - converter faltas de exame em `manual_review_required`.
- **Motivo da rejeição:** a primeira elimina a autoridade final do médico; a segunda perde
  o valor clínico da recomendação objetiva que a equipe explicitamente quer ver na Sala 2.

### Decision 6: Codificar evidência suficiente por tipo de exame, com equivalências qualitativas somente onde foram autorizadas

- **Escolha:** estabelecer uma matriz explícita de evidência aceita:
  - `Hb`, plaquetas e `TP/INR/RNI` exigem valor numérico;
  - `TTPa`, ureia e creatinina admitem evidência qualitativa autorizada;
  - `função renal preservada` supre ureia + creatinina;
  - `coagulograma normal` supre `TTPa` apenas se o critério numérico de `TP/INR/RNI` já
    estiver satisfeito;
  - frases genéricas como `exames laboratoriais sem alterações` não suprem os mínimos.
- **Racional:** isso reduz ambiguidades na implementação e evita regressão para texto
  genérico que enfraqueça a segurança clínica.
- **Alternativas consideradas:**
  - tratar qualquer texto qualitativo como suficiente para todos os exames;
  - exigir número para absolutamente todos os mínimos.
- **Motivo da rejeição:** a primeira flexibiliza demais; a segunda conflita com a decisão
  clínica já tomada para TTPa e função renal.

### Decision 7: Manter `non_eda` e `unknown` em revisão manual, mas alterar o gate para não excluir subtipos suportados de EDA

- **Escolha:** ajustar o gate de escopo para deixar de tratar `gastrostomia` e
  `dilatação esofágica` como exclusões finais, mantendo apenas casos realmente não-EDA ou
  indefinidos como `manual_review_required`.
- **Racional:** o Proposal 1 precisa corrigir o principal erro de escopo sem tocar ainda no
  fluxo operacional posterior.
- **Alternativas consideradas:**
  - manter o gate atual e apenas maquiar mensagens;
  - tratar subtipos suportados como `manual_review_required` temporariamente.
- **Motivo da rejeição:** ambos manteriam desalinhamento clínico já explicitamente rejeitado.

### Decision 8: Manter a recomendação de suporte em três valores e derivá-la de ASA + contexto de risco

- **Escolha:** preservar os três valores atuais de suporte:
  - `none`
  - `anesthesist`
  - `anesthesist_icu`
- **Mapeamento clínico desejado:**
  - `ASA I-II` -> `none`
  - `ASA III ou mais` -> `anesthesist`
  - risco cardiovascular moderado/alto derivado da própria avaliação ASA/contexto ->
    `anesthesist_icu`
- **Racional:** preserva compatibilidade com o restante do sistema enquanto atualiza a base
  clínica da recomendação.
- **Alternativas consideradas:**
  - ampliar enum de suporte já neste change;
  - deixar suporte inteiramente a cargo do médico.
- **Motivo da rejeição:** a primeira mistura Proposal 1 com mudanças de contrato futuro; a
  segunda reduz o valor da recomendação clínica que continua sendo desejada.

### Decision 9: Inserir ASA estimado como bloco explícito no resumo da Sala 2

- **Escolha:** adicionar bloco `ASA estimado` explicitamente no resumo da Sala 2, entre
  `Suporte recomendado` e `Motivo objetivo`.
- **Racional:** evita diluir ASA dentro de justificativas textuais e reduz a chance de a
  informação desaparecer em truncamentos ou resumos livres.
- **Alternativas consideradas:**
  - embutir ASA em `Achados críticos`;
  - embutir ASA em `Motivo objetivo`.
- **Motivo da rejeição:** ambas misturam níveis semânticos distintos e prejudicam leitura
  rápida pelo médico.

### Decision 10: Reorganizar o contexto apresentado nas mensagens da Sala 2 sem antecipar o novo contrato da resposta médica

- **Escolha:** atualizar apenas o conteúdo do resumo e do contexto de identificação para
  refletir:
  - procedimento solicitado canônico;
  - `paciente pediátrico: sim` quando aplicável;
  - exceção de corpo estranho;
  - novo ASA e suporte recomendado.
- **Racional:** Proposal 1 deve preparar a leitura médica do caso sem tocar ainda no parser
  da decisão humana, que pertence ao Proposal 2.
- **Alternativas consideradas:**
  - já alterar também o template de resposta médica.
- **Motivo da rejeição:** misturaria rulebook clínico com fluxo operacional e dificultaria
  validar regressões por etapa.

### Decision 11: Atualizar documentação do produto no mesmo change

- **Escolha:** incluir explicitamente no plano técnico a atualização de:
  - `docs/decision-engine-and-rulebook.md`
  - `docs/en/decision-engine-and-rulebook.md`
  - `docs/manual_e2e_runbook.md`
  - `docs/en/manual_e2e_runbook.md`
- **Racional:** a mudança altera comportamento observável do sistema, critérios clínicos e
  validações operacionais. Deixar a documentação para depois aumentaria risco de drift.
- **Alternativas consideradas:**
  - documentar apenas em OpenSpec;
  - empurrar documentação de produto para um change posterior.
- **Motivo da rejeição:** a governança do repositório exige sincronia de documentação e o
  runbook manual precisa refletir o novo comportamento antes das próximas fases.

## Risks / Trade-offs

- **[Risco]** O novo schema do LLM1 pode exigir revisão significativa de prompts, validação
  e adaptadores determinísticos de teste.  
  **Mitigação:** introduzir o novo contrato com cobertura unitária/integrada direcionada e
  manter payloads explicitamente versionados/validados.

- **[Risco]** Parte da lógica hoje dividida entre `eda_preop_policy` e `eda_policy` pode
  ficar semanticamente duplicada durante a transição.  
  **Mitigação:** definir fronteira clara entre política de elegibilidade clínica,
  recomendação de suporte/ASA e reconciliação final, com testes focados por módulo.

- **[Risco]** A estimativa de ASA via LLM pode introduzir variabilidade indesejada se o
  prompt ficar frouxo.  
  **Mitigação:** limitar a saída a buckets conservadores, exigir justificativa/evidência
  observável e cobrir com fixtures representativas nos testes de integração do pipeline.

- **[Risco]** A inclusão de gastrostomia, dilatação e corpo estranho no escopo automático
  pode alterar taxa de publicação na Sala 2 e surpreender operação.  
  **Mitigação:** atualizar runbook e mensagem/resumo para deixar o subtipo explícito,
  reduzindo ambiguidade operacional.

- **[Risco]** O resumo da Sala 2 pode crescer demais ao incluir ASA, subtipo e novas causas.
  
  **Mitigação:** preservar estrutura concisa, priorizar blocos fixos e limitar a listagem de
  causas objetivas à seleção mais crítica.

- **[Trade-off]** Manter o LLM2 neste change reduz escopo arquitetural, mas conserva uma
  etapa de inferência adicional.  
  **Mitigação:** tratar eventual simplificação arquitetural apenas após estabilizar o novo
  rulebook e observar se a etapa ainda agrega valor real.

## Migration Plan

1. Atualizar o documento consolidado de pesquisa apenas se, durante a implementação, algum
   detalhe clínico desta design decision precisar de ajuste formal.
2. Expandir o contrato de extração do LLM1 para suportar:
   - novo escopo/subtipo EDA;
   - sinais necessários para exames mínimos e exames adicionais;
   - buckets de ASA;
   - justificativa/evidência estruturada suficiente para o novo resumo da Sala 2.
3. Atualizar prompts e validações do LLM1 para permitir ASA prático e remover a restrição
   anterior que proibia essa estimativa.
4. Reescrever a política clínica EDA para refletir o novo rulebook, incluindo subtipos,
   matriz de contraindicação, bypass de corpo estranho e semântica de evidência.
5. Ajustar a etapa de síntese/reconciliação da recomendação para derivar suporte a partir
   do novo modelo clínico e compatibilizar a recomendação final com o formato já persistido.
6. Atualizar a classificação de escopo e o roteamento do pipeline para que `gastrostomia`,
   `dilatação esofágica` e `corpo estranho` avancem como EDA suportada, mantendo
   `non_eda|unknown` em revisão manual obrigatória.
7. Atualizar o resumo da Sala 2 e helpers de contexto para exibir:
   - procedimento solicitado canônico;
   - `paciente pediátrico: sim`;
   - `ASA estimado`;
   - novas causas objetivas alinhadas ao novo rulebook.
8. Atualizar documentação de produto e runbook manual, com espelhos `docs/en/` no mesmo
   change.
9. Executar validações direcionadas de testes, lint, tipos e markdown antes de avançar para
   a fase de tasks/implementação.

### Rollback

- Reverter o change completo se o novo contrato clínico gerar regressões relevantes em
  extração ou recomendação.
- Como este proposal não altera ainda o contrato da resposta médica nem o state machine de
  `vinda_imediata`, o rollback fica concentrado nas camadas de extração, política clínica,
  resumo da Sala 2 e documentação.

## Open Questions

- Nenhuma pendência funcional relevante foi deixada aberta para este Proposal 1.
- A principal decisão deliberadamente adiada é a implementação do novo contrato da resposta
  médica da Sala 2 com `fluxo de admissão`, que pertence ao Proposal 2.
- Também ficam explicitamente adiados para o Proposal 3 os ajustes de dashboard, Room-4 e
  métricas relacionados ao outcome `VINDA_IMEDIATA`.

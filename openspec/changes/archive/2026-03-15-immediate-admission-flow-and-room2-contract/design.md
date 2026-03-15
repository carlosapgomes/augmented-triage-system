# Immediate admission flow and Room-2 contract design

## Context

Após o Proposal 1, o sistema já produz um resumo clínico da Sala 2 alinhado ao novo rulebook EDA, incluindo subtipo de procedimento, ASA estimado, suporte recomendado e marcador pediátrico. Porém, a resposta médica estruturada e o fluxo operacional posterior continuam modelados pelo contrato antigo.

O estado atual do código mostra esse acoplamento legado de forma explícita:

- `doctor_decision_parser.py` só reconhece `decisao`, `suporte`, `motivo` e `caso`;
- `TriageDecisionWebhookPayload` aceita apenas `decision`, `support_flag` e `reason`;
- `HandleDoctorDecisionService._next_job_type()` bifurca rigidamente `deny -> post_room1_final_denial_triage` e `accept -> post_room3_request`;
- `CaseStatus` e `transitions.py` modelam apenas o ramo positivo que necessariamente passa por `DOCTOR_ACCEPTED -> R3_POST_REQUEST -> WAIT_APPT`;
- `PostRoom3RequestService` só sabe abrir o combo de agendamento no Room-3;
- `PostRoom1FinalService` só renderiza finais de agendamento confirmado, agendamento negado, negação médica, falha ou revisão manual.

Isso conflita com a decisão consolidada no documento de pesquisa: a Sala 2 deve continuar sendo a autoridade final, mas o médico precisa poder aceitar com `agendamento` ou com `vinda_imediata`, e o ramo de `vinda_imediata` não pode abrir agendamento nem depender operacionalmente da Sala 3 para fechar o caso.

Restrições já definidas:

- o parser continua estrito com campos desconhecidos;
- `vinda_imediata` só é válida quando `decisao=aceitar`;
- `motivo` permanece opcional;
- Room-3 participa como superfície informativa/auditável em `vinda_imediata`, mas não como gate de fechamento;
- o fechamento continua dependente do ACK da Sala 1;
- dashboard, métricas agregadas e outcome `VINDA_IMEDIATA` ficam fora deste change.

Stakeholders principais:

- médicos reguladores da Sala 2;
- equipe operacional da Sala 3;
- solicitantes/operadores da Sala 1;
- engenharia responsável por parser, state machine, recovery e mensagens Matrix.

## Goals / Non-Goals

**Goals:**

- Introduzir o novo contrato estruturado da Sala 2 com campo explícito de `fluxo de admissão`.
- Normalizar os aliases aceitos para `fluxo de admissão` e `vinda_imediata` sem flexibilizar campos desconhecidos.
- Persistir o fluxo de admissão escolhido pelo médico no mesmo registro do caso.
- Roteirizar deterministicamente o pós-decisão em dois ramos positivos: `agendamento` e `vinda_imediata`.
- Implementar o ramo de `vinda_imediata` com notificação na Sala 3, mensagem final na Sala 1 e fechamento governado apenas pela Sala 1.
- Preservar idempotência, recovery e rastreabilidade dos fluxos já existentes.
- Reaproveitar o máximo possível dos serviços e templates já existentes, especialmente para ACKs e finalização da Sala 1.

**Non-Goals:**

- Introduzir outcome agregado `VINDA_IMEDIATA` em dashboard, filtros, totais ou Sala 4.
- Redesenhar o rulebook clínico do Proposal 1.
- Reabrir a discussão sobre widget vs Matrix reply como caminho padrão da Sala 2.
- Preservar compatibilidade com o antigo callback/widget de decisão, que deixa de ser relevante neste proposal.
- Criar compatibilidade com templates legados da Sala 2 sem `fluxo de admissão`.
- Remodelar completamente a máquina de estados se um campo persistido + branching dirigido por job for suficiente.

## Decisions

### Decision 1: Estender o contrato estruturado da Sala 2 sem criar um segundo parser

- **Escolha:** evoluir `parse_doctor_decision_reply` para um único contrato canônico que suporte `decision`, `support_flag`, `reason`, `case_id` e o novo `admission_flow`.
- **Comportamento desejado:**
  - `decisao=aceitar` exige `suporte`, `fluxo de admissão` e `caso`;
  - `fluxo de admissão` aceita aliases de chave (`fluxo de admissão`, `fluxo de admissao`, `fluxo_admissao`);
  - `vinda_imediata` e `vinda imediata` são equivalentes e normalizados para um valor canônico único;
  - `decisao=negar` continua estrito para campos desconhecidos, mas `suporte` e `fluxo de admissão` tornam-se opcionais/ignoráveis e são normalizados internamente para `none`/`None`.
- **Racional:** evita bifurcar contratos paralelos para aceitar e negar, preserva previsibilidade do parser e mantém um único ponto de verdade para a resposta estruturada Matrix e para os consumidores internos já derivados desse parsing.
- **Alternativas consideradas:**
  - criar um parser separado só para `vinda_imediata`;
  - manter o parser atual e inferir `agendamento` como default implícito sem campo explícito.
- **Motivo da rejeição:** a primeira cria divergência de contratos; a segunda contradiz a decisão consolidada de que o médico deve declarar explicitamente o fluxo de admissão.

### Decision 2: Persistir `doctor_admission_flow` no caso, mantendo `doctor_decision` como eixo principal

- **Escolha:** adicionar um novo campo persistido no caso para o fluxo de admissão escolhido (`scheduled`/`immediate`, com nomenclatura interna a definir na implementação), sem substituir `doctor_decision`.
- **Racional:** `doctor_decision` continua respondendo “aceitou ou negou?”, enquanto `doctor_admission_flow` responde “como o aceite deve prosseguir?”. Isso permite branching posterior, recovery e auditoria sem duplicar significado em `doctor_decision` ou inventar novos valores para um enum já disseminado pelo código.
- **Alternativas consideradas:**
  - embutir `vinda_imediata` dentro de `doctor_decision`;
  - não persistir o fluxo e derivar tudo apenas do transcript Matrix.
- **Motivo da rejeição:** a primeira quebra o contrato semântico de `accept|deny`; a segunda fragiliza recovery, queries determinísticas e idempotência.

### Decision 3: Manter `DOCTOR_ACCEPTED` como estado-base e dirigir o ramo positivo por job + campo persistido

- **Escolha:** preservar `DOCTOR_ACCEPTED` como estado após aceite médico e fazer o branching para `post_room3_request` ou `post_immediate_admission_flow` com base em `doctor_admission_flow`.
- **Racional:** minimiza explosão de estados, reduz impacto em consultas existentes e mantém a distinção entre decisão médica e execução operacional do ramo positivo.
- **Como sustentar recovery:** `RecoveryService` passa a ler `doctor_admission_flow` junto com o snapshot do caso para reenfileirar o job correto.
- **Alternativas consideradas:**
  - criar um novo status terminal/intermediário exclusivo para `DOCTOR_ACCEPTED_IMMEDIATE`;
  - pular `DOCTOR_ACCEPTED` e ir direto a um estado operacional novo no CAS update.
- **Motivo da rejeição:** ambas aumentam o custo de migração de transições, queries e testes sem benefício proporcional, já que o branching pode ser determinado por um campo adicional persistido.

### Decision 4: Implementar `vinda_imediata` como um job orquestrador dedicado e idempotente

- **Escolha:** introduzir um job/serviço específico para o ramo `vinda_imediata`, responsável por:
  1. postar a comunicação informativa na Sala 3;
  2. postar o alvo auditável de ACK na Sala 3;
  3. postar a mensagem final específica na Sala 1 reutilizando a infraestrutura existente de finalização;
  4. tolerar falhas da Sala 3 sem bloquear a etapa da Sala 1.
- **Racional:** o fluxo precisa coordenar múltiplas salas com regra explícita de tolerância parcial a falhas. Concentrar isso num orquestrador dedicado torna o comportamento mais testável do que espalhar branches pontuais em `HandleDoctorDecisionService`, `PostRoom3RequestService` e `PostRoom1FinalService`.
- **Alternativas consideradas:**
  - adaptar `PostRoom3RequestService` para também fazer `vinda_imediata`;
  - encadear dois jobs separados e depender da fila para prosseguir para Sala 1.
- **Motivo da rejeição:** a primeira mistura scheduling com não-scheduling; a segunda aumenta chance de falhas intermediárias e de estado parcial difícil de recuperar.

### Decision 5: Reaproveitar a infraestrutura de finalização da Sala 1 com novo tipo de mensagem final

- **Escolha:** estender `PostRoom1FinalService` com um novo `job_type` para `vinda_imediata`, mantendo o mesmo mecanismo de reply ao evento original da Sala 1, persistência do transcript e criação do checkpoint `ROOM1_FINAL`.
- **Racional:** a regra de fechamento já é centrada na mensagem final da Sala 1. Reusar esse serviço preserva a arquitetura atual e evita duplicar a lógica crítica de cleanup/reação.
- **Alternativas consideradas:**
  - postar a mensagem da Sala 1 direto dentro do novo orquestrador, fora do serviço de final reply;
  - transformar a mensagem de `vinda_imediata` em uma variante da mensagem de agendamento confirmado.
- **Motivo da rejeição:** a primeira duplicaria lógica de finalização; a segunda criaria semântica enganosa, porque `vinda_imediata` explicitamente não depende de data/local/instruções de agendamento.

### Decision 6: Modelar a Sala 3 em `vinda_imediata` como superfície informativa + ACK auditável

- **Escolha:** na Sala 3, publicar uma mensagem informativa raiz e um segundo post de ACK como reply dessa mensagem, sem template de resposta de agendamento.
- **Conteúdo mínimo propagado:** procedimento solicitado, médico que aceitou, suporte recomendado, subtipo EDA relevante e marcador pediátrico quando existir.
- **Racional:** espelha a decisão consolidada de que a Sala 3 deve ser notificada e auditável, mas não acionada para marcar agenda. O reply de ACK preserva agrupamento visual semelhante ao padrão já existente no Room-3.
- **Alternativas consideradas:**
  - não notificar a Sala 3 no fluxo imediato;
  - reaproveitar o template de agendamento só mudando o texto de introdução.
- **Motivo da rejeição:** a primeira perde auditabilidade operacional; a segunda gera instrução incorreta para uma sala que não deve agendar esse caso.

### Decision 7: Manter feedback da Sala 2 e parser de erro coerentes com o novo campo

- **Escolha:** atualizar templates da Sala 2 para:
  - exibir `fluxo de admissão: agendamento` como default no modelo puro;
  - ecoar o fluxo normalizado nos ACKs de sucesso quando `decision=accept`;
  - preservar mensagens de erro/correção com o novo campo quando o erro ocorrer em contexto de aceite.
- **Racional:** o contrato novo precisa ser ensinável no próprio canal operacional, sem depender de documentação externa para o uso correto.
- **Alternativas consideradas:**
  - deixar o novo campo apenas na spec e no runbook;
  - manter ACKs antigos e mostrar o fluxo só nas salas posteriores.
- **Motivo da rejeição:** ambas reduzem legibilidade operacional e dificultam depuração de erros de uso do template.

## Risks / Trade-offs

- **[Risco]** O novo campo persistido exige migração de banco e atualização de snapshots/repositórios.  
  **Mitigação:** limitar a mudança a uma coluna explícita, atualizar fakes/fixtures e cobrir recovery/integration tests do caminho positivo.

- **[Risco]** O ramo `vinda_imediata` pode gerar duplicidade de mensagens se houver retry após falha parcial.  
  **Mitigação:** usar `case_messages.kind` distintos para mensagem informativa e ACK da Sala 3, e tornar o orquestrador idempotente antes de chamar a finalização da Sala 1.

- **[Risco]** Tornar `suporte` opcional em `negar` no parser pode enfraquecer demais a validação.  
  **Mitigação:** restringir a flexibilização apenas a `suporte` e `fluxo de admissão`, mantendo rejeição para qualquer outro campo desconhecido e normalizando o deny para `support_flag=none`.

- **[Risco]** Queries e telas existentes podem assumir que todo `DOCTOR_ACCEPTED` sempre chega a `WAIT_APPT`.  
  **Mitigação:** manter Proposal 2 explicitamente fora de dashboard agregada, atualizar apenas o que for necessário para não quebrar recovery e fluxos de operador já cobertos por testes.

- **[Trade-off]** Preservar `DOCTOR_ACCEPTED` como estado-base simplifica a migração, mas transfere parte da complexidade para o job de orquestração e para o campo persistido.  
  **Mitigação:** documentar claramente o branching em design/tests e centralizar a lógica de roteamento pós-decisão em um ponto único.

## Migration Plan

1. Adicionar o novo campo persistido de fluxo de admissão no modelo `cases` e nos ports/snapshots necessários.
2. Estender DTOs e parser da Sala 2 para carregar `admission_flow` normalizado até `HandleDoctorDecisionService`.
3. Atualizar o CAS de decisão médica para persistir `doctor_admission_flow` junto com `doctor_decision`, `doctor_support_flag` e `doctor_reason`.
4. Alterar o roteamento pós-decisão para escolher entre `post_room3_request`, `post_room1_final_denial_triage` e o novo job de `vinda_imediata`.
5. Implementar o orquestrador idempotente de `vinda_imediata` e os novos tipos de mensagem/kinds da Sala 3.
6. Estender `PostRoom1FinalService` e templates para o final reply específico de `vinda_imediata`.
7. Atualizar recovery, testes de integração, runbook manual e espelho inglês correspondente.
8. Validar explicitamente cenários de retry parcial, ausência/falha de postagem na Sala 3 e fechamento somente por ACK da Sala 1.

### Rollback

- Reverter a migração da coluna e o novo branching, restaurando `accept -> post_room3_request` como único caminho positivo.
- Como dashboard e outcome agregado permanecem fora deste change, o rollback fica concentrado em parser, persistência, roteamento de jobs e templates entre salas.

## Open Questions

- Nenhuma pendência funcional bloqueante permanece aberta para redigir o OpenSpec.
- A principal decisão deliberadamente adiada continua sendo a introdução do outcome agregado `VINDA_IMEDIATA` nas superfícies de observabilidade, reservada para o Proposal 3.

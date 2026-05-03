# Design

## Context

O change de fundação Django entrega autenticação, papéis, shell PWA e política de acesso por zona. O próximo passo é migrar o fluxo operacional humano completo para a web app, seguindo a sequência aprovada:

1. NIR envia PDF e acompanha casos.
2. Médico recebe fila e envia decisão estruturada.
3. Agendador recebe fila e confirma/nega o agendamento.
4. NIR visualiza o resultado final e confirma recebimento/fechamento.

O backend do ATS continua responsável pela orquestração do caso, máquina de estados, jobs e auditoria. O objetivo deste change não é redesenhar a lógica clínica, e sim substituir a interface humana baseada em mensagens por uma interface web role-aware. Este change assume um hard refactor: não haverá compatibilidade legada nem operação paralela do sistema antigo enquanto a versão web não estiver completa.

## Goals / Non-Goals

**Goals:**

- Entregar fluxo operacional web completo para `nir`, `doctor` e `scheduler`.
- Preservar rastreabilidade individual das ações humanas por caso.
- Reutilizar ao máximo os contratos e serviços de aplicação existentes para decisão médica, agendamento e fechamento.
- Manter timeline auditável única por caso, agora combinando PDF, LLM, sistema e ações web humanas.
- Eliminar a necessidade de operação humana via mensagens nesses três perfis.

**Non-Goals:**

- Entregar gestão/admin/manager completa neste change.
- Redesenhar a máquina de estados clínica.
- Mudar contratos LLM, critérios clínicos ou comportamento de scheduling interno.
- Adicionar MFA, autenticação externa ou canais híbridos de transição.

## Decisions

### Decision 1: Migrar a superfície humana, não a lógica clínica central

- **Escolha:** substituir apenas os pontos de interação humana, mantendo a orquestração clínica e os serviços centrais como base do workflow.
- **Racional:** reduz risco e preserva comportamento já testado em domínio/aplicação.
- **Alternativas consideradas:**
  - reimplementar o workflow inteiro no Django;
    - rejeitada por ampliar demais o escopo e ameaçar a estabilidade da máquina de estados.

### Decision 2: Tratar o upload NIR como a nova entrada canônica humana do caso

- **Escolha:** o NIR passa a criar casos exclusivamente pela web com upload do PDF, acionando a mesma cadeia downstream de extração e processamento.
- **Racional:** alinha a operação ao mock aprovado e remove a dependência do envio humano inicial por mensagem.
- **Conseqüência:** o sistema precisa persistir um evento humano web equivalente à entrada operacional do caso, definir estratégia clara de storage temporário/persistência do PDF enviado e expor ao NIR um estado operacional visível quando o processamento downstream falhar.

### Decision 3: Reusar a semântica de decisão médica existente em novo adapter web

- **Escolha:** o formulário web médico deve alimentar a mesma semântica de decisão estruturada já tratada pelo backend, incluindo `decision`, `support_flag`, `admission_flow` e `reason`.
- **Racional:** mantém consistência clínica e evita duplicação de regra de negócio.
- **Alternativas consideradas:**
  - criar um fluxo médico alternativo com schema diferente;
    - rejeitada por criar divergência de comportamento.

### Decision 4: Reusar a semântica de confirmação do agendamento em novo adapter web

- **Escolha:** o formulário web do agendador deve alimentar os mesmos conceitos já usados no backend para confirmação/negação de agendamento, incluindo data/hora, observações e motivo quando negado.
- **Racional:** preserva continuidade do workflow e mantém próximos jobs/auditoria.

### Decision 5: Substituir a confirmação final do NIR por uma ação web explícita

- **Escolha:** a confirmação final do NIR deixa de depender da reação humana em Room-1 e passa a ser um ato web explícito de confirmação de recebimento/ciência.
- **Racional:** sem interface humana por mensagens, a regra de fechamento precisa migrar para uma interação equivalente na web.
- **Conseqüência:** o checkpoint lógico de fechamento deixa de depender da reação humana em Room-1 e passa a depender da confirmação web do NIR; o cleanup trigger humano canônico migra de reação Matrix para ação web confirmatória.

### Decision 6: Persistir ações web humanas como eventos de timeline de primeira classe

- **Escolha:** upload NIR, decisão médica, resposta do agendador e confirmação final do NIR devem aparecer no histórico cronológico do caso com ator, timestamp e tipo de evento.
- **Racional:** a auditabilidade do ATS depende de uma timeline única e explicável.
- **Contrato mínimo:** cada evento humano web precisa carregar origem (`web`, `pdf`, `llm`, `matrix`, `system`), ator, timestamp, payload textual resumido e vínculo explícito com o caso.

### Decision 7: Construir filas web por papel com projeções focadas no trabalho pendente

- **Escolha:** cada perfil operacional terá fila/listagem voltada à sua etapa atual:
  - NIR: casos recentes e seus estados/resultados;
  - Doctor: casos aguardando decisão;
  - Scheduler: casos aguardando agendamento.
- **Racional:** reduz ruído operacional e segue o modelo dos mocks aprovados.

## Risks / Trade-offs

- **Risco:** regressão ao trocar entrada/decisão/fechamento humanos de mensagens para web.
  - **Mitigação:** slices verticais pequenos, TDD rigoroso e reuso dos contratos centrais existentes.
- **Risco:** inconsistência entre timeline antiga baseada em rooms e novos eventos web.
  - **Mitigação:** persistir origem/tipo de evento explicitamente e adaptar o dashboard para múltiplas origens humanas.
- **Risco:** mudança no fechamento final do caso afetar cleanup semantics.
  - **Mitigação:** tornar explícito na spec que o checkpoint humano canônico migra para a confirmação web do NIR e cobrir cenários positivos/negativos com testes focados.

## Migration Plan

1. Preparar projeções/queries necessárias para filas web por papel e fixar o contrato físico/lógico mínimo dos eventos humanos web na timeline.
2. Entregar upload NIR e criação de caso via web.
3. Entregar listagem e detalhe NIR com progresso inicial.
4. Entregar fila médica e submissão da decisão web.
5. Entregar fila do agendador e submissão da confirmação/negação web.
6. Entregar resultado final no NIR e confirmação explícita de recebimento.
7. Atualizar dashboard/timeline e runbook manual para refletir o fluxo web completo.

## Slice Plan

### Phase 1: Shared workflow projections

- Slice 1.1: consultas/projeções compartilhadas para filas e detalhes operacionais web.

### Phase 2: NIR intake and tracking

- Slice 2.1: upload PDF NIR e criação de caso.
- Slice 2.2: dashboard NIR e detalhe inicial do caso.

### Phase 3: Doctor workflow

- Slice 3.1: fila médica web.
- Slice 3.2: formulário de decisão médica web.

### Phase 4: Scheduler workflow

- Slice 4.1: fila do agendador web.
- Slice 4.2: formulário de confirmação/negação do agendamento.

### Phase 5: Final NIR acknowledgment and audit visibility

- Slice 5.1: resultado final no NIR + confirmação explícita de recebimento.
- Slice 5.2: timeline/dashboard/manual E2E atualizados para eventos web.

## Open Questions

- A visualização do PDF original no detalhe web do médico/NIR será entregue já neste change ou ficará inicialmente como placeholder com foco no fluxo principal.
- Caso exista falha downstream após upload NIR, a experiência de erro operacional precisa mostrar apenas estado do caso ou também ação explícita de retry para o operador.

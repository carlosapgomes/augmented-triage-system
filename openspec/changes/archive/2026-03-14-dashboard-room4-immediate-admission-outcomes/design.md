# Dashboard and Room-4 immediate-admission observability design

## Context

Após o Proposal 2, o sistema já distingue operacionalmente casos aceitos com
`agendamento` dos casos aceitos com `vinda_imediata`. Porém, as superfícies de
observabilidade ainda estão modeladas com semântica mais simples do que o
fluxo real exige.

Pelos artefatos atuais, o problema aparece em três frentes:

- `case-thread-monitoring-dashboard` ainda resume outcome da lista como:
  - `ACEITO` quando `appointment_status = confirmed`;
  - `NEGADO` quando há negação médica ou de agendamento;
  - `EM_ANDAMENTO` caso contrário.
- `room4-supervisor-periodic-summary` ainda resume apenas:
  - `pacientes recebidos`;
  - `relatórios processados`;
  - `casos avaliados`;
  - `aceitos`;
  - `recusados`.
- o Proposal 2 deliberadamente deixou fora do escopo a introdução de
  `VINDA_IMEDIATA` como outcome agregado nas superfícies de observabilidade.

Ao mesmo tempo, a semântica operacional já consolidada permanece válida:

- a decisão médica da Sala 2 escolhe o ramo (`agendamento` ou
  `vinda_imediata`);
- a Sala 3 é não bloqueante no ramo `vinda_imediata`;
- o processo só conclui quando a Sala 1 dá ciência da recomendação médica.

Isso cria uma necessidade de design importante: dashboard e Room-4 não podem
colapsar “ramo escolhido”, “status atual” e “desfecho final” em um único campo.
Caso contrário, o supervisor perde a informação operacional mais importante:
**onde o fluxo está parado agora**.

Stakeholders principais:

- supervisores da Sala 4, que precisam enxergar backlog e gargalos ao longo do
  dia;
- operadores do dashboard, que precisam localizar rapidamente em qual etapa um
  caso está pendente;
- equipe médica/operacional, que precisa distinguir aceite com agendamento de
  aceite com `vinda_imediata`;
- engenharia, que precisa introduzir essa observabilidade sem reabrir o fluxo
  operacional já entregue no Proposal 2.

Restrições já confirmadas:

- este change não altera parser, contrato da Sala 2 nem state machine clínica
  principal;
- a ciência da Sala 1 continua sendo o marco de conclusão do processo;
- `VINDA_IMEDIATA` não deve ser mostrado como concluído antes da ciência da
  Sala 1;
- a timeline existente deve ser preservada, com ajustes de leitura e resumo, e
  não redesenhada integralmente.

## Goals / Non-Goals

**Goals:**

- Separar observabilidade em quatro dimensões explícitas:
  - status atual do caso;
  - etapa pendente / ponto de parada;
  - ramo médico-operacional escolhido;
  - desfecho final agregado.
- Fazer o dashboard mostrar claramente quando um caso está:
  - em andamento;
  - aguardando uma sala/etapa específica;
  - já direcionado para `vinda_imediata`, sem estar concluído.
- Introduzir `VINDA_IMEDIATA` como desfecho agregado distinto quando o caso de
  fato conclui por esse ramo.
- Permitir filtros e totais operacionais que respondam perguntas de backlog e
  gargalo, não apenas de desfecho final.
- Expandir a mensagem periódica da Sala 4 para refletir tanto produção
  concluída quanto pendências atuais por etapa.
- Reaproveitar ao máximo os campos e eventos já persistidos pelo Proposal 2,
  evitando nova lógica de workflow.

**Non-Goals:**

- Alterar o parser da resposta médica da Sala 2.
- Alterar o fluxo operacional de `vinda_imediata` entre Sala 2, Sala 3 e Sala
  1.
- Redesenhar a timeline cronológica existente ou mudar seu modelo de
  persistência.
- Introduzir analytics históricos avançados, SLA, aging ou painéis analíticos
  além do backlog/totais operacionais necessários.
- Reabrir a semântica clínica do rulebook EDA.

## Decisions

### Decision 1: Separar `status_atual`, `etapa_pendente`, `ramo_operacional` e `desfecho_final` como conceitos de leitura

- **Escolha:** o design de observabilidade passará a tratar esses quatro
  conceitos como dimensões distintas, ainda que parte deles continue sendo
  derivada de campos e eventos já existentes.
- **Semântica desejada:**
  - `status_atual` responde se o caso segue `EM_ANDAMENTO` ou se já concluiu;
  - `etapa_pendente` responde onde ele está parado agora;
  - `ramo_operacional` responde qual caminho foi escolhido após a decisão
    médica (`agendamento`, `vinda_imediata`, ou ausência de ramo quando não
    aplicável);
  - `desfecho_final` responde o resultado consolidado do caso
    (`ACEITO`, `VINDA_IMEDIATA`, `NEGADO`, ou ausência quando ainda não
    concluído).
- **Racional:** isso preserva a pergunta operacional central (“onde parou?”)
  sem perder a distinção do ramo `vinda_imediata`.
- **Alternativas consideradas:**
  - continuar usando apenas uma coluna de outcome;
  - introduzir `VINDA_IMEDIATA` como substituto de `EM_ANDAMENTO` assim que o
    médico responde.
- **Motivo da rejeição:** a primeira perde visibilidade operacional; a segunda
  mascara casos ainda abertos aguardando ciência da Sala 1.

### Decision 2: Derivar a observabilidade prioritariamente do estado persistido do caso, não de heurísticas na timeline

- **Escolha:** dashboard e Room-4 devem usar primeiro o snapshot persistido do
  caso e seus campos derivados conhecidos, complementando com eventos somente
  quando necessário para leitura cronológica.
- **Racional:** a timeline serve muito bem para auditoria, mas é um ponto
  frágil para agregações determinísticas. A observabilidade operacional precisa
  de leitura consistente para lista, filtros, totais e resumo periódico.
- **Como aplicar:**
  - o cálculo de `status_atual`, `ramo_operacional` e `desfecho_final` deve ser
    centralizado em função/consulta compartilhada entre dashboard e Room-4;
  - `etapa_pendente` pode ser derivada do estado/job/checkpoint já persistidos
    pelo runtime, sem parsear a timeline inteira em cada tela.
- **Alternativas consideradas:**
  - inferir tudo diretamente dos transcripts Matrix;
  - deixar dashboard e Room-4 implementarem suas próprias regras separadas.
- **Motivo da rejeição:** a primeira é mais custosa e sujeita a ambiguidades; a
  segunda tende a criar divergência semântica entre superfícies.

### Decision 3: Considerar `VINDA_IMEDIATA` como desfecho final apenas após ciência da Sala 1

- **Escolha:** o caso só recebe `desfecho_final = VINDA_IMEDIATA` quando o
  fluxo imediato concluir pelo mesmo marco de fechamento já definido no
  Proposal 2: a ciência/ACK da Sala 1.
- **Antes disso:**
  - `status_atual = EM_ANDAMENTO`;
  - `ramo_operacional = vinda_imediata`;
  - `etapa_pendente` deve indicar algo equivalente a “aguardando ciência da
    Sala 1”, quando esse for o ponto de parada.
- **Racional:** mantém coerência com a definição de conclusão do processo e
  evita falsos positivos de caso concluído para supervisão.
- **Alternativas consideradas:**
  - marcar `VINDA_IMEDIATA` imediatamente após a resposta médica;
  - só marcar `VINDA_IMEDIATA` após algum evento adicional da Sala 3.
- **Motivo da rejeição:** a primeira quebra a semântica de fechamento; a segunda
  contradiz a regra de não bloqueio da Sala 3.

### Decision 4: Manter `ACEITO` como desfecho final reservado ao ramo com agendamento concluído

- **Escolha:** nas superfícies agregadas, `ACEITO` continua representando o ramo
  positivo concluído por agendamento/confirmado, enquanto `VINDA_IMEDIATA`
  representa o ramo positivo concluído por admissão imediata.
- **Racional:** isso concretiza a decisão consolidada da pesquisa e evita que os
  dois ramos positivos apareçam fundidos em um único total que esconde a carga
  operacional real.
- **Alternativas consideradas:**
  - manter um único total de `ACEITOS` e apenas mostrar `VINDA_IMEDIATA` como
    detalhe secundário;
  - substituir `ACEITO` por algo mais genérico para ambos os ramos.
- **Motivo da rejeição:** a primeira reduz utilidade operacional; a segunda cria
  mudança semântica maior do que o necessário para as specs atuais.

### Decision 5: Introduzir uma taxonomia de etapa pendente orientada a operação, não a todos os detalhes internos da state machine

- **Escolha:** o dashboard e a Room-4 exibirão uma taxonomia pequena e estável
  de “ponto de parada”, derivada dos estados/jobs atuais, por exemplo:
  - aguardando decisão médica (Sala 2);
  - aguardando agendamento / ação da Sala 3;
  - aguardando ciência final da Sala 1;
  - concluído.
- **Racional:** supervisores precisam de leitura rápida. Expor todos os estados
  internos, jobs e checkpoints torna a interface mais fiel ao código, mas pior
  para operação.
- **Alternativas consideradas:**
  - expor enums internos brutos do workflow;
  - não exibir etapa pendente e deixar o operador inferir pela timeline.
- **Motivo da rejeição:** a primeira aumenta ruído operacional; a segunda perde
  precisamente a informação que o Proposal 3 quer tornar explícita.

### Decision 6: Dashboard listagem e detalhe devem reutilizar a mesma camada de projeção de observabilidade

- **Escolha:** a listagem do dashboard, os totais/filtros e o resumo do detalhe
  do caso devem ser alimentados pela mesma projeção semântica.
- **Racional:** evita que a listagem mostre um caso como “em andamento” enquanto
  o detalhe o trate como “vinda imediata concluída”, ou vice-versa.
- **Implicação:**
  - a listagem passa a exibir, de forma compacta, ao menos outcome/status e a
    etapa pendente resumida;
  - o detalhe reforça essa leitura em bloco próprio acima da timeline.
- **Alternativas consideradas:**
  - resolver apenas a listagem;
  - resolver apenas o detalhe e manter a listagem simplificada.
- **Motivo da rejeição:** supervisão exige coerência rápida entre vista macro e
  vista detalhada.

### Decision 7: Room-4 deve receber duas famílias de agregados no mesmo resumo periódico

- **Escolha:** a mensagem periódica da Sala 4 passará a incluir dois blocos
  conceituais:
  1. **Desfechos concluídos no período**;
  2. **Backlog/pendências atuais no momento do resumo**.
- **Conteúdo mínimo esperado:**
  - desfechos concluídos:
    - aceitos por agendamento;
    - `VINDA_IMEDIATA`;
    - negados;
  - pendências atuais:
    - total em andamento;
    - subtotal por etapa pendente;
    - possibilidade de destacar quantos pendentes já estão no ramo
      `vinda_imediata`.
- **Racional:** supervisores precisam entender simultaneamente produção do
  período e estoque atual de trabalho pendente.
- **Alternativas consideradas:**
  - manter Room-4 apenas com desfechos concluídos;
  - criar uma segunda mensagem separada só para backlog.
- **Motivo da rejeição:** a primeira não atende ao objetivo operacional; a
  segunda aumenta ruído e fragmenta a leitura do supervisor.

### Decision 8: Totais do dashboard e resumo da Room-4 podem ter semânticas relacionadas, mas não idênticas no recorte temporal

- **Escolha:** os dois usarão a mesma projeção semântica, mas respeitando seu
  contexto:
  - dashboard: visão interativa filtrável do conjunto consultado;
  - Room-4: resumo periódico com desfechos no período e backlog atual no momento
    da emissão.
- **Racional:** isso mantém coerência conceitual sem forçar igualdade artificial
  entre uma consulta filtrável e um boletim periódico.
- **Alternativas consideradas:**
  - exigir que os números sempre batam literalmente com qualquer filtro do
    dashboard;
  - permitir semânticas completamente independentes.
- **Motivo da rejeição:** a primeira é irrealista; a segunda enfraquece a
  confiança operacional.

## Risks / Trade-offs

- **[Risco]** Misturar `status_atual` e `desfecho_final` na interface pode gerar
  leitura incorreta de caso concluído.  
  **Mitigação:** usar rótulos explícitos e centralizar a projeção semântica em
  um ponto compartilhado.

- **[Risco]** A derivação de `etapa_pendente` a partir de estados/jobs atuais
  pode ficar frágil se depender demais de detalhes internos.  
  **Mitigação:** definir uma taxonomia curta e mapear explicitamente apenas os
  estados/checkpoints relevantes para operação.

- **[Risco]** Room-4 pode ficar verbosa demais se o resumo tentar espelhar o
  dashboard inteiro.  
  **Mitigação:** limitar o resumo a totais essenciais, backlog por etapa e um
  destaque objetivo para `vinda_imediata`.

- **[Risco]** Casos legados, anteriores ao Proposal 2, podem não ter todos os
  sinais necessários para preencher ramo/outcome da nova forma.  
  **Mitigação:** prever fallback determinístico para “não aplicável/indisponível”
  e evitar reclassificação heurística agressiva do histórico.

- **[Trade-off]** Reutilizar estado persistido do caso simplifica agregação, mas
  exige disciplina para manter a projeção de observabilidade coerente com o
  runtime real.  
  **Mitigação:** concentrar regra em camada única reutilizada por dashboard e
  Room-4 e cobrir os ramos principais com testes direcionados.

## Migration Plan

1. Definir a projeção semântica compartilhada de observabilidade, capaz de
   derivar `status_atual`, `etapa_pendente`, `ramo_operacional` e
   `desfecho_final` a partir do caso persistido.
2. Atualizar as consultas e/ou adaptadores usados pelo dashboard para expor
   esses campos derivados na listagem, filtros, totais e resumo do detalhe.
3. Ajustar a renderização do dashboard para tornar visíveis:
  - backlog em andamento;
  - ponto de parada por etapa;
  - distinção entre ramo imediato pendente e `VINDA_IMEDIATA` concluído.
4. Atualizar a geração do resumo periódico da Sala 4 para incluir:
  - desfechos concluídos por tipo;
  - pendências atuais por etapa;
  - destaque para o ramo imediato quando ainda pendente e quando já concluído.
5. Cobrir com testes direcionados os principais cenários:
  - caso em agendamento ainda pendente;
  - caso em `vinda_imediata` aguardando ciência da Sala 1;
  - caso concluído como `VINDA_IMEDIATA`;
  - caso negado;
  - compatibilidade de leitura em viewport mobile.
6. Atualizar docs/runbook somente se necessário para refletir a nova leitura de
   dashboard/Room-4, sem reabrir o fluxo manual do Proposal 2.

### Rollback

- Reverter a nova projeção semântica e restaurar a leitura simplificada atual
  do dashboard e do resumo Room-4.
- Como este change não altera parser nem workflow operacional, o rollback fica
  concentrado em consultas/agregações, renderização do dashboard e formatação do
  resumo periódico.

## Open Questions

- Nenhuma pendência bloqueante permanece aberta para redigir os delta specs.
- Decisões já fechadas nesta fase:
  - a listagem do dashboard deve priorizar uma composição curta de
    `status_atual` com `etapa_pendente` ou `desfecho_final`, conforme o caso;
  - o resumo da Sala 4 deve incluir já na primeira versão o subtotal de
    pendentes no ramo `vinda_imediata`;
  - casos históricos anteriores ao Proposal 2 devem exibir ramo/semântica
    observável como `não aplicável` ou `indisponível`, sem inferência
    retrospectiva agressiva.

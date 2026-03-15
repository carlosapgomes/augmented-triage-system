# Dashboard and Room-4 immediate-admission observability proposal

## Why

O Proposal 2 introduziu o ramo operacional de `vinda_imediata`, mas as superfícies de observabilidade ainda não mostram com clareza se um caso já concluiu, em que etapa ele está parado e qual ramo médico-operacional foi escolhido. Para supervisão real do serviço, dashboard e Room-4 precisam mostrar não só desfechos finais, mas também backlog em andamento e pendências por etapa, inclusive quando um caso foi aceito com `vinda_imediata` e ainda aguarda ciência final da Sala 1.

## What Changes

- Tratar observabilidade operacional com dimensões separadas de:
  - status atual do caso;
  - etapa pendente / ponto de parada do fluxo;
  - ramo médico-operacional escolhido;
  - desfecho final agregado.
- Atualizar dashboard e superfícies de monitoramento para exibir claramente casos ainda `EM_ANDAMENTO`, inclusive quando já houve decisão médica de `vinda_imediata` mas a Sala 1 ainda não deu ciência.
- Introduzir `VINDA_IMEDIATA` como desfecho agregado distinto nas superfícies de observabilidade, sem confundir esse desfecho final com o ramo imediato ainda pendente de conclusão operacional.
- Adaptar filtros e totais do dashboard para responder perguntas operacionais como:
  - quantos casos seguem pendentes;
  - em qual sala/etapa eles estão parados;
  - quantos pertencem ao ramo `vinda_imediata`;
  - quantos já concluíram como `VINDA_IMEDIATA`.
- Adaptar o resumo/detalhe do caso para destacar onde o fluxo está parado e qual ramo foi escolhido, mantendo coerência com a timeline já existente.
- Adaptar os relatórios periódicos da Sala 4 para incluir visão semelhante ao dashboard, combinando:
  - desfechos consolidados;
  - pendências atuais por etapa;
  - visibilidade do ramo `vinda_imediata` dentro do backlog e dos desfechos concluídos.
- Preservar integralmente a semântica do Proposal 2:
  - a ciência da Sala 1 continua sendo o marco de conclusão do processo;
  - a Sala 3 continua não bloqueante no ramo `vinda_imediata`;
  - este change não altera parser, contrato da Sala 2 nem roteamento operacional já aprovado.

## Capabilities

### New Capabilities

- _None._

### Modified Capabilities

- `case-thread-monitoring-dashboard`: ajustar requisitos de listagem, detalhe, filtros e totais para distinguir status em andamento, etapa pendente, ramo `vinda_imediata` e desfechos finais sem perder a leitura de onde o fluxo parou.
- `dashboard-mobile-usability`: garantir que as mesmas semânticas de status, pendência, ramo e totais continuem legíveis e operáveis em viewport mobile.
- `room4-supervisor-periodic-summary`: expandir o resumo periódico da Sala 4 para incluir backlog em andamento por etapa e distinção entre desfechos concluídos, incluindo `VINDA_IMEDIATA`.

## Impact

- Dashboard web e consultas/agregações de monitoramento.
- Renderização da listagem, detalhe do caso, filtros e totais do dashboard.
- Geração e formatação dos resumos periódicos enviados à Sala 4.
- Testes de monitoramento/dashboard/Room-4 e documentação operacional associada.
- Nenhuma mudança no rulebook clínico, no parser da Sala 2 ou no fluxo operacional de `vinda_imediata` já entregue no Proposal 2.

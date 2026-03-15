# Immediate admission flow and Room-2 contract proposal

## Why

O Proposal 1 já reescreveu o rulebook clínico da EDA, mas o fluxo operacional continua preso ao contrato antigo da Sala 2: hoje o parser aceita apenas `decisao`, `suporte`, `motivo` e `caso`, e o serviço `HandleDoctorDecisionService` ainda bifurca rigidamente `accept -> post_room3_request` e `deny -> post_room1_final_denial_triage`. Isso impede materializar a decisão já consolidada de que o médico pode aceitar com `agendamento` ou com `vinda_imediata`, mantendo a Sala 2 como autoridade final sem abrir agendamento quando a admissão imediata for escolhida.

A mudança é necessária agora porque o novo rulebook já expõe contexto clínico suficiente para esse ramo operacional, e o código atual não possui campo persistido, semântica de parser, estado intermediário, mensagens entre salas nem tratamento de falha compatíveis com `vinda_imediata`.

## What Changes

- **BREAKING**: substituir o contrato estruturado da resposta médica na Sala 2 por um template que exija explicitamente o novo campo `fluxo de admissão`, aceitando aliases definidos e normalizando `agendamento` vs `vinda_imediata`.
- Ajustar o parser e a validação determinística da resposta médica da Sala 2 para:
  - exigir `fluxo de admissão` quando `decisao=aceitar`;
  - aceitar `vinda_imediata` e `vinda imediata` como equivalentes;
  - manter semântica de `negar` com parser estrito para campos desconhecidos, mas tornando `suporte` e `fluxo de admissão` semanticamente ignoráveis/opcionais nesse cenário;
  - preservar identidade do médico derivada do sender Matrix.
- Persistir o novo campo operacional no caso e ajustar o roteamento posterior à decisão médica para suportar dois ramos positivos:
  - `aceitar + agendamento` continua abrindo o fluxo atual da Sala 3;
  - `aceitar + vinda_imediata` cria um novo ramo operacional sem abrir fluxo de agendamento.
- Introduzir o fluxo operacional de `vinda_imediata` com a ordem já consolidada:
  - ACK padrão na Sala 2;
  - mensagem informativa + alvo auditável de ACK na Sala 3, sem solicitar agendamento;
  - mensagem final específica na Sala 1 informando aceite com vinda imediata autorizada;
  - encerramento ainda dependente apenas do ACK da Sala 1.
- Tornar a etapa da Sala 3 em `vinda_imediata` explicitamente não bloqueante:
  - falha de postagem ou ausência de reação na Sala 3 não pode impedir o fechamento quando a Sala 1 confirmar ciência.
- Propagar corretamente para o novo ramo o contexto mínimo já definido no Proposal 1, incluindo:
  - procedimento solicitado;
  - marcador pediátrico;
  - médico que aceitou;
  - suporte recomendado;
  - subtipo relevante como gastrostomia, dilatação esofágica ou corpo estranho.
- Atualizar runbook/manual E2E e documentação operacional para cobrir:
  - o novo template da Sala 2;
  - o ramo `agendamento`;
  - o ramo `vinda_imediata`;
  - cenários negativos de parsing/roteamento.
- Delimitar explicitamente que este change **não** introduz ainda:
  - o outcome agregado `VINDA_IMEDIATA` no dashboard;
  - filtros, totais, timeline agregada ou relatórios da Sala 4 específicos desse desfecho.
- Assumir explicitamente que o antigo callback/widget de decisão não precisa ser preservado nem mantido compatível neste change, porque o caminho padrão e único de decisão continua sendo a resposta estruturada Matrix na Sala 2.

## Capabilities

### New Capabilities

- `immediate-admission-operational-flow`: define o novo ramo operacional de `vinda_imediata`, incluindo persistência do fluxo escolhido, comunicação entre Sala 2, Sala 3 e Sala 1, tolerância a falhas da Sala 3 e regra de encerramento dependente do ACK da Sala 1.

### Modified Capabilities

- `room2-structured-reply-decision`: altera o contrato obrigatório da resposta estruturada da Sala 2 para incluir `fluxo de admissão`, atualizar parsing/normalização e preservar semântica estrita por campo.
- `manual-e2e-readiness`: atualiza as validações manuais para cobrir o novo template da Sala 2, o ramo positivo com `agendamento`, o ramo positivo com `vinda_imediata` e as novas falhas de validação/roteamento.

## Impact

- Código potencialmente afetado:
  - `src/triage_automation/domain/doctor_decision_parser.py`
  - `src/triage_automation/application/dto/webhook_models.py`
  - `src/triage_automation/application/services/room2_reply_service.py`
  - `src/triage_automation/application/services/handle_doctor_decision_service.py`
  - `src/triage_automation/application/services/post_room3_request_service.py`
  - `src/triage_automation/application/services/post_room1_final_service.py`
  - `src/triage_automation/application/services/recovery_service.py`
  - `src/triage_automation/domain/case_status.py`
  - `src/triage_automation/domain/transitions.py`
  - `src/triage_automation/application/ports/case_repository_port.py`
  - `src/triage_automation/infrastructure/db/case_repository.py`
  - `src/triage_automation/infrastructure/db/metadata.py`
  - `src/triage_automation/infrastructure/matrix/message_templates.py`
- Testes e validação potencialmente afetados:
  - parser e fluxo de reply da Sala 2;
  - serviços de ACK e roteamento pós-decisão;
  - mensagens e jobs da Sala 3;
  - mensagens finais e cleanup da Sala 1;
  - recovery/idempotência para ramos positivos.
- Documentação potencialmente afetada:
  - `docs/manual_e2e_runbook.md`
  - `docs/en/manual_e2e_runbook.md`
  - documentação operacional relacionada ao fluxo entre salas.
- Dependências e operação:
  - exige migração do modelo persistido/estado do caso para registrar o fluxo de admissão escolhido;
  - altera contrato humano-operacional da Sala 2 sem manter compatibilidade com templates antigos;
  - não altera ainda métricas agregadas, dashboard nem relatórios Room-4.

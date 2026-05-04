# Runbook Manual E2E

Idioma: **Português (BR)** | [English](en/manual_e2e_runbook.md)

Este runbook valida ponta a ponta o fluxo operacional completo em ambiente
local controlado/determinístico, cobrindo tanto a interface web operacional
(NIR, médico, agendador) quanto o dashboard de monitoramento e auditoria.

> **Direção atual do refactor web:** a validação deve priorizar a superfície consolidada em Django. Passos envolvendo superfícies humanas em FastAPI/Matrix devem ser tratados como referência legada ou apoio de cutover, não como baseline obrigatório de compatibilidade.

Execute `docs/runtime-smoke.md` antes para confirmar startup dos processos e
alcance de callback.

## Pré-requisitos

1. Inicie os processos de runtime com os mesmos comandos usados em
   `docs/runtime-smoke.md`:

```bash
# API de monitoramento (FastAPI)
uv run uvicorn apps.bot_api.main:create_app --factory --host 0.0.0.0 --port 8000

# App operacional web (Django) — porta 8001
uv run apps/django_ops/manage.py runserver 0.0.0.0:8001

# Bot Matrix (para jobs downstream e transcrições)
uv run python -m apps.bot_matrix.main

# Worker de jobs
uv run python -m apps.worker.main
```

1. O banco de dados deve estar migrado (`alembic upgrade head`).

1. Crie usuários de teste para cada papel operacional, se ainda não existirem:

```bash
uv run apps/django_ops/manage.py create_user nir@teste.com senha123 nir
uv run apps/django_ops/manage.py create_user medico@teste.com senha123 doctor
uv run apps/django_ops/manage.py create_user agenda@teste.com senha123 scheduler
uv run apps/django_ops/manage.py create_user gestor@teste.com senha123 manager
uv run apps/django_ops/manage.py create_user admin@teste.com senha123 admin
```

## Checagens de login web e menu por papel

> **Nota:** as rotas e superfícies administrativas definitivas deste programa devem convergir para o Django. Se algum passo abaixo mencionar fluxo legado ou rota antiga, trate-o como referência histórica até a atualização final do runbook no slice de handoff.

1. Acesso anônimo no navegador:

- abrir `GET /`
- esperado: redirect para `/login`

1. Checagens de sessão `manager`:

- login como usuário `manager` via formulário `POST /login`
- verificar `GET /dashboard/cases` retorna `200`
- verificar shell nav contém `Dashboard`
- verificar shell nav não contém `Prompts`
- verificar `GET /admin/prompts` retorna `403`

1. Checagens de sessão `admin`:

- login como usuário `admin` via formulário `POST /login`
- verificar `GET /dashboard/cases` retorna `200`
- verificar shell nav contém `Dashboard` e `Prompts`
- verificar `GET /admin/prompts` retorna `200` com lista e controles de
  ativação

1. Logout:

- enviar `POST /logout` no cabeçalho da shell
- esperado: redirect para `/login`
- verificar que um novo `GET /` redireciona para `/login`

## Fluxo Operacional Web

O fluxo operacional humano principal (NIR → Médico → Agendador → NIR)
é executado exclusivamente pela app web Django na porta 8001.

### NIR — Upload de PDF e Criação de Caso

1. Acessar `/login/` na porta 8001 e autenticar como `nir@teste.com`.

1. Após login, verificar redirect para `/nir/` com:
   - link "Novo Caso" ou similar apontando para `/nir/upload/`
   - listagem de casos ativos (se houver)

1. Clicar no link de upload e verificar:
   - formulário com campo de upload de arquivo
   - botão de envio

1. Selecionar um arquivo PDF válido e enviar:
   - esperado: página de resultado com `case_id` e status
     "Recebido — processando"
   - o worker deve enfileirar o job `process_pdf_case` automaticamente

1. Verificar criação auditável:
   - voltar para `/nir/` e confirmar que o novo caso aparece na listagem
   - abrir o detalhe do caso em `/nir/cases/{case_id}/`
   - verificar seção "Linha do Tempo" contém evento `NIR_PDF_UPLOAD` com
     source `[web]`
   - verificar se o ator do evento é o email do NIR logado

1. Checagens negativas:
   - enviar arquivo não-PDF (ex: `.txt`): deve rejeitar com mensagem de erro
   - enviar sem selecionar arquivo: deve rejeitar com mensagem de erro
   - acessar `/nir/upload/` como `medico@teste.com`: deve retornar 403

### Médico — Fila e Decisão Web

1. Após o caso ser processado pelo worker e chegar ao status `WAIT_DOCTOR`,
   acessar `/login/` e autenticar como `medico@teste.com`.

1. Verificar redirect para `/doctor/` com:
   - listagem de casos aguardando decisão (status `WAIT_DOCTOR`)
   - cada card mostra resumo clínico e link para decidir

1. Clicar no link de decisão e verificar formulário em
   `/doctor/cases/{case_id}/decision/`:
   - campos: decisão (aceitar/negar), suporte, fluxo de admissão,
     motivo
   - dados do paciente visíveis (nome, idade, registro)

1. Submeter decisão de aceite com agendamento:
   - `decisao: aceitar`
   - `fluxo de admissão: scheduled`
   - esperado: redirect para `/doctor/` e o caso some da fila
   - verificar no detalhe do caso (via `/monitoring/cases/{case_id}`)
     que o evento `DOCTOR_DECISION` aparece na timeline com
     source `web` e ator `medico@teste.com`

1. Submeter decisão de negativa (outro caso):
   - `decisao: negar`
   - `motivo: documentação insuficiente`
   - esperado: redirect e o caso some da fila médica

1. Checagens negativas:
   - submeter sem selecionar fluxo de admissão no aceite:
     deve rejeitar com mensagem de erro
   - submeter negativa sem motivo: deve rejeitar com mensagem de erro
   - submeter com `support_flag` inválido: deve rejeitar
   - acessar `/doctor/` como `nir@teste.com`: deve retornar 403

### Agendador — Fila e Confirmação Web

1. Após decisão médica de aceite com agendamento, o caso avança para
   `WAIT_APPT`. Acessar `/login/` e autenticar como `agenda@teste.com`.

1. Verificar redirect para `/scheduler/` com:
   - listagem de casos aguardando confirmação (status `WAIT_APPT`)
   - cada card mostra resumo e link para confirmar

1. Clicar no link e verificar formulário em
   `/scheduler/cases/{case_id}/confirm/`:
   - campos: ação (confirmar/negar), data, horário, local,
     instruções (opcional)
   - dados do paciente visíveis

1. Submeter confirmação:
   - `ação: confirmar`
   - preencher data (DD/MM/AAAA), horário (HH:MM), local
   - esperado: redirect para `/scheduler/` e o caso some da fila
   - verificar na timeline (via `/monitoring/cases/{case_id}`)
     que o evento `SCHEDULER_CONFIRMATION` aparece com
     source `web` e ator `agenda@teste.com`

1. Submeter negativa (outro caso):
   - `ação: negar`
   - `motivo: vaga indisponível`
   - esperado: redirect, caso sai da fila

1. Checagens negativas:
   - confirmar sem preencher data: deve rejeitar com erro
   - confirmar sem horário: deve rejeitar com erro
   - confirmar sem local: deve rejeitar com erro
   - data/hora em formato inválido: deve rejeitar com erro
   - negar sem motivo: deve rejeitar com erro
   - acessar `/scheduler/` como `medico@teste.com`: deve retornar 403

### NIR — Resultado Final e Confirmação de Recebimento

1. Após a confirmação do agendador, o worker processa o job
   `post_room1_final_appt` e o caso avança para
   `WAIT_R1_CLEANUP_THUMBS`.

1. Acessar o detalhe do caso como NIR em
   `/nir/cases/{case_id}/`.

1. Verificar seção "Resultado Final":
   - deve exibir botão "Confirmar Recebimento do Resultado"
   - o status do caso deve ser `WAIT_R1_CLEANUP_THUMBS`

1. Clicar no botão de confirmação:
   - esperado: redirect para `/nir/`
   - o caso deve desaparecer da listagem NIR (status muda para `CLEANED`
     após o job `execute_cleanup`)
   - verificar na timeline (via `/monitoring/cases/{case_id}`)
     que o evento `NIR_FINAL_ACKNOWLEDGMENT` aparece com
     source `web` e ator `nir@teste.com`

1. Este passo substitui a reação thumbs-up na Room-1 do Matrix como
   checkpoint canônico de fechamento humano.

## Caminho positivo de resposta estruturada da Sala 2 (Matrix — referência legada)

1. Validar o combo de três mensagens da Sala 2 para o caso alvo em clientes
   desktop e mobile:

- mensagem I: contexto original do PDF
- mensagem II: resumo técnico da triagem, reply da mensagem I
- mensagem III (`message III`): instruções de template estrito, reply da mensagem I
- verificar em desktop e mobile que as mensagens permanecem agrupadas sob a
  mensagem I

1. Validar o conteúdo obrigatório da mensagem II.

Esperado no resumo técnico:

- contexto com `procedimento solicitado: ...`
- `paciente pediátrico: sim` quando aplicável
- blocos na ordem abaixo:
  1. `Resumo clínico`
  2. `Achados críticos`
  3. `Pendências críticas`
  4. `Decisão sugerida`
  5. `Suporte recomendado`
  6. `ASA estimado`
  7. `Motivo objetivo`

1. Abrir a mensagem III e copiar o template estrito.

2. Validar que o template de aceite inclui explicitamente a linha
   `fluxo de admissão: agendamento`.

3. Enviar decisão como reply Matrix para a mensagem I (`reply to message I`):

- manter exatamente uma linha por campo do template
- respeitar os valores válidos fornecidos pelo bot
- `motivo` pode ser vazio/opcional
- para `decisao: aceitar`, preencher obrigatoriamente `fluxo de admissão`

### Aceite com agendamento

1. Para validação do caminho positivo padrão, enviar uma resposta de aceite sem
   suporte adicional usando `fluxo de admissão: agendamento`.

2. Validar progressão esperada:

- status do caso move para `DOCTOR_ACCEPTED`
- próximo job `post_room3_request` é enfileirado
- a confirmação do bot na Sala 2 ecoa o fluxo normalizado como `agendamento`
- a Sala 3 recebe o combo padrão de solicitação + template de agendamento
- auditoria inclui sender Matrix como ator e outcome

### Aceite com vinda imediata

1. Repetir o fluxo de aceite usando `fluxo de admissão: vinda_imediata`.

2. Validar aliases aceitos em cliente mobile, quando aplicável:

- `vinda_imediata`
- `vinda imediata`

1. Validar progressão esperada do ramo imediato:

- status médico continua em `DOCTOR_ACCEPTED` até a mensagem final da Sala 1
- próximo job `post_immediate_admission_flow` é enfileirado
- a confirmação do bot na Sala 2 ecoa o fluxo normalizado imediato
- a Sala 3 recebe apenas a comunicação informativa de vinda imediata e o alvo
  de ACK auditável
- a Sala 3 não deve receber o combo padrão de agendamento (`post_room3_request`)
- a Sala 1 recebe a mensagem final equivalente a
  `aceito com vinda imediata autorizada`
- o fechamento segue pela reação positiva da Sala 1, via
  `post_room1_final_immediate`
- a reação/observação da Sala 3 permanece opcional, não obrigatória, para o
  fechamento do caso

## Casos suportados EDA: subtipo e contexto na Room-2

1. Validar que os seguintes subtipos permanecem dentro do fluxo automático EDA:

- `standard`
- `gastrostomy`
- `esophageal_dilation`
- `foreign_body`

1. Executar pelo menos um caso manual para cada subtipo suportado.

2. Validar no contexto da mensagem II da Room-2 o texto canônico esperado:

- `standard` → `procedimento solicitado: EDA`
- `gastrostomy` → `procedimento solicitado: EDA para gastrostomia`
- `esophageal_dilation` → `procedimento solicitado: EDA para dilatação esofágica`
- `foreign_body` → `procedimento solicitado: EDA para retirada de corpo estranho`

1. Validar que o texto exibido na Room-2 vem do subtipo canônico e não de texto
   livre inconsistente do laudo.

2. Quando o caso for pediátrico (idade `< 16`), validar também:

- presença de `paciente pediátrico: sim`
- marcador renderizado perto do contexto do caso, e não escondido dentro da
  justificativa livre

## ASA estimado e suporte recomendado na Room-2

1. Executar um caso com `ASA estimado` prático igual a `I-II`.

- esperado: bloco `ASA estimado` exibe `I-II`
- esperado: `Suporte recomendado` compatível com ausência de suporte adicional
  obrigatório

1. Executar um caso com `ASA estimado` prático igual a `III ou mais`.

- esperado: bloco `ASA estimado` exibe `III ou mais`
- esperado: `Suporte recomendado` ao menos `anestesista`

1. Executar um caso com risco cardiovascular suficiente para ICU.

- esperado: `Suporte recomendado = anestesista_uti`
- esperado: o bloco `ASA estimado` continua explícito e separado do suporte

1. Executar um caso com dados insuficientes para ASA prático.

- esperado: bloco `ASA estimado` exibe `não foi possível estimar com os dados apresentados`
- esperado: o suporte continua derivado do restante da evidência confirmada, sem
  inventar classe ASA formal

## Caminho de revisão manual por escopo EDA (`non_eda|unknown`)

1. Execute dois casos manuais com `preop_screening.exam_type` diferente:

- caso A: `non_eda`
- caso B: `unknown`

1. Valide o resultado determinístico no `suggested_action_json` de cada caso:

- `decision = manual_review_required`
- `suggestion` não pode ser `accept` nem `deny`
- `preop_gate.decision = manual_review_required`
- `reason_code` esperado:
  - `non_eda_request` para caso A
  - `unknown_exam_type` para caso B

1. Valide auditoria e roteamento:

- existe evento `EDA_SCOPE_GATED_MANUAL_REVIEW` com `reason_code`,
  `reason_text` e `evidence_spans`
- job `post_room1_final_scope_manual_review` é enfileirado/executado
- mensagem final na Room-1 informa que a solicitação não é EDA (ou está
  indefinida) e exige revisão manual

1. Valide ausência de recomendação automática na Room-2 no mesmo ciclo:

- não deve existir publicação de resumo de recomendação para esse caso na
  Room-2

## Exceção de corpo estranho (`foreign_body`)

1. Execute um caso suportado com subtipo `foreign_body`.

2. Monte o caso sem exames mínimos completos e sem laudos condicionais, por
   exemplo:

- sem Hb/plaquetas/INR/TTPa/ureia/creatinina úteis
- sem laudo mínimo de ECG
- sem laudo mínimo de RX de tórax
- sem laudo mínimo de ecocardiograma

1. Valide o comportamento determinístico esperado:

- o caso continua dentro do fluxo automático EDA
- `preop_gate.decision = accept`
- `preop_gate.reason_code = foreign_body_exception`
- a ausência desses exames não derruba o caso por completude mínima nessa etapa

1. Valide a Room-2:

- `procedimento solicitado: EDA para retirada de corpo estranho`
- `Motivo objetivo` não deve descrever negação por falta de exames mínimos ou
  gates condicionais quando a exceção de corpo estranho se aplica
- `Suporte recomendado` e `ASA estimado` continuam podendo aparecer conforme o
  restante do contexto clínico

## Negações determinísticas do rulebook reescrito

### Exames mínimos obrigatórios ausentes

1. Execute pelo menos um caso `standard`, `gastrostomy` ou
   `esophageal_dilation` faltando exame mínimo obrigatório.

Cenários recomendados:

- creatinina ausente
- plaquetas ausentes
- TP/INR/RNI sem evidência numérica

1. Valide saída persistida:

- `suggestion = deny`
- `preop_gate.decision = deny`
- `preop_gate.reason_code` compatível com o exame faltante

1. Valide a mensagem II da Room-2:

- `Motivo objetivo` cita explicitamente qual exame mínimo está ausente
- o texto permanece curto e orientado à decisão médica

### ECG, RX e ECO sem laudo mínimo quando aplicáveis

1. Execute um caso EDA com gatilho cardiovascular e sem laudo mínimo de ECG.

Exemplos de gatilho:

- idade `> 40`
- doença cardiovascular conhecida
- dor torácica, dispneia, palpitações, síncope
- diabetes, obesidade explícita, múltiplas comorbidades

1. Execute um caso EDA com gatilho respiratório e sem laudo mínimo de RX de
   tórax.

2. Execute um caso EDA com gatilho estrutural cardíaco e sem laudo mínimo de
   ecocardiograma.

3. Valide saída persistida:

- `preop_gate.reason_code` esperado:
  - `missing_ecg_with_cardiovascular_disease`
  - `missing_chest_xray_with_respiratory_risk`
  - `missing_echocardiogram_with_structural_heart_risk`

1. Valide a mensagem II da Room-2:

- texto deve explicar objetivamente a falta de laudo mínimo do exame aplicável
- não deve cair em texto genérico de fallback quando o `reason_code` existe
- a redação deve ser adequada para revisão médica rápida

### Contraindicação por limiar clínico

1. Execute casos EDA com limiar excedido para cada perfil clínico relevante,
   quando possível:

- geral
- hepatopatia explícita
- cardiopatia explícita
- hepatopatia + cardiopatia explícitas

1. Exemplos de cenários:

- Hb abaixo do limiar
- plaquetas abaixo do limiar
- INR/RNI acima do limiar

1. Valide saída persistida:

- `preop_gate.decision = deny`
- `reason_code` esperado:
  - `hb_below_threshold`, ou
  - `platelets_below_threshold`, ou
  - `inr_above_threshold`

1. Valide a mensagem II da Room-2:

- `Motivo objetivo` explicita a contraindicação e o limiar falhado
- o texto continua curto, sem linguagem de aceite e sem misturar recomendação de
  suporte

### Precedência do motivo objetivo

1. Execute um caso com mais de uma causa potencial de negação.

Exemplo recomendado:

- exame mínimo ausente **e** ECG faltante **e** outro sinal de pendência

1. Valide a precedência do texto em `Motivo objetivo`:

- exame mínimo obrigatório ausente tem prioridade sobre ECG/RX/ECO
- ECG/RX/ECO têm prioridade sobre contraindicação por limiar
- se houver mais de duas causas, a Room-2 lista no máximo duas e adiciona texto
  equivalente a `e outras pendências críticas`

## Checagens negativas de auth do widget

1. Enviar sem Authorization header (`without Authorization`):

- `POST /widget/room2/submit`
- esperado: `401`

1. Enviar com token de papel `manager` (`manager role token`):

- `POST /widget/room2/submit`
- esperado: `403`

1. Validar ausência de mutação inesperada de estado/job (`state/job mutation`):

- status do caso não muda
- nenhum job adicional de decisão é enfileirado
- apenas registros esperados de auth/auditoria são adicionados

## Checagens negativas de reply da Sala 2

1. Postar reply com template malformado (`malformed template`):

- reply para a mensagem I com linhas obrigatórias ausentes/inválidas
- esperado: feedback do bot inclui `error_code: invalid_template`
- esperado: nenhuma mutação de decisão (`no decision mutation`) e nenhum novo job downstream

1. Postar template válido no parent de reply errado (`wrong reply-parent`):

- enviar template como reply para message II/III ou evento não relacionado
- esperado: feedback do bot inclui `error_code: invalid_template`
- esperado: nenhuma mutação de decisão (`no decision mutation`) e nenhum novo job downstream

1. Postar `decisao: aceitar` sem a linha obrigatória `fluxo de admissão`:

- exemplo: aceitar sem a linha obrigatória `fluxo de admissão`
- esperado: decisão rejeitada sem mutação de estado/job
- esperado: mensagem de correção do bot restaura o campo obrigatório no template

1. Postar `decisao: aceitar` com valor inválido de `fluxo de admissão`:

- exemplos inválidos: `plantao`, `urgente`, qualquer valor fora de
  `agendamento|vinda_imediata`
- esperado: decisão rejeitada sem mutação de estado/job
- esperado: nenhuma abertura de agendamento e nenhum job
  `post_immediate_admission_flow`

## Checagens de dashboard e API de monitoramento

1. Abrir listagem de dashboard server-rendered no navegador:

- `GET /dashboard/cases` com bearer token válido
- esperado: lista HTML renderiza casos e filtros
- validar presença do resumo operacional compacto por caso (`status atual · etapa pendente · ramo operacional`) quando diferente do desfecho legado exibido na linha
- validar totais operacionais da busca com pelo menos: `casos em andamento`, `aguardando Sala 2`, `aguardando Sala 3`, `aguardando Sala 1` e `pendentes no ramo vinda imediata`
- validar filtros operacionais para `status atual`, `etapa pendente`, `ramo operacional` e `desfecho final`

1. Validar API de listagem de monitoramento:

- `GET /monitoring/cases`
- esperado: `200` com JSON contendo `items`, `page`, `page_size`, `total`

1. Validar API de detalhe por caso e eventos auditáveis:

- `GET /monitoring/cases/{case_id}`
- esperado: `200` com timeline cronológica (`chronological timeline`) ordenada por `timestamp`
- timeline deve incluir `source`, `channel`, `actor`, `event_type`
- quando aplicável, validar presença de eventos ACK, human reply e **eventos web humanos**
  (`NIR_PDF_UPLOAD`, `DOCTOR_DECISION`, `SCHEDULER_CONFIRMATION`,
  `NIR_FINAL_ACKNOWLEDGMENT`) com `source="web"`
- verificar que eventos web e matrix coexistem na mesma timeline com
  origens distintas

1. Cruzar API com detalhe do dashboard:

- abrir `GET /dashboard/cases/{case_id}`
- verificar timeline cronológica visível na UI igual à API de monitoramento para
  o mesmo caso
- validar bloco `Resumo Operacional` acima da timeline com `status atual`, `etapa pendente`, `ramo operacional` e `desfecho final`
- em caso pendente com `vinda imediata`, validar que o detalhe continua `EM_ANDAMENTO`/`AGUARDANDO_SALA_1` até a ciência final da Sala 1
- alternar entre `view=thread` e `view=pure` e confirmar que o resumo operacional permanece visível em ambos

## Fluxo de autorização de gerenciamento de prompts

1. Usando `manager token`, verificar comportamento read-only:

- `GET /monitoring/cases` retorna `200`
- `GET /admin/prompts/versions` retorna `403`
- `GET /admin/prompts/{prompt_name}/active` retorna `403`
- `POST /admin/prompts/{prompt_name}/activate` retorna `403`

1. Usando `admin token`, verificar mutação de prompts:

- `GET /admin/prompts/versions` retorna `200`
- `GET /admin/prompts/{prompt_name}/active` retorna `200`
- `POST /admin/prompts/{prompt_name}/activate` retorna `200`

1. Validar efeitos colaterais de ativação de prompt:

- exatamente uma versão ativa permanece para o nome do prompt
- auditoria auth inclui `prompt_version_activated` com ator e prompt/version alvo

1. Validar ativação de prompt via formulário HTML (sessão `admin`):

- abrir `GET /admin/prompts`
- enviar formulário `POST /admin/prompts/{prompt_name}/activate-form`
- esperado: redirect para `/admin/prompts` com feedback de ativação
- validar última linha em `auth_events` com
  `event_type=prompt_version_activated`

## Fluxo de autorização de gerenciamento de usuários

1. Usando `manager token`, validar bloqueio de acesso:

- `GET /admin/users` retorna `403`
- `POST /admin/users` retorna `403`
- `POST /admin/users/{user_id}/block` retorna `403`
- `POST /admin/users/{user_id}/activate` retorna `403`
- `POST /admin/users/{user_id}/remove` retorna `403`
- esperado: sem mutação de contas de usuário

1. Usando sessão `admin`, validar criação de conta:

- abrir `GET /admin/users`
- enviar formulário `POST /admin/users` para criar um `manager`
- esperado: redirect para `/admin/users` com feedback `Usuario criado`
- validar que o novo usuário aparece na listagem com estado `active`
- validar auditoria em `auth_events`:
  - consultar o último evento para o alvo:

    ```sql
    SELECT event_type, user_id, payload
    FROM auth_events
    WHERE payload->>'target_user_id' = '<target_user_id>'
    ORDER BY occurred_at DESC
    LIMIT 1;
    ```

  - `event_type=user_created`
  - `user_id` do evento igual ao admin ator
  - `payload` inclui `target_user_id`, `target_email`, `target_role`,
    `previous_status`, `new_status`
  - `previous_status` esperado: `null`
  - `new_status` esperado: `active`

1. Usando sessão `admin`, validar bloqueio de conta ativa:

- enviar `POST /admin/users/{user_id}/block` para usuário alvo `active`
- esperado: redirect para `/admin/users` com feedback de atualização
- validar na listagem que o usuário alvo muda para estado `blocked`
- validar `POST /auth/login` com credenciais do usuário alvo retorna `403`
  (`inactive user`)
- validar auditoria em `auth_events`:
  - consultar o último evento para o alvo:

    ```sql
    SELECT event_type, user_id, payload
    FROM auth_events
    WHERE payload->>'target_user_id' = '<target_user_id>'
    ORDER BY occurred_at DESC
    LIMIT 1;
    ```

  - `event_type=user_blocked`
  - `user_id` do evento igual ao admin ator
  - `payload.target_user_id` igual ao usuário alvo
  - `payload.previous_status=active`
  - `payload.new_status=blocked`

1. Usando sessão `admin`, validar reativação de conta bloqueada:

- enviar `POST /admin/users/{user_id}/activate` para usuário alvo `blocked`
- esperado: redirect para `/admin/users` com feedback de atualização
- validar na listagem que o usuário alvo volta para estado `active`
- validar `POST /auth/login` com credenciais do usuário alvo retorna `200`
- validar auditoria em `auth_events`:
  - consultar o último evento para o alvo:

    ```sql
    SELECT event_type, user_id, payload
    FROM auth_events
    WHERE payload->>'target_user_id' = '<target_user_id>'
    ORDER BY occurred_at DESC
    LIMIT 1;
    ```

  - `event_type=user_reactivated`
  - `user_id` do evento igual ao admin ator
  - `payload.target_user_id` igual ao usuário alvo
  - `payload.previous_status=blocked`
  - `payload.new_status=active`

1. Usando sessão `admin`, validar remoção administrativa (soft delete):

- enviar `POST /admin/users/{user_id}/remove` para usuário alvo
- esperado: redirect para `/admin/users` com feedback de atualização
- validar na listagem que o usuário alvo muda para estado `removed`
- validar `POST /auth/login` com credenciais do usuário alvo retorna `403`
  (`inactive user`)
- validar auditoria em `auth_events`:
  - consultar o último evento para o alvo:

    ```sql
    SELECT event_type, user_id, payload
    FROM auth_events
    WHERE payload->>'target_user_id' = '<target_user_id>'
    ORDER BY occurred_at DESC
    LIMIT 1;
    ```

  - `event_type=user_removed`
  - `user_id` do evento igual ao admin ator
  - `payload.target_user_id` igual ao usuário alvo
  - `payload.previous_status=active` ou `blocked`
  - `payload.new_status=removed`

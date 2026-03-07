# room3-message-adjustments Proposal

## Why

As mensagens do Room-3 (agendamento) contêm inconsistências de ortografia e formatação que prejudicam a clareza para os usuários. Especificamente: (1) a palavra "instruções" está sem acento e sem cedilha; (2) o formato de data no template usa hífen (`DD-MM-YYYY`) ao invés do formato brasileiro padrão com barra (`DD/MM/YYYY`); (3) a mensagem de ack não deixa claro que é uma confirmação de encerramento; (4) a mensagem de solicitação não mostra quem foi o médico que aceitou o caso.

## What Changes

- **Mensagem 1 (`build_room3_request_message`)**: Adicionar linha `aceito por: <nome do médico>` abaixo do exame solicitado
- **Mensagem 2 (`build_room3_reply_template_message`)**:
  - Corrigir `instrucoes` → `instruções`
  - Alterar formato de data de `DD-MM-YYYY HH:MM BRT` para `DD/MM/YYYY HH:MM`
- **Mensagem 3 (`build_room3_ack_message`)**: Alterar texto de `Reaja com +1 para confirmar.` para `Reaja com +1 para confirmar ciência do encerramento.`
- **Parser de data (`scheduler_parser.py`)**: Continuar aceitando ambos os formatos (`DD-MM-YYYY` e `DD/MM/YYYY`), mas documentar preferência pelo formato com barra
- **Timezone configurável**: Adicionar variável de ambiente `TRIAGE_DEFAULT_TIMEZONE` (default: `America/Bahia`) para evitar hardcode de timezone

## Capabilities

### New Capabilities

- `room3-scheduling-messages`: Especifica o formato e conteúdo das mensagens de solicitação de agendamento, template de resposta, e confirmação no Room-3, incluindo requisitos de ortografia, formato de data, e timezone configurável.

### Modified Capabilities

- `room2-structured-reply-decision`: Estende o snapshot de decisão do médico para incluir `doctor_display_name`, permitindo que o nome seja exibido nas mensagens subsequentes do Room-3.

## Impact

### Código Afetado

- `src/triage_automation/infrastructure/matrix/message_templates.py`:
  - `build_room3_request_message()` - adicionar parâmetro `doctor_display_name` e linha no output
  - `build_room3_reply_template_message()` - corrigir ortografia e formato de data
  - `build_room3_ack_message()` - atualizar texto de confirmação
  - `build_room3_invalid_format_reprompt()` - atualizar formato de data no template de erro
- `src/triage_automation/domain/scheduler_parser.py`:
  - Manter suporte a ambos os formatos de data (já suportado)
  - Usar timezone da env var ao invés de hardcoded
- `src/triage_automation/application/ports/case_repository_port.py`:
  - `CaseDoctorDecisionSnapshot` - adicionar campo `doctor_display_name`
- `src/triage_automation/infrastructure/db/case_repository.py`:
  - `get_case_doctor_decision_snapshot()` - fazer join com `case_matrix_message_transcripts` para recuperar `sender_display_name`
- `src/triage_automation/application/services/post_room3_request_service.py`:
  - Passar `doctor_display_name` para `build_room3_request_message()`
- `src/triage_automation/infrastructure/config/settings.py`:
  - Adicionar `TRIAGE_DEFAULT_TIMEZONE` (default: `America/Bahia`)

### Testes Afetados

- `tests/unit/test_room1_room3_message_templates.py`
- `tests/unit/test_scheduler_parser.py`
- `tests/integration/test_room3_scheduler_reply_flow.py`

### Migração de Banco

- Nenhuma migração necessária (dados já estão disponíveis em `case_matrix_message_transcripts.sender_display_name`)

### Dependências

- Nenhuma nova dependência

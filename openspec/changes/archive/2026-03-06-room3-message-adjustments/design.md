# room3-message-adjustments Design

## Context

O sistema de triagem utiliza três salas Matrix para orquestrar o fluxo de casos:
- **Room-1**: Recepção inicial
- **Room-2**: Avaliação médica (médico decide aceitar/negar)
- **Room-3**: Agendamento de exames

Atualmente, as mensagens do Room-3 têm inconsistências que prejudicam a experiência do usuário:
1. Ortografia incorreta (`instrucoes` sem acento/cedilha)
2. Formato de data não-convencional para usuários brasileiros (`DD-MM-YYYY`)
3. Mensagem de confirmação ambígua
4. Falta de informação sobre qual médico aceitou o caso

O nome do médico já é capturado no momento da decisão (Room-2) via `case_matrix_message_transcripts.sender_display_name`, mas não é repassado para as mensagens do Room-3.

## Goals / Non-Goals

**Goals:**

1. Corrigir ortografia das mensagens do Room-3 (`instruções` com acento e cedilha)
2. Padronizar formato de data para `DD/MM/YYYY HH:MM` (formato brasileiro)
3. Tornar o timezone configurável via env var (evitar hardcode)
4. Adicionar nome do médico que aceitou o caso na mensagem de solicitação do Room-3
5. Melhorar clareza da mensagem de ack (confirmar "ciência do encerramento")

**Non-Goals:**

1. Não alterar o parser de data - ele já aceita ambos os formatos e continuará aceitando
2. Não adicionar migração de banco - dados já existem em `case_matrix_message_transcripts`
3. Não alterar mensagens do Room-1 ou Room-2
4. Não modificar o fluxo de estado do caso

## Decisions

### D1: Recuperar nome do médico via JOIN no snapshot

**Decisão:** Estender `CaseDoctorDecisionSnapshot` para incluir `doctor_display_name`, recuperado via JOIN com `case_matrix_message_transcripts` onde `message_type = 'room2_doctor_reply'`.

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|-------------|------|---------|
| **A) JOIN no snapshot (escolhida)** | Sem migração, usa dados existentes, consulta única | Query levemente mais complexa |
| B) Adicionar coluna `doctor_display_name` em `cases` | Query mais simples | Requer migration, dado duplicado |
| C) Chamada HTTP ao Matrix no momento do post | Sempre atualizado | Latência extra, pode falhar |

**Racional:** A alternativa A é a mais simples e não requer mudanças de schema. O dado já está disponível e confiável.

### D2: Timezone via variável de ambiente

**Decisão:** Adicionar `TRIAGE_DEFAULT_TIMEZONE` nas settings, com default `America/Bahia` (BRT).

**Alternativas consideradas:**

| Alternativa | Prós | Contras |
|-------------|------|---------|
| **A) Env var (escolhida)** | Configurável por ambiente, sem redeploys | Precisa ser documentada |
| B) Hardcode `America/Bahia` | Simples | Inflexível para outros timezones |
| C) Detectar do cliente Matrix | Automático | Matrix não expõe timezone do cliente |

**Racional:** Env var é o padrão do projeto para configurações de ambiente (ver `settings.py`).

### D3: Manter compatibilidade de parser

**Decisão:** O parser de data continuará aceitando ambos os formatos (`DD-MM-YYYY` e `DD/MM/YYYY`). Apenas o template visual mudará para mostrar preferência pelo formato com barra.

**Racional:** Evita quebrar respostas existentes ou de usuários acostumados com o formato anterior.

## Risks / Trade-offs

### R1: Nome do médico pode não estar disponível

**Risco:** Se o transcript `room2_doctor_reply` não tiver `sender_display_name` (ex: usuário sem display name configurado), o campo ficará vazio.

**Mitigação:** Fallback para `"não informado"` quando `doctor_display_name` for `None` ou vazio.

### R2: Timezone mal configurado

**Risco:** Se `TRIAGE_DEFAULT_TIMEZONE` for configurado com valor inválido, o sistema pode falhar ao criar objetos `ZoneInfo`.

**Mitigação:** Validar o timezone no startup da aplicação (em `settings.py`) e falhar rápido com mensagem clara.

### R3: Breaking change no formato visual do template

**Risco:** Usuários acostumados com `DD-MM-YYYY` podem se confundir inicialmente.

**Mitigação:** O parser continua aceitando o formato antigo, então não há quebra funcional. Apenas o template visual muda.

## Migration Plan

1. **Deploy da mudança:**
   - Adicionar `TRIAGE_DEFAULT_TIMEZONE` ao `.env` (ou usar default)
   - Deploy normal da aplicação

2. **Rollback:**
   - Reverter deploy
   - Sem necessidade de rollback de banco (sem migrations)

3. **Validação:**
   - Verificar logs de startup para confirmação de timezone válido
   - Testar fluxo completo Room-2 → Room-3 em ambiente de staging

## Open Questions

Nenhuma questão em aberto. Todos os pontos foram esclarecidos na fase de discovery.

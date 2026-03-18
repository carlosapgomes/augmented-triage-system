# Design

## Context

O builder `build_room3_request_message` reutiliza `_build_room3_details_block`, que já sabe renderizar `paciente pediátrico: sim|não` quando recebe `pediatric_flag`. O problema atual está na orquestração de `PostRoom3RequestService`, que extrai nome, idade e exame solicitado, mas não extrai nem repassa a flag pediátrica para o builder da mensagem inicial de agendamento.

## Goals / Non-Goals

**Goals:**

- Exibir contexto pediátrico na mensagem `room3_request` quando o caso estiver marcado como pediátrico.
- Reaproveitar o mecanismo determinístico já usado nos fluxos de Room-1 final e Room-3 immediate.
- Cobrir o ajuste com testes direcionados.

**Non-Goals:**

- Alterar o template puro de resposta da Room-3.
- Mudar parsing do scheduler, estados do fluxo ou mensagens finais da Room-1.
- Redesenhar a regra de detecção pediátrica.

## Decisions

### Decision 1: Reutilizar `extract_pediatric_flag` no serviço da Room-3

- Escolha: extrair `pediatric_flag` em `PostRoom3RequestService` usando o helper compartilhado `extract_pediatric_flag`.
- Racional: mantém alinhamento com os outros fluxos já corretos e evita duplicar heurística de idade ou leitura do payload estruturado.

### Decision 2: Estender apenas o builder de `room3_request`

- Escolha: adicionar `pediatric_flag` à assinatura de `build_room3_request_message` e repassar ao bloco de detalhes já existente.
- Racional: a infraestrutura de apresentação já suporta a linha pediátrica; o ajuste mínimo é apenas ligar o parâmetro faltante.

## Risks / Trade-offs

- [Risk] Casos explicitamente não pediátricos podem passar a exibir `paciente pediátrico: não` se o fluxo optar por repassar a flag em ambos os estados.
  - Mitigação: o slice será validado com testes para o comportamento desejado e limitado à mensagem `room3_request`, sem ampliar escopo para outros builders nesta etapa.

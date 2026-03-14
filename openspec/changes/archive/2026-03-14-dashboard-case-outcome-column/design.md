# Design: Dashboard Case Outcome Column

## Context

A listagem de casos no dashboard já exibe identificador, status técnico e atividade mais recente, mas não mostra explicitamente o desfecho operacional para leitura rápida da equipe. O dado necessário já existe no banco (`doctor_decision` e `appointment_status`), porém hoje não é projetado na consulta nem renderizado como coluna dedicada.

## Goals / Non-Goals

**Goals:**

- Exibir na lista de casos uma coluna de desfecho operacional com leitura direta (`ACEITO`, `NEGADO`, `EM_ANDAMENTO`).
- Derivar o desfecho a partir de campos já persistidos, sem criar nova migração.
- Manter compatibilidade com arquitetura atual (`application`/`ports`/`infrastructure`) e sem alterar transições do workflow.
- Cobrir o comportamento com testes de integração da página de dashboard.

**Non-Goals:**

- Não alterar regras de negócio de decisão médica/agendamento.
- Não alterar contratos de callback, prompts ou parser de Room-2/Room-3.
- Não criar novos estados no `CaseStatus`.
- Não redesenhar a experiência visual além de acrescentar a nova coluna.

## Decisions

### Decision 1: Derivar desfecho na projeção de listagem do repositório

- Escolha: incluir `doctor_decision` e `appointment_status` na query de listagem e calcular `case_outcome` no adapter `SqlAlchemyCaseRepository` antes de montar `CaseMonitoringListItem`.
- Racional: mantém a regra centralizada na camada de dados usada por dashboard e evita lógica de derivação em template/router.
- Alternativa considerada: derivar no template Jinja.
- Motivo da rejeição: duplicaria regra de mapeamento em camada de apresentação e reduziria testabilidade unitária/integrada.

### Decision 2: Ordem de precedência de desfecho

- Escolha: aplicar precedência determinística:
  1. `appointment_status == confirmed` -> `ACEITO`
  2. `appointment_status == denied` -> `NEGADO`
  3. `doctor_decision == deny` -> `NEGADO`
  4. Demais casos -> `EM_ANDAMENTO`
- Racional: privilegia desfecho final de agendamento quando presente; usa negativa médica como fallback quando fluxo encerra antes do Room-3; mantém estado neutro para casos ainda em processamento.
- Alternativa considerada: mapear apenas por `CaseStatus` terminal.
- Motivo da rejeição: pode perder semântica quando campos de decisão já existem mas status técnico ainda está em transição intermediária.

### Decision 3: Expandir contrato de item de monitoramento com campo explícito

- Escolha: adicionar campo `case_outcome` em `CaseMonitoringListItem` (port de aplicação) e usá-lo diretamente no fragmento `cases_list_fragment.html`.
- Racional: deixa o contrato explícito e evita inferência implícita em múltiplas camadas.
- Alternativa considerada: reutilizar apenas `status` para inferir no frontend.
- Motivo da rejeição: status técnico não representa de forma clara o desfecho operacional solicitado.

## Risks / Trade-offs

- [Risco] Casos legados com dados incompletos podem aparecer como `EM_ANDAMENTO` mesmo já encerrados em versões antigas.
  - Mitigação: fallback explícito e previsível; futuras melhorias podem tratar retrocompatibilidade histórica se necessário.
- [Trade-off] Introdução de um novo campo no contrato interno de listagem exige ajuste em testes e possíveis consumidores indiretos.
  - Mitigação: mudança é pequena, tipada e coberta por testes de integração do dashboard.

## Migration Plan

1. Adicionar/ajustar teste de integração da página para validar presença da coluna e rótulos de desfecho.
2. Atualizar contrato `CaseMonitoringListItem` e implementação de `list_cases_for_monitoring` para produzir `case_outcome`.
3. Atualizar template de listagem para renderizar a nova coluna.
4. Executar validações alvo (`pytest`, `ruff`, `mypy`, `markdownlint`).

Rollback:

- Reverter o commit do change; como não há migração de banco, rollback é apenas de código/template.

## Open Questions

- Confirmar nomenclatura final no UI: manter `ACEITO`/`NEGADO`/`EM_ANDAMENTO` (técnico) ou usar versão mais amigável (`Em andamento`) para operação.

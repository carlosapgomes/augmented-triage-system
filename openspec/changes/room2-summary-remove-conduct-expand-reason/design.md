# Design: Sala 2 sem conduta e com motivo objetivo expandido

## Context

A mensagem II da Sala 2 (`room2_case_summary`) foi desenhada para apoiar decisão médica rápida, mas hoje ainda inclui o bloco `Conduta sugerida` e limita `Motivo objetivo` a formato muito curto (com truncamento agressivo). Na prática, isso conflita com o posicionamento esperado do bot (sugerir aceitar/negar com justificativa) e reduz a utilidade do motivo para a tomada de decisão.

O fluxo de decisão estruturada em Room-2 já está estável e não deve ser alterado: mensagem I (PDF), mensagem II (resumo técnico), mensagem III (template de resposta). A mudança é exclusivamente de contrato de apresentação da mensagem II (Markdown e `formatted_body` HTML), preservando máquina de estados, parser estrito de resposta médica e persistência de artefatos.

## Goals / Non-Goals

**Goals:**

- Remover `Conduta sugerida` da mensagem II em texto e HTML.
- Rebalancear o espaço da mensagem para fortalecer `Motivo objetivo`.
- Reduzir truncamento do motivo, permitindo justificativa mais completa e objetiva.
- Manter coerência explícita entre decisão sugerida, suporte recomendado e motivo.
- Preservar o combo de três mensagens e contratos de reply/parsing já existentes.

**Non-Goals:**

- Não alterar workflow de estados do caso.
- Não alterar schema/prompts de LLM1/LLM2.
- Não alterar contratos do template de resposta estruturada do médico (mensagem III).
- Não introduzir novos campos persistidos ou migração de banco.

## Decisions

### Decision 1: Remover bloco de conduta apenas na camada de template

- Escolha: excluir a seção `Conduta sugerida` dos builders de mensagem II (`body` e `formatted_body`), sem alterar serviços de decisão ou adapters de parsing.
- Racional: a regra de posicionamento do bot é editorial/de apresentação e não de estado de domínio.
- Alternativas consideradas:
  - manter conduta opcional em alguns casos;
  - mover conduta para mensagem separada.
- Motivo da rejeição:
  - mantém ambiguidade de escopo do bot;
  - aumenta ruído operacional no Room-2.

### Decision 2: Priorizar completude do motivo objetivo com limite menos restritivo

- Escolha: substituir limitação curta baseada em 1 linha/limite rígido por regra que preserve justificativa mais completa no `Motivo objetivo`, com truncamento apenas como proteção final.
- Racional: a justificativa é o principal insumo textual para decidir aceitar/negar quando o médico lê rapidamente.
- Alternativas consideradas:
  - manter limite atual e apenas remover conduta;
  - remover qualquer limite de tamanho.
- Motivo da rejeição:
  - limite atual já comprovou perda de informação relevante;
  - ausência total de limite pode degradar legibilidade em casos extremos.

### Decision 3: Atualizar contrato de capability para layout sem conduta

- Escolha: ajustar delta specs para refletir que a mensagem II mantém blocos clínicos e de decisão, mas sem `Conduta sugerida`.
- Racional: o comportamento esperado precisa ficar explícito e testável no contrato OpenSpec.
- Alternativas consideradas:
  - tratar como detalhe de implementação sem mudança de spec.
- Motivo da rejeição:
  - listas de seções obrigatórias fazem parte do comportamento funcional observado no Room-2.

### Decision 4: Preservar regra de prioridade emergente dentro do motivo

- Escolha: quando houver contexto de sangramento com instabilidade hemodinâmica documentada, a frase de prioridade emergente deve permanecer no `Motivo objetivo`.
- Racional: remove-se conduta sem perder sinal crítico de urgência clínica.
- Alternativas consideradas:
  - descartar frase emergente junto com a conduta.
- Motivo da rejeição:
  - risco de perda de alerta clínico importante no resumo.

## Risks / Trade-offs

- [Risk] Motivo expandido ficar longo demais em casos com rationale extensa.
  - Mitigação: manter teto de proteção e truncamento controlado apenas no fim, preservando a parte causal principal.

- [Risk] Regressões em testes que hoje exigem seção de conduta e limites antigos.
  - Mitigação: atualizar testes unitários/integrados com TDD (red/green) para o novo contrato de layout e tamanho.

- [Trade-off] Menos orientação operacional explícita no texto do bot.
  - Mitigação: manter foco da mensagem em decisão + justificativa, com contexto clínico e pendências já presentes nos blocos anteriores.

## Migration Plan

1. Atualizar testes unitários de templates Room-2 para falhar sem a remoção de `Conduta sugerida` e sem expansão de `Motivo objetivo`.
2. Ajustar builders da mensagem II (texto e HTML) removendo conduta e revisando regras de truncamento do motivo.
3. Atualizar testes de integração que validam conteúdo final da mensagem publicada na Sala 2.
4. Executar validações obrigatórias do slice (`pytest` alvo, `ruff`, `mypy`, `markdownlint`).
5. Rollback: reverter commit de templates/testes para restaurar formato anterior, sem migração de banco.

## Open Questions

- Nenhuma no momento.

# Design

## Context

A Room-2 publica um resumo técnico em markdown e também `formatted_body` HTML no Matrix. Mesmo quando a equipe consome majoritariamente markdown, os testes e o transporte atual validam ambos os formatos.

O pedido funcional é estrito em três eixos:

- procedência (cidade/hospital/unidade, com UF opcional);
- exames explicitamente mais recentes;
- transfusão sempre respondida de forma binária (`sim`/`não`), sem estado indeterminado.

Além disso, o fluxo já existente depende de validação rígida do schema LLM1 (`extra=forbid`) e de prompts versionados em `prompt_templates`, o que exige alteração coordenada de contrato + prompt + renderização.

## Goals / Non-Goals

**Goals:**

- Adicionar ao contrato LLM1 campos estruturados para origem, recência de exames e transfusão.
- Tornar a extração instruída por prompt e auditável via nova versão de prompt template.
- Exibir no relatório da Room-2, de forma explícita:
  - origem com fallback `sem evidência no laudo`;
  - exames marcados com `(mais recente)`;
  - `Há relato de transfusão? sim|não` e, quando `sim`, total de unidades e hemocomponente.
- Implementar em fases sequenciais com slices verticais pequenos e TDD.

**Non-Goals:**

- Redesenhar o motor de decisão clínica (rulebook) ou gates determinísticos.
- Alterar parser de resposta médica da Room-2.
- Introduzir lógica de negócio em adapters.

## Decisions

### Decision 1: Contrato LLM1 explícito para origem/transfusão/exames

- Escolha: estender `Llm1Response` com modelos dedicados para:
  - origem: cidade/hospital/unidade/UF opcional + hint de evidência;
  - transfusão: `had_transfusion` binário (`yes|no`) + `total_units` inteiro opcional + `hemocomponent` opcional;
  - exames rastreados: coleção estruturada com tipo, valor/resumo, data/hora opcional e marcador de recência.
- Racional: sem contrato explícito, a Room-2 dependeria de texto livre e perderia determinismo/validabilidade.

### Decision 2: Ausência de evidência de transfusão vira negativa explícita

- Escolha: prompt e renderização tratam ausência de evidência como `não`.
- Racional: requisito do solicitante restringe a resposta a `sim|não` e remove estado indeterminado.

### Decision 3: Regra de recência determinística

- Escolha:
  - priorizar data/hora explícita para selecionar item mais recente por tipo;
  - sem data/hora, permitir fallback por posição textual;
  - em empate, adotar última ocorrência no texto.
- Racional: regra previsível e alinhada ao fluxo de extração textual já existente.

### Decision 4: Manter paridade markdown + HTML

- Escolha: atualizar markdown e HTML da mensagem Room-2 no mesmo slice funcional.
- Racional: pipeline Matrix envia ambos (`body` e `formatted_body`) e testes de integração validam os dois caminhos.

### Decision 5: Versionamento de prompt via Alembic

- Escolha: criar nova migração de prompt template para `llm1_system`/`llm1_user` (v6), ativando a nova versão e desativando a anterior.
- Racional: mantém trilha de auditoria e rollback consistente com padrão do repositório.

## Data Contract Outline

Campos planejados (nomes finais podem ajustar para compatibilidade com padrões atuais):

- `origin_context`
  - `city: str | None`
  - `hospital: str | None`
  - `unit: str | None`
  - `state_uf: str | None`
  - `source_text_hint: str | None`
- `transfusion`
  - `had_transfusion: Literal["yes", "no"]`
  - `total_units: int | None`
  - `hemocomponent: str | None`
  - `source_text_hint: str | None`
- `tracked_exams` (lista)
  - `exam_type: str`
  - `exam_label: str | None`
  - `result_value: str | None`
  - `exam_datetime_iso: str | None`
  - `is_most_recent: bool`
  - `source_text_hint: str | None`

## Slice Strategy

Fases sequenciais e slices verticais, cada um alterando o mínimo de arquivos:

1. contrato LLM1 e validação;
2. prompt LLM1 e migração versionada;
3. renderização Room-2 (origem + transfusão);
4. renderização Room-2 (exames com recência);
5. atualização do cliente determinístico;
6. fechamento com relatório consolidado.

## Risks / Trade-offs

- [Risk] O texto clínico pode trazer datas incompletas/inconsistentes.
  - Mitigação: fallback explícito `recência indeterminada (sem data no laudo)` e regra de desempate por última ocorrência textual.
- [Risk] Crescimento excessivo da mensagem Room-2.
  - Mitigação: manter bloco enxuto, com apenas exames já rastreados pelo LLM1 e marcador curto `(mais recente)`.
- [Risk] Divergência markdown vs HTML.
  - Mitigação: testes unitários e de integração cobrindo os dois formatos no mesmo slice.

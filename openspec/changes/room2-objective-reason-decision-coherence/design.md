# Design técnico: coerência do motivo objetivo na Sala 2

## Context

A mensagem II da Sala 2 hoje é montada em `message_templates.py` a partir de `suggested_action_json` (LLM2 já reconciliado por política) e dados estruturados do caso. O bloco `Motivo objetivo` combina:

- uma frase fixa baseada em decisão/suporte;
- uma frase livre de `rationale.short_reason`.

Na prática, quando a política força `suggestion=deny`, o texto livre pode manter conteúdo de aceite e gerar contradição clínica no resumo final. Além disso, há desalinhamento semântico entre o resumo e a regra de decisão médica estruturada (`negar` exige `suporte=nenhum`).

Stakeholders principais: médicos reguladores da Sala 2 (consumidores diretos da mensagem), operação clínica (confiabilidade do resumo), engenharia (determinismo/testabilidade).

## Goals / Non-Goals

**Goals:**

- Garantir coerência determinística entre `Decisão sugerida`, `Suporte recomendado` e `Motivo objetivo` no resumo técnico da Sala 2.
- Para decisão `negar`, sempre exibir motivo objetivo de negativa com causa explícita e auditável (priorizando pendências críticas e exclusão de escopo).
- Para decisão `aceitar`, padronizar `Motivo objetivo` em frase curta de aceite com suporte, sem explicações adicionais.
- Impedir frases contraditórias (ex.: `negar` com texto de `aceitar`) por regra de construção no backend e por testes.

**Non-Goals:**

- Alterar workflow/state machine de casos.
- Redesenhar schema LLM2 v1.1.
- Alterar parser da resposta médica estruturada da Sala 2.
- Introduzir nova dependência externa.

## Decisions

### 1) Tratar coerência no render da mensagem (camada de template), não no prompt

**Escolha:** aplicar regra determinística em `_build_room2_objective_reason_lines` para derivar o texto final a partir da decisão reconciliada e dos campos estruturados.

**Racional:** o prompt melhora qualidade, mas não garante coerência após overrides de política. O render é o último ponto de verdade antes da publicação em Matrix.

**Alternativas consideradas:**

- Reforçar somente `llm2_user/system`: reduz incidência, mas não elimina contradição pós-reconciliação.
- Reconciliar também `rationale` no `llm2_service`: melhora consistência do payload, mas ainda exige guarda no template para robustez.

### 2) Regra de saída por decisão final

**Escolha:**

- `deny` → `Motivo objetivo` deve conter apenas texto de negativa com causa explícita (sem frase de aceite e sem "com suporte ...").
- `accept` → `Motivo objetivo` deve ser apenas frase curta de aceite (`Aceito sem suporte adicional.` / `Aceito com suporte de anestesista.` / `Aceito com suporte de anestesista UTI.` / fallback para suporte desconhecido).

**Racional:** espelha a expectativa clínica do usuário e reduz ruído cognitivo na leitura rápida.

**Alternativas consideradas:**

- Manter frase fixa "Decisão X com suporte Y" para ambos os caminhos: simples, porém continua pouco clínica e gera ambiguidades para `deny`.

### 3) Prioridade determinística para motivo de negativa

**Escolha:** ao negar, selecionar causa na ordem:

1. fora do fluxo EDA (`excluded_from_eda_flow` / `excluded_request`);
2. pendência laboratorial obrigatória (`labs_required=true` e `labs_pass!=yes`, usando `labs_failed_items` quando disponível);
3. ECG obrigatório ausente (`ecg_required=true` e `ecg_present!=yes`);
4. fallback de segurança quando faltarem detalhes.

Quando houver múltiplas pendências, compor frase única com lista curta e objetiva.

**Racional:** explicação auditável e alinhada a gatilhos de política já existentes.

**Alternativas consideradas:**

- Usar `rationale.short_reason` sempre: não determinístico e sujeito a contradição semântica.

### 4) Testes de regressão explícitos de anti-contradição

**Escolha:** ampliar testes unitários e de integração para verificar:

- `deny` nunca contém tokens de aceite no `Motivo objetivo`;
- `deny` contém causa explícita de negativa quando há pendência estrutural;
- `accept` usa exclusivamente frase curta de aceite com suporte;
- payloads com `short_reason` conflitante não vazam contradição no resumo renderizado.

**Racional:** garante estabilidade em alterações futuras de prompt/template.

## Risks / Trade-offs

- **[Risco]** Causa de negativa ficar genérica em casos com dados incompletos. → **Mitigação:** fallback explícito de segurança e cobertura de teste para ausência de detalhes.
- **[Risco]** Mudança textual quebrar asserts rígidos de testes existentes. → **Mitigação:** atualizar asserts por contrato semântico (coerência + presença de causa), não por frase legada.
- **[Trade-off]** Menos liberdade narrativa para `accept`. → **Mitigação:** intencional para reduzir variação e acelerar leitura clínica.

## Migration Plan

1. Atualizar regras de montagem de `Motivo objetivo` no template da Sala 2.
2. Atualizar testes unitários de `room2_message_templates` para novo contrato textual.
3. Atualizar testes de integração de `post_room2_widget` para refletir novos textos esperados.
4. Validar com suíte direcionada (pytest + ruff + mypy nos caminhos alterados).
5. Rollback simples: reverter commit caso haja impacto operacional inesperado.

## Open Questions

- Em `deny`, o bloco `Suporte recomendado` deve sempre exibir `nenhum` no resumo (mesmo que payload legado traga outro valor), ou apenas no `Motivo objetivo`?
- Em casos com múltiplas pendências, qual limite máximo de itens na frase de negativa antes de truncar?
- A frase de prioridade emergente deve permanecer apenas para `accept` ou também pode coexistir em negativas por pendência documental?

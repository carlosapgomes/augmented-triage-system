# Sala 2: coerência entre decisão final e motivo objetivo no resumo técnico

## Why

O resumo técnico da Sala 2 está exibindo contradições no bloco `Motivo objetivo`, com casos em que a decisão sugerida é `negar` mas o texto inclui recomendação de `aceitar` ou frase de suporte incompatível. Isso reduz a confiança clínica no resumo e dificulta a justificativa objetiva da negativa quando há pendências críticas (ex.: exame obrigatório ausente).

## What Changes

- Definir regra determinística de composição do `Motivo objetivo` baseada na decisão final exibida no resumo da Sala 2.
- Para `negar`, exigir motivo objetivo de negação com causa explícita e verificável (ex.: exame obrigatório ausente, pendência laboratorial obrigatória, solicitação fora de escopo), sem frases de aceite.
- Para `aceitar`, padronizar mensagem curta e direta no formato `Aceito com suporte ...` (ou sem suporte), sem explicações adicionais.
- Eliminar combinações contraditórias no resumo (ex.: `negar` com frase de aceite; `negar` com suporte não coerente com negativa).
- Cobrir regras com testes unitários e de integração para garantir comportamento determinístico e evitar regressão.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `room2-concise-medical-opinion-message`: ajusta o contrato textual de `Motivo objetivo` para garantir coerência estrita com a decisão final e explicitação objetiva da negativa.
- `room2-structured-reply-decision`: atualiza o contrato da mensagem II para impedir conteúdo contraditório entre `Decisão sugerida`, `Suporte recomendado` e `Motivo objetivo`.

## Impact

- Código potencialmente afetado:
  - `src/triage_automation/infrastructure/matrix/message_templates.py`
  - (se necessário para reconciliação de apresentação) `src/triage_automation/application/services/llm2_service.py`
  - (se necessário para regra determinística) `src/triage_automation/domain/policy/eda_policy.py`
- Testes potencialmente afetados:
  - `tests/unit/test_room2_message_templates.py`
  - `tests/integration/test_post_room2_widget.py`
- Sem impacto esperado em parser da resposta médica da Sala 2, workflow de estados do caso, ou contratos externos de API.

# Design: eda-scope-gate-explicit-eda-fallback

## Contexto

O gate de escopo atual depende primariamente de `preop_screening.exam_type` produzido pelo LLM1. Quando esse campo retorna `unknown`, o fluxo segue para revisão manual obrigatória, mesmo na presença de texto explícito de solicitação EDA no relatório.

## Objetivo do design

Adicionar um fallback determinístico e explicável para reduzir falso negativo de escopo EDA sem enfraquecer exclusões de segurança já existentes.

## Decisões

### 1) Fallback positivo de EDA somente para `unknown`

- Aplicar fallback apenas quando `exam_type` inicial for `unknown`.
- Buscar termos explícitos de EDA em candidatos textuais já utilizados no gate (texto limpo, campos estruturados e evidências).

### 2) Preservar precedência de exclusões non-EDA

- Se houver termos non-EDA detectados (`gastrostomia/GTT/PEG`, `dilatação esofágica`), manter `non_eda` e revisão manual, mesmo com menção a EDA no documento.

### 3) Evidência explicável

- Quando houver promoção `unknown -> eda`, anexar `evidence_spans` com `field_path` determinístico para auditoria diagnóstica.

## Fluxo atualizado (resumo)

1. Ler `exam_type` vindo do LLM1.
2. Detectar termos non-EDA (lógica existente).
3. Se `exam_type=unknown` e sem non-EDA, detectar termos explícitos de EDA.
4. Se detectar EDA explícito, promover para `eda` e não acionar gate de revisão manual.
5. Seguir fluxo normal de LLM2/política determinística EDA.

## Riscos e mitigação

- **Risco:** falso positivo de EDA por menção incidental.
  - **Mitigação:** termos de detecção focados em solicitação/procedimento EDA, não apenas palavra solta genérica.
- **Risco:** conflito entre sinais EDA e non-EDA.
  - **Mitigação:** exclusões non-EDA continuam com precedência.

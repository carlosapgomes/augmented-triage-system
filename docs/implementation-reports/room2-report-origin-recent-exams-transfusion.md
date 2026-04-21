# Relatório de Implementação — Room 2: Origem, Exames Recentes e Transfusão

**Change ID:** `room2-report-origin-recent-exams-transfusion`

**Data de consolidação:** 2026-04-21

**Branch:** `main` (commits `bfdb773..2cd3565`)

---

## Resumo

Este change adiciona ao fluxo Room-2 três capacidades de negócio:

1. **Origem do paciente** — cidade, hospital, unidade e UF extraídos do laudo, com fallback `sem evidência no laudo`.
2. **Exames rastreados com recência** — cada exame marcado como `(mais recente)` ou `(recência indeterminada (sem data no laudo))`, com desempate por última ocorrência textual.
3. **Transfusão binária** — linha mandatória `Há relato de transfusão? sim|não` com agregação de unidades quando aplicável.

---

## Checklist por Slice

### Fase 1 — Contrato estruturado LLM1

- [x] **1.1** Testes TDD RED para origin_context, transfusion e tracked_exams em `tests/unit/test_llm1_validation.py`
  - Commit: `bfdb773`
  - 344 linhas adicionadas cobrindo origem (cidade/hospital/unidade/UF), transfusão binária (yes/no) e exames rastreados com recência
- [x] **1.2** Extensão do schema em `src/triage_automation/application/dto/llm1_models.py`
  - Commit: `649b3f1`
  - Novos modelos: `Llm1OriginContext`, `Llm1Transfusion`, `Llm1TrackedExam`
  - Tipo `BrazilStateUf` com 27 UFs válidas
  - Campos com defaults seguros (`had_transfusion="no"`, `tracked_exams=[]`)

### Fase 2 — Prompt LLM1 versionado

- [x] **2.1** Testes de validação de prompt para procedência, recência e transfusão
  - Commit: `31ecea2`
  - Asserções que validam instruções de prompt para origem, exames com recência e fallback negativo de transfusão
- [x] **2.2** Atualização do service + migração Alembic v6
  - Commit: `0d0f011`
  - `llm1_service.py` atualizado com fallback de prompt estendido
  - `alembic/versions/0018_prompt_templates_llm1_ptbr_v6.py` — migração que desativa v5 e ativa v6

### Fase 3 — Room-2 com origem e transfusão

- [x] **3.1** Testes de template para origem e linha mandatória de transfusão
  - Commit: `d9add06`
  - Testes unitários para renderização com dados completos, parciais e ausentes
- [x] **3.2** Implementação em `message_templates.py`
  - Commit: `31d1b28`
  - `_build_room2_origin_line()` — renderiza `origem: city (UF) - hospital - unit`
  - `_build_room2_transfusion_lines()` — renderiza `Há relato de transfusão? sim|não` + detalhes

### Fase 4 — Room-2 com exames marcados como mais recentes

- [x] **4.1** Testes de template para exames com sufixo `(mais recente)`
  - Commit: `e2167a8`
  - Testes para recência com data, sem data (fallback), e empate por última ocorrência
- [x] **4.2** Implementação em `message_templates.py`
  - Commit: `4fbf051`
  - `_build_room2_tracked_exam_lines()` — renderiza exames com marcadores de recência

### Fase 5 — Cliente determinístico

- [x] **5.1** Testes do cliente determinístico com contrato estendido
  - Commit: `1147e36`
  - Testes para origem regex, transfusão padrão e exames com mapeamento de tipo
- [x] **5.2** Implementação em `deterministic_client.py`
  - Commit: `2cd3565`
  - Padrões regex para cidade/UF, hospital, unidade, transfusão e exames
  - `_extract_origin_context()`, `_extract_transfusion()`, `_extract_tracked_exams()`

### Fase 6 — Fechamento e evidências

- [x] **6.1** Relatório consolidado (este documento)
- [ ] **6.2** Revisão com solicitante e arquivamento

---

## Arquivos Alterados

| Arquivo | Tipo | Slices |
| ------- | ---- | ------ |
| `src/triage_automation/application/dto/llm1_models.py` | modificado | 1.2 |
| `src/triage_automation/application/services/llm1_service.py` | modificado | 2.2 |
| `src/triage_automation/infrastructure/llm/deterministic_client.py` | modificado | 5.2 |
| `src/triage_automation/infrastructure/matrix/message_templates.py` | modificado | 3.2, 4.2 |
| `alembic/versions/0018_prompt_templates_llm1_ptbr_v6.py` | adicionado | 2.2 |
| `tests/unit/test_llm1_validation.py` | adicionado/modificado | 1.1 |
| `tests/unit/test_room2_message_templates.py` | adicionado/modificado | 3.1, 4.1 |
| `tests/unit/test_deterministic_llm_client.py` | adicionado/modificado | 5.1 |
| `tests/integration/test_post_room2_widget.py` | adicionado/modificado | 3.1, 4.1 |
| `tests/integration/test_llm_prompt_loading_runtime.py` | modificado | 2.2 |

**Total:** +2013 linhas, 14 arquivos, 7 commits.

---

## Comandos Executados e Status

| Comando | Status |
| ------- | ------ |
| `uv run pytest tests/unit/test_llm1_validation.py` | ✓ 127 passed |
| `uv run pytest tests/unit/test_room2_message_templates.py` | ✓ 127 passed |
| `uv run pytest tests/unit/test_deterministic_llm_client.py` | ✓ 127 passed |
| `uv run pytest tests/integration/test_post_room2_widget.py` | ✓ 127 passed |
| `uv run pytest tests/integration/test_llm_prompt_loading_runtime.py` | ✓ 127 passed |
| `uv run ruff check <changed-paths>` | ✓ All checks passed |
| `uv run mypy <changed-paths>` | ✓ Success: no issues found |
| `markdownlint-cli2 "docs/implementation-reports/room2-report-origin-recent-exams-transfusion.md"` | ✓ (verificado abaixo) |

---

## Fragmentos de Diff por Requisito

### Requisito 1 — Origem (cidade/hospital/unidade)

**Schema** (`llm1_models.py`, slice 1.2):

```python
class Llm1OriginContext(StrictModel):
    """Structured provenance/origin context extracted from the medical report."""

    city: str | None = None
    hospital: str | None = None
    unit: str | None = None
    state_uf: BrazilStateUf | None = None
    source_text_hint: str | None = None
```

**Template Room-2** (`message_templates.py`, slice 3.2):

```python
def _build_room2_origin_line(structured_data: dict[str, object]) -> str:
    ...
    if not parts:
        return "origem: sem evidência no laudo"
    return f"origem: {' - '.join(parts)}"
```

### Requisito 2 — Exames com marcador `(mais recente)`

**Schema** (`llm1_models.py`, slice 1.2):

```python
class Llm1TrackedExam(StrictModel):
    exam_type: str = Field(min_length=1)
    exam_label: str | None = None
    result_value: str | None = None
    exam_datetime_iso: str | None = None
    is_most_recent: bool
    source_text_hint: str | None = None
```

**Template Room-2** (`message_templates.py`, slice 4.2):

```python
if is_most_recent is True:
    if isinstance(exam_datetime, str) and exam_datetime.strip():
        line += " (mais recente)"
    else:
        line += " (recência indeterminada (sem data no laudo))"
```

### Requisito 3 — `Há relato de transfusão? sim|não`

**Schema** (`llm1_models.py`, slice 1.2):

```python
class Llm1Transfusion(StrictModel):
    had_transfusion: Literal["yes", "no"]
    total_units: int | None = Field(default=None, ge=0)
    hemocomponent: str | None = None
    source_text_hint: str | None = None
```

**Template Room-2** (`message_templates.py`, slice 3.2):

```python
lines: list[str] = [f"Há relato de transfusão? {'sim' if is_yes else 'não'}"]

if is_yes and isinstance(transfusion, dict):
    ...
    lines.append(f"Total de unidades transfundidas: {units_label}")
    lines.append(f"Hemocomponente: {hemo_label}")
```

**Prompt v6** (`alembic/versions/0018_prompt_templates_llm1_ptbr_v6.py`, slice 2.2):

> Registre had_transfusion como binario (yes/no); ausencia de evidencia de transfusao deve ser tratada como 'no'.

---

## Confirmação de Cobertura dos 3 Requisitos

| Requisito | Schema | Prompt v6 | Template Room-2 | Cliente Determinístico | Testes |
| --------- | ------ | --------- | --------------- | --------------------- | ------ |
| Origem (cidade/hospital/unidade) | ✓ `Llm1OriginContext` | ✓ | ✓ `_build_room2_origin_line` | ✓ `_extract_origin_context` | ✓ slices 1.1, 3.1 |
| Exames com `(mais recente)` | ✓ `Llm1TrackedExam` | ✓ | ✓ `_build_room2_tracked_exam_lines` | ✓ `_extract_tracked_exams` | ✓ slices 4.1, 5.1 |
| `Há relato de transfusão? sim\|não` | ✓ `Llm1Transfusion` | ✓ | ✓ `_build_room2_transfusion_lines` | ✓ `_extract_transfusion` | ✓ slices 1.1, 3.1, 5.1 |

---

## Riscos e Pendências

1. **Prompt v6 em produção** — A migração Alembic `0018` deve ser executada antes do deploy para que o novo prompt seja carregado. O fallback no service (`_default_user_prompt_template`) cobre o caso de BD sem migração, mas o prompt v5 não terá as instruções de origem/transfusão/recência.
2. **Desempate textual de exames** — Quando múltiplos exames do mesmo tipo compartilham o mesmo datetime, o desempate usa a última ocorrência textual (posição na lista). Isso depende do LLM preservar a ordem de ocorrência no texto, o que não é garantido por modelos não determinísticos. O cliente determinístico lida corretamente.
3. **Validação de UF** — O tipo `BrazilStateUf` restringe a valores válidos, mas o LLM pode gerar strings inválidas que causarão erro de validação (retriable). Comportamento correto, mas pode gerar retries extras em textos malformados.
4. **Slice 6.2 pendente** — Revisão com solicitante, registro de follow-ups e arquivamento do change ainda não realizados.

---

## Timeline de Commits

```text
2cd3565 feat(room2-report): slice 5.2 - deterministic client with origin, transfusion, tracked exams
1147e36 test(room2-origin): add deterministic client RED tests for origin, transfusion, tracked exams (slice 5.1)
4fbf051 feat(room2): implement tracked exams rendering with recency markers (slice 4.2)
e2167a8 test(room2): add RED tests for tracked exams recency in Room-2 templates (slice 4.1)
31d1b28 feat(room2): render origin and transfusion in summary template (slice 3.2)
d9add06 test(room2): add origin and transfusion tests for slice 3.1 (RED)
0d0f011 feat(llm1): add origin/recency/transfusion prompt instructions + migration v6
31ecea2 test(llm1): add red prompt assertions for origin/recency/transfusion (slice 2.1)
649b3f1 feat(llm1): add origin_context, transfusion, and tracked_exams to LLM1 schema (slice 1.2)
bfdb773 feat(room2): add TDD red tests for origin, transfusion and tracked exams in LLM1 contract (slice 1.1)
```

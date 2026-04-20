# Slice Report 1.1 - testes de validação do contrato LLM1

## Objetivo

Adicionar testes TDD (RED) em `tests/unit/test_llm1_validation.py` para os novos campos estruturados do contrato LLM1:
- **origem** (`origin_context`): cidade/hospital/unidade/UF opcional
- **transfusão** (`transfusion`): resposta binária (`yes`/`no`), unidades inteiras, hemocomponente
- **exames rastreados** (`tracked_exams`): com marcador `is_most_recent` e data/hora opcional

## Arquivos alterados

- `tests/unit/test_llm1_validation.py` (modificado — 9 testes novos adicionados)
- `openspec/changes/room2-report-origin-recent-exams-transfusion/tasks.md` (modificado — item 1.1 marcado [x])

## Comandos executados + status

| Comando | Status |
|---|---|
| `uv run pytest tests/unit/test_llm1_validation.py -q` | **7 failed, 16 passed** (RED esperado) |
| `uv run ruff check tests/unit/test_llm1_validation.py` | **All checks passed!** |
| `uv run mypy tests/unit/test_llm1_validation.py` | 65 errors (38 pre-existing + 27 novos, todos do mesmo tipo `object not indexable`) |

## Evidência RED

### Testes que falharam (esperado — schema ainda não tem os campos)

1. `test_llm1_extracts_origin_context_with_all_fields` — `extra_forbidden` para `origin_context`
2. `test_llm1_extracts_origin_context_with_optional_fields_as_none` — `extra_forbidden` para `origin_context`
3. `test_llm1_extracts_transfusion_negative_response` — `extra_forbidden` para `transfusion`
4. `test_llm1_extracts_transfusion_positive_with_units` — `extra_forbidden` para `transfusion`
5. `test_llm1_extracts_tracked_exams_with_most_recent_flag` — `extra_forbidden` para `tracked_exams`
6. `test_llm1_extracts_tracked_exams_without_datetime` — `extra_forbidden` para `tracked_exams`
7. `test_llm1_extracts_tracked_exams_multiple_types_with_recency` — `extra_forbidden` para `tracked_exams`

### Testes que passaram (coincidência esperada no RED)

- `test_llm1_rejects_origin_context_with_invalid_state_uf` — levanta `Llm1RetriableError` (por `extra_forbidden`, não por validação de UF; corrigirá no GREEN)
- `test_llm1_rejects_transfusion_with_unknown_value` — levanta `Llm1RetriableError` (por `extra_forbidden`, não por validação de `unknown`; corrigirá no GREEN)

## Cobertura dos critérios de aceite

- [x] Cenários cobrindo origem (cidade/hospital/unidade/UF opcional)
- [x] Cenários cobrindo transfusão com resposta binária (`yes`/`no`) e unidades inteiras
- [x] Cenários cobrindo exames rastreados com marcação de item mais recente
- [x] Testes novos falham por ausência de implementação (RED)

## Diff snippets

### Novos testes adicionados (resumo)

```python
# Origem
def _payload_with_origin(agency_record, *, city, hospital, unit, state_uf, source_text_hint) -> dict
test_llm1_extracts_origin_context_with_all_fields()
test_llm1_extracts_origin_context_with_optional_fields_as_none()
test_llm1_rejects_origin_context_with_invalid_state_uf()

# Transfusão
def _payload_with_transfusion(agency_record, *, had_transfusion, total_units, hemocomponent, source_text_hint) -> dict
test_llm1_extracts_transfusion_negative_response()
test_llm1_extracts_transfusion_positive_with_units()
test_llm1_rejects_transfusion_with_unknown_value()

# Exames rastreados
def _payload_with_tracked_exams(agency_record, *, tracked_exams) -> dict
test_llm1_extracts_tracked_exams_with_most_recent_flag()
test_llm1_extracts_tracked_exams_without_datetime()
test_llm1_extracts_tracked_exams_multiple_types_with_recency()
```

## Riscos/pendências

- Os 2 testes de rejeição passam pelo motivo errado (`extra_forbidden`). No slice 1.2 (implementação do schema), será necessário verificar se eles falham pelo motivo correto e, se necessário, ajustar.
- Erros mypy (27 novos) são do mesmo tipo dos 38 pre-existentes — `dict[str, object]` indexado. Consistente com padrão do arquivo.
- Nenhum arquivo fora do escopo permitido foi alterado.

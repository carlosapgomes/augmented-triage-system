# Proposal: eda-scope-gate-explicit-eda-fallback

## Why

Alguns relatórios com texto explícito de solicitação EDA (por exemplo, "Motivo da Solicitação: Endoscopia Digestiva Alta - EDA") estão sendo classificados como `unknown` no `preop_screening.exam_type` e, por consequência, encerrados com revisão manual obrigatória indevida.

## What Changes

- Introduzir fallback determinístico para promover `exam_type=unknown` para `exam_type=eda` quando houver evidência textual explícita de solicitação EDA.
- Preservar precedência de exclusões já existentes (`gastrostomia/GTT/PEG` e `dilatação esofágica`) para evitar falso positivo de escopo EDA.
- Adicionar testes de regressão para garantir que casos com "Endoscopia Digestiva Alta - EDA" não sejam bloqueados no gate de escopo.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `eda-request-scope-gating`: Ajustar a lógica de gate para tratar evidência textual explícita de EDA como confirmação de escopo quando a extração LLM vier `unknown`.

## Impact

- `src/triage_automation/application/services/process_pdf_case_service.py`
- `tests/integration/test_process_pdf_case_llm2.py`
- Artefatos OpenSpec do change para rastreabilidade e verificação.

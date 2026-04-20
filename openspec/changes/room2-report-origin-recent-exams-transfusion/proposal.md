# Room-2 report origin recent exams transfusion

## Why

Usuários médicos em teste solicitaram três reforços obrigatórios no relatório técnico da Room-2 para apoiar o parecer clínico com menos ambiguidade:

- explicitar procedência (cidade/hospital/unidade de origem);
- explicitar que os exames mostrados são os mais recentes;
- afirmar de forma inequívoca se houve transfusão e, quando houver, a quantidade total de unidades e hemocomponente.

Hoje o contrato estruturado do LLM1 e o renderer da Room-2 não cobrem isso de forma determinística ponta a ponta.

## What Changes

- Estender o contrato estruturado do LLM1 com:
  - origem (cidade/hospital/unidade/UF opcional);
  - bloco de transfusão (resposta binária sim/não, total de unidades, hemocomponente);
  - coleção de exames rastreados com metadados de recência.
- Atualizar instruções do prompt LLM1 para extração robusta de origem, recência e transfusão.
- Versionar prompts LLM1 via migração Alembic em `prompt_templates`.
- Atualizar a mensagem técnica da Room-2 para renderizar explicitamente:
  - origem com fallback `sem evidência no laudo`;
  - exames com marcador `(mais recente)` e fallback de recência indeterminada quando sem data;
  - pergunta/linha mandatória `Há relato de transfusão? sim|não`.
- Cobrir as mudanças com TDD (unit + integração) e registrar evidências em relatório final de implementação.

## Capabilities

### New Capabilities

- Nenhuma.

### Modified Capabilities

- `room2-concise-medical-opinion-message`: passa a incluir procedência, recência explícita dos exames e status de transfusão com quantidade total de unidades quando aplicável.
- `eda-preop-deterministic-criteria`: contrato de extração LLM1 passa a persistir metadados estruturados de origem, recência e transfusão.
- `prompt-management-admin`: novo versionamento de prompts LLM1 para suportar os campos adicionais.

## Impact

- Código afetado (mínimo esperado):
  - `src/triage_automation/application/dto/llm1_models.py`
  - `src/triage_automation/application/services/llm1_service.py`
  - `src/triage_automation/infrastructure/matrix/message_templates.py`
  - `src/triage_automation/infrastructure/llm/deterministic_client.py`
  - `alembic/versions/<nova_migracao_llm1_prompt_v6>.py`
- Testes afetados (mínimo esperado):
  - `tests/unit/test_llm1_validation.py`
  - `tests/unit/test_room2_message_templates.py`
  - `tests/unit/test_deterministic_llm_client.py`
  - `tests/integration/test_post_room2_widget.py`
  - `tests/integration/test_llm_prompt_loading_runtime.py`
- Entregáveis de governança:
  - handoffs por slice com prompts de execução/validação/atualização de tarefa;
  - relatório final em `docs/implementation-reports/room2-report-origin-recent-exams-transfusion.md`.

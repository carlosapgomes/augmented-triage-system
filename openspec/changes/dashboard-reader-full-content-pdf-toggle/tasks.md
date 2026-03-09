# Tasks

## 1. Cobertura de teste (TDD) para autorização e visualização completa no detalhe

- [x] 1.1 Ajustar teste de integração em `tests/integration/test_dashboard_pages.py` para refletir que `reader` também pode expandir conteúdo completo no modo `Histórico Completo`.
- [x] 1.2 Adicionar teste de integração para o modo `Fluxo por Etapas` validando presença do botão de exibir/ocultar relatório PDF no card superior e bloco inicial colapsado.

## 2. Backend do detalhe de caso para full content e relatório PDF no card superior

- [x] 2.1 Atualizar `src/triage_automation/infrastructure/http/dashboard_router.py` para permitir `can_view_full_content` a usuários com papel `admin` e `reader`.
- [ ] 2.2 Derivar no `dashboard_router` o texto persistido do evento `pdf_report_extracted` a partir de `detail.timeline` e incluir no contexto do template do detalhe.

## 3. Template do detalhe para toggle no fluxo por etapas

- [ ] 3.1 Atualizar `src/triage_automation/infrastructure/http/templates/dashboard/case_detail.html` para renderizar, no card "Detalhe do Caso", botão de toggle "Exibir/Ocultar relatório PDF extraído" quando houver texto disponível.
- [ ] 3.2 Garantir que o conteúdo do relatório permaneça oculto por padrão e que o mesmo clique expanda/recolha o bloco no card superior, mantendo consistência com o comportamento atual de toggles.

## 4. Verificação de qualidade do slice

- [ ] 4.1 Executar testes alvo: `uv run pytest tests/integration/test_dashboard_pages.py -k "detail and (reader or thread)" -q` (ou seleção equivalente cobrindo os cenários novos).
- [ ] 4.2 Executar lint/type-check dos paths alterados: `uv run ruff check src/triage_automation/infrastructure/http/dashboard_router.py src/triage_automation/infrastructure/http/templates/dashboard/case_detail.html tests/integration/test_dashboard_pages.py` e `uv run mypy src/triage_automation/infrastructure/http/dashboard_router.py tests/integration/test_dashboard_pages.py`.
- [ ] 4.3 Executar `markdownlint-cli2 "openspec/changes/dashboard-reader-full-content-pdf-toggle/*.md" "openspec/changes/dashboard-reader-full-content-pdf-toggle/specs/**/*.md"`.

## Notes

- Evidência de TDD (red) para 1.1:
  - `uv run pytest tests/integration/test_dashboard_pages.py -k "full_content_toggle_for_reader" -q`
  - Falha esperada confirmada: `reader` ainda não recebe conteúdo completo/toggle na visualização `view=pure` até implementação das tarefas de backend/template.
- Evidência de TDD (red) para 1.2:
  - `uv run pytest tests/integration/test_dashboard_pages.py -k "thread_shows_pdf_report_toggle_in_header_card" -q`
  - Falha esperada confirmada: o card superior de `Fluxo por Etapas` ainda não exibe botão de exibir/ocultar relatório PDF.
- Evidência (green) para 2.1:
  - `uv run pytest tests/integration/test_dashboard_pages.py -k "full_content_toggle_for_reader" -q`
  - Passou após liberar `can_view_full_content` para `reader` no `dashboard_router`.
- Qualidade local do slice 2.1:
  - `uv run ruff check src/triage_automation/infrastructure/http/dashboard_router.py`
  - `uv run mypy src/triage_automation/infrastructure/http/dashboard_router.py`
  - Ambos passaram sem issues.

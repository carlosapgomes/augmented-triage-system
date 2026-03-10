# Tasks

## 1. Slice vertical: Base PWA instalavel (manifesto, service worker e shell)

- [x] 1.1 Adicionar/ajustar testes de integracao para falhar inicialmente quando `dashboard/base.html` nao expuser link de manifesto, metadados mobile/PWA e registro de service worker.
- [x] 1.2 Publicar assets estaticos PWA no `bot-api` (manifest, service worker e icones) com rotas/paths estaveis para consumo do browser.
- [ ] 1.3 Implementar `manifest.webmanifest` com `short_name=CHD`, `start_url=/dashboard/cases`, `display=standalone`, `scope=/` e cores alinhadas ao tema do dashboard.
- [ ] 1.4 Implementar service worker online-only (sem fallback offline e sem cache de HTML como fonte autoritativa).
- [ ] 1.5 Integrar no template base compartilhado os metadados/links/scripts PWA para cobrir login, dashboard e navegacao autenticada.
- [ ] 1.6 Executar testes alvo do dashboard/web session e confirmar green para o slice.

## 2. Slice vertical: Iconografia CHD para instalacao Android/iOS

- [ ] 2.1 Criar arte base do icone com composicao quadrada (`CHD` em destaque e `dashboard` menor abaixo) seguindo estilo/paleta do header atual.
- [ ] 2.2 Gerar e versionar tamanhos de icone exigidos para instalacao e navegação web (`16`, `32`, `180`, `192`, `512`, incluindo variante maskable quando aplicavel).
- [ ] 2.3 Referenciar corretamente os icones no manifesto e metadados Apple touch icon.
- [ ] 2.4 Adicionar validacoes de integracao para garantir que os assets de icone respondem com sucesso e sao referenciados no HTML/manifest.

## 3. Slice vertical: Mobile UX da listagem de casos (fluxo reader)

- [ ] 3.1 Adicionar/ajustar testes de integracao para preservar informacao obrigatoria (`caso`, `status`, `desfecho`, `atividade`) em markup mobile-friendly.
- [ ] 3.2 Implementar ajustes responsivos em `/dashboard/cases` para leitura em viewport pequeno (layout, espacamento e tipografia).
- [ ] 3.3 Tornar filtros, totalizacao e paginacao ergonomicos para toque (tap targets e fluxo de uso em celular).
- [ ] 3.4 Garantir compatibilidade com atualizacoes Unpoly apos os ajustes de layout.

## 4. Slice vertical: Mobile UX do detalhe de caso (fluxo reader)

- [ ] 4.1 Adicionar/ajustar testes de integracao para garantir operacao dos modos `thread` e `pure` em contexto mobile.
- [ ] 4.2 Implementar ajustes responsivos no cabecalho e controles do detalhe (`/dashboard/cases/{case_id}`) para navegacao touch.
- [ ] 4.3 Melhorar legibilidade mobile da timeline/etapas, mantendo integridade cronologica e sem perda de conteudo.
- [ ] 4.4 Validar que toggles de conteudo e localizacao de timestamps permanecem funcionais apos as mudancas.

## 5. Validacao operacional e documentacao

- [ ] 5.1 Executar checklist manual de instalacao e abertura em Android/Chrome (home screen, icone, standalone, start em `/dashboard/cases`).
- [ ] 5.2 Executar checklist manual de instalacao e abertura em iOS/Safari (Adicionar a Tela de Inicio, icone, standalone, start em `/dashboard/cases`).
- [ ] 5.3 Atualizar documentacao operacional em portugues com fluxo de instalacao mobile e limitacao explicita de ausencia de suporte offline.
- [ ] 5.4 Atualizar espelho em ingles para toda documentacao alterada no slice.
- [ ] 5.5 Rodar validacoes finais (pytest alvo, ruff, mypy e markdownlint dos artefatos OpenSpec/docs alterados).

## Notes

- Evidência da task 1.1 (TDD red):
  - `uv run pytest tests/integration/test_web_session_routes.py -k "pwa_manifest_mobile_metadata" -q`
  - Falha esperada confirmada: ausência de link de manifesto, metadados PWA/mobile e registro de service worker no `dashboard/base.html`.
- Verificação de qualidade dos arquivos alterados nesta slice:
  - `uv run ruff check tests/integration/test_web_session_routes.py` (passou)
  - `uv run mypy tests/integration/test_web_session_routes.py` (passou)
- Evidência da task 1.2 (TDD red):
  - `uv run pytest tests/integration/test_web_session_routes.py -k "pwa_assets_are_published" -q`
  - Falha esperada confirmada: `/manifest.webmanifest`, `/service-worker.js` e `/pwa/icons/chd-192.png` retornavam `404`.
- Evidência da task 1.2 (green):
  - `uv run pytest tests/integration/test_web_session_routes.py -k "pwa_assets_are_published" -q`
  - Resultado: `1 passed, 7 deselected` após publicação dos assets e rotas estáveis.
- Verificação de qualidade dos arquivos alterados na task 1.2:
  - `uv run ruff check apps/bot_api/main.py src/triage_automation/infrastructure/http/pwa_assets_router.py tests/integration/test_web_session_routes.py` (passou)
  - `uv run mypy --explicit-package-bases apps/bot_api/main.py src/triage_automation/infrastructure/http/pwa_assets_router.py tests/integration/test_web_session_routes.py` (passou)

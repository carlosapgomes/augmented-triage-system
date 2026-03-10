# Dashboard PWA Mobile Installable Design

## Context

O dashboard atual do ATS e server-rendered (FastAPI + Jinja) e ja possui base responsiva com Bootstrap, mas ainda opera como pagina web tradicional. Nao ha manifesto web app, service worker, icones de instalacao, nem metadados especificos para instalacao mobile.

Para o contexto operacional do CHD, o acesso rapido via tela inicial (Android/iOS) reduz friccao no fluxo diario dos lideres. Ao mesmo tempo, o projeto explicitou que nao precisa de modo offline funcional; portanto, o desenho deve priorizar instalabilidade, experiencia standalone e usabilidade mobile, sem introduzir cache offline.

Restricoes relevantes:

- Preservar arquitetura atual (camada HTTP/infrastructure, sem alterar regras de negocio).
- Manter fluxo de autenticacao por sessao ja especificado (`/dashboard/cases` redireciona para `/login` quando nao autenticado).
- Considerar diferencas entre Android e iOS para instalacao (prompt automatico vs Add to Home Screen manual).
- Operar sob HTTPS em ambiente publicado, conforme runbook operacional.

## Goals / Non-Goals

**Goals:**

- Habilitar instalacao do dashboard como PWA em Android e iOS.
- Configurar app instalado com `start_url=/dashboard/cases` e `display=standalone`.
- Entregar conjunto de icones com identidade visual CHD:
  - `CHD` em destaque (alto, maiusculo)
  - `dashboard` menor abaixo
  - composicao quadrada
- Implementar service worker em estrategia online-only (sem cache offline).
- Melhorar usabilidade mobile das telas de uso do `reader` (`/dashboard/cases` e `/dashboard/cases/{case_id}`), priorizadas para a primeira entrega.

**Non-Goals:**

- Nao oferecer funcionamento offline.
- Nao introduzir push notifications, background sync ou fila local.
- Nao alterar contratos clinicos, workflow de triagem, estados de caso ou politicas de autorizacao.
- Nao redesenhar o fluxo de login/sessao alem do necessario para compatibilidade com abertura via app instalado.

## Decisions

### Decision 1: Entregar artefatos PWA como assets estaticos versionados no bot-api

- Choice: adicionar assets estaticos dedicados para PWA (manifest, service worker, icones e favicon) e servi-los pelo `bot-api`.
- Rationale: separa claramente concerns de UI/instalabilidade, simplifica cache de browser e facilita validacao em testes de integracao.
- Alternative considered: gerar manifesto dinamicamente em template.
  - Rejected por reduzir previsibilidade de cache e dificultar validacao deterministica de artefatos.

### Decision 2: Manifest com foco em app instalado para operacao clinica

- Choice: configurar `start_url` para `/dashboard/cases`, `display` como `standalone`, `scope` em `/`, `short_name` como `CHD` e nome completo orientado ao contexto clinico (`CHD Dashboard`), com cores alinhadas ao tema hospitalar e icones completos para Android/iOS.
- Rationale: atende requisito explicito de abrir direto no dashboard, preserva legibilidade do rotulo no home screen e reforca uso como app operacional.
- Alternative considered: `start_url` em `/` e nome curto mais longo.
  - Rejected porque adiciona salto desnecessario para o principal ponto de uso e pode comprometer legibilidade no icone/home screen.

### Decision 3: Compatibilidade de sessao preservando seguranca atual

- Choice: manter comportamento atual de autenticacao: app instalado inicia em `/dashboard/cases`; sem sessao valida, ocorre redirect para `/login`.
- Rationale: nao altera modelo de seguranca e reutiliza requisito vigente de `web-login-session`.
- Alternative considered: bypass de login para contexto PWA.
  - Rejected por implicar novo risco de seguranca e escopo fora desta mudanca.

### Decision 4: Service worker minimo, sem cache de conteudo

- Choice: registrar service worker para habilitar instalabilidade, com ciclo de vida minimo e sem estrategia de cache offline.
- Rationale: cumpre objetivo de PWA instalavel sem assumir complexidade e risco de sincronizacao/offline.
- Alternative considered: cache-first/network-first para paginas e assets.
  - Rejected por conflito com requisito de nao priorizar suporte sem rede e por aumentar risco de conteudo stale no dashboard.

### Decision 5: Integracao PWA no template base compartilhado

- Choice: inserir links/meta/scripts PWA no `dashboard/base.html`, para cobrir login, dashboard e telas admin sem duplicacao.
- Rationale: ponto unico de manutencao e consistencia de comportamento entre rotas web.
- Alternative considered: incluir tags PWA por pagina.
  - Rejected por duplicacao e maior risco de divergencia.

### Decision 6: Iconografia CHD com fonte visual unica e multiplos tamanhos

- Choice: adotar conceito textual aprovado (`CHD` grande + `dashboard` pequeno), com estilo visual seguindo o header atual do dashboard (gradiente/paleta institucional existente), e gerar conjunto de tamanhos exigidos (pelo menos 16, 32, 180, 192, 512, incluindo variante maskable).
- Rationale: atende necessidade imediata de branding funcional sem dependencia de arte externa e com coerencia direta com a interface atual.
- Alternative considered: usar placeholder generico de icone.
  - Rejected por baixo valor visual e risco de retrabalho imediato.

### Decision 7: Mobile UX progressiva por CSS + ajustes de template nas telas criticas do reader

- Choice: priorizar melhorias em slices verticais nas telas de uso do `reader`:
  - listagem de casos com layout mais legivel em telas pequenas;
  - detalhe de caso com melhor hierarquia visual/tap targets.
- Rationale: entrega valor incremental com risco baixo, mantendo renderizacao server-side e sem introduzir framework SPA.
- Alternative considered: incluir tambem telas administrativas na primeira entrega.
  - Rejected para manter foco no fluxo operacional principal e reduzir risco de escopo.

## Risks / Trade-offs

- [Instalacao iOS depende de fluxo manual "Adicionar a Tela de Inicio"] -> Mitigation: documentar passo a passo no runbook e validar em device real.
- [Ausencia de offline pode gerar expectativa incorreta de "app nativo"] -> Mitigation: declarar explicitamente limitacao no checklist operacional.
- [Service worker mal configurado pode introduzir efeito colateral de cache] -> Mitigation: manter implementacao minima sem caching de conteudo e validar comportamento de rede em testes manuais.
- [`start_url=/dashboard/cases` redireciona para login sem sessao] -> Mitigation: tratar como comportamento esperado e consistente com especificacao de sessao.
- [Divergencia visual de icones entre Android e iOS] -> Mitigation: gerar assets dedicados por tamanho/plataforma e validar rendering em ambos.
- [Melhorias mobile podem afetar legibilidade desktop] -> Mitigation: usar breakpoints claros e cobertura de testes de pagina existentes + smoke manual desktop/mobile.

## Migration Plan

1. Adicionar base PWA (assets, manifesto, service worker, metadados no template base) mantendo comportamento atual de autenticacao.
2. Publicar em ambiente de homologacao com HTTPS e validar instalabilidade em Android e iOS.
3. Implementar melhorias de usabilidade mobile por slices verticais nas telas de reader (listagem e detalhe), com validacao incremental.
4. Atualizar documentacao operacional (pt-BR e espelho EN) com checklist de instalacao e limitacoes conhecidas.
5. Liberar para producao apos aceite funcional em dispositivos reais.

Rollback strategy:

- Remover referencias de manifesto/service worker do template base e desabilitar/publicar sem assets PWA.
- Manter paginas web tradicionais inalteradas como fallback operacional.
- Como nao ha migracao de banco nem alteracao de dominio, rollback e de baixo risco e imediato.

## Open Questions

- Nenhuma pendencia funcional bloqueante no momento; seguir com validacao manual em Android/Chrome e iOS/Safari em dispositivos reais disponiveis.

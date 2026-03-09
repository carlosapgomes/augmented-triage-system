# Dashboard Reader Full Content and PDF Toggle Design

## Context

A tela de detalhe de caso do dashboard possui dois modos: "Fluxo por Etapas" (`view=thread`) e "Histórico Completo" (`view=pure`). Hoje, o backend permite conteúdo completo apenas para `admin` (`can_view_full_content = role is admin`), enquanto `reader` vê apenas excerpt. Além disso, o card superior de "Detalhe do Caso" no modo em etapas não expõe o texto do relatório PDF extraído, embora esse conteúdo já exista no timeline (`pdf_report_extracted`) vindo de `case_report_transcripts`.

A operação pediu dois ajustes de UX/autorização: (1) liberar conteúdo completo também para `reader`, e (2) oferecer no card superior do fluxo em etapas um botão de exibir/ocultar o relatório PDF extraído, sem mostrar o texto expandido por padrão.

## Goals / Non-Goals

**Goals:**

- Permitir que `reader` visualize conteúdo completo dos eventos no detalhe do caso, inclusive no modo "Histórico Completo".
- Exibir no card superior do modo "Fluxo por Etapas" um controle de toggle para o texto de `relatório pdf extraído`.
- Reusar o texto já persistido no banco/timeline, sem reprocessar arquivo PDF.
- Manter comportamento colapsável (oculto por padrão, expande/recolhe no clique) com semântica consistente de acessibilidade (`aria-expanded`).

**Non-Goals:**

- Não alterar pipeline de ingestão/extrator PDF.
- Não alterar workflow clínico, state machine, eventos Matrix ou persistência de transcritos.
- Não introduzir novos papéis/perfis de acesso além de `admin` e `reader`.

## Decisions

### Decision 1: Autorizar full content para `reader` e `admin` no detalhe do caso

- Escolha: alterar a regra de visualização completa no `dashboard_router` para aceitar ambos os papéis com permissão de auditoria (`admin` e `reader`).
- Racional: atende a necessidade operacional de acesso completo sem criar endpoint novo; mantém diferenciação de `admin` concentrada em gestão de usuários.
- Alternativa considerada: manter `reader` com excerpt e liberar somente PDF completo em bloco separado.
- Motivo da rejeição: comportamento inconsistente entre eventos e maior complexidade de autorização por tipo de evento.

### Decision 2: Derivar o texto de relatório PDF diretamente do timeline do caso

- Escolha: identificar no `detail.timeline` o evento `pdf_report_extracted` e expor seu `content_text` no contexto do template para o card superior.
- Racional: evita duplicar query/repositório e garante que a origem exibida seja a mesma já usada em "Histórico Completo".
- Alternativa considerada: buscar `case_report_transcripts` com consulta dedicada.
- Motivo da rejeição: duplicação de caminho de leitura e risco de divergência temporal/ordenação.

### Decision 3: Implementar toggle no card superior com o mesmo padrão de UI já existente

- Escolha: adicionar botão "Exibir relatório PDF extraído" / "Ocultar relatório PDF extraído" e bloco `<pre>` colapsável no card de "Detalhe do Caso", reaproveitando o padrão de `data-toggle-full` já usado na página.
- Racional: mantém consistência visual/comportamental e reduz JS adicional.
- Alternativa considerada: criar componente JS separado para thread view.
- Motivo da rejeição: sobreengenharia para interação simples já suportada pelo handler atual.

## Risks / Trade-offs

- [Risco] Exposição mais ampla de conteúdo sensível para usuários `reader`.
  - Mitigação: decisão é explícita do negócio; manter trilha de auditoria via autenticação/sessão e logs existentes.
- [Trade-off] O card superior pode crescer bastante para relatórios longos.
  - Mitigação: conteúdo inicia colapsado; usar bloco com estilo atual (`pre`) para leitura sob demanda.
- [Risco] Casos sem evento `pdf_report_extracted` podem renderizar botão vazio se a lógica for incompleta.
  - Mitigação: exibir botão apenas quando houver texto não vazio.

## Migration Plan

1. Atualizar/Adicionar testes de integração de dashboard para refletir nova autorização de conteúdo completo para `reader` (red).
2. Ajustar `dashboard_router` para liberar full content a `reader` e incluir no contexto o texto de `pdf_report_extracted` para o modo thread (green).
3. Atualizar `case_detail.html` com botão colapsável no card superior do fluxo por etapas e reaproveitar toggle JS.
4. Rodar validações alvo (`pytest` focado, `ruff`, `mypy`, `markdownlint`) antes de concluir a implementação.

## Open Questions

- Nenhuma pendência funcional no momento; o caso padrão continua assumindo um único PDF extraído por caso.

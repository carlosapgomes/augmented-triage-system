Você está em contexto limpo e deve executar APENAS um slice.

## Leitura obrigatória (nesta ordem)
1) AGENTS.md
2) openspec/changes/room2-report-origin-recent-exams-transfusion/handoffs/6.1-final-implementation-report.md

3) openspec/changes/room2-report-origin-recent-exams-transfusion/tasks.md

## Parâmetros
- Skill obrigatório: openspec-apply-change
- Change ID: room2-report-origin-recent-exams-transfusion
- Task file: openspec/changes/room2-report-origin-recent-exams-transfusion/tasks.md
- Slice alvo: 6.1
- Handoff do slice:openspec/changes/room2-report-origin-recent-exams-transfusion/handoffs/6.1-final-implementation-report.md

## Modo de execução
- Execute somente o slice alvo.
- Não avance para próximo slice.
- Faça TDD (RED -> GREEN).
- Altere o mínimo de arquivos necessário.
- Siga estritamente os comandos de verificação definidos no handoff.
- Atualize o tasks.md marcando somente o item do slice.
- Gere relatório detalhado em /tmp/openspec-slice-report-<SLICE>.md.
- Commit e push específicos do slice.
- Pare e aguarde aprovação.

## Conteúdo obrigatório do relatório temporário
Arquivo: /tmp/openspec-slice-report-6.1.md
Deve conter:
- objetivo do slice
- arquivos alterados
- comandos executados + status
- evidência RED/GREEN
- fragmentos de diff relevantes
- riscos/pendências

## Restrições
- Não alterar arquitetura fora do escopo.
- Não incluir lógica de negócio em adapters.
- Não mexer em tasks de outros slices.
- Se houver bloqueio, parar e reportar claramente.

## Formato final de saída (EXATO)
---
## SLICE COMPLETE

**Task:** <X.Y - descrição>
**Status:** ✓ Implemented

**Changes:**
- <arquivo1> (added/modified)
- <arquivo2> (added/modified)

**Tests:** <passed/failed/not run>

**Next:** <X.Z - descrição>

**Temp report:** /tmp/openspec-slice-report-<SLICE>.md

Awaiting your approval to continue.
---

# Handoffs por slice

Ordem recomendada de execução (contexto limpo por slice):

1. `1.1-llm1-validation-tests.md`
2. `1.2-llm1-schema-implementation.md`
3. `2.1-llm1-prompt-tests.md`
4. `2.2-llm1-prompt-and-migration.md`
5. `3.1-room2-origin-transfusion-tests.md`
6. `3.2-room2-origin-transfusion-implementation.md`
7. `4.1-room2-recent-exams-tests.md`
8. `4.2-room2-recent-exams-implementation.md`
9. `5.1-deterministic-client-tests.md`
10. `5.2-deterministic-client-implementation.md`
11. `6.1-final-implementation-report.md`

Todos os handoffs exigem geração de relatório operacional em `/tmp/openspec-slice-report-<slice>.md`.

Arquivos de apoio:

- `MASTER_PROMPT.md`: prompt mestre reutilizável por slice.
- `MINI_HANDOFF.md`: contexto mínimo para retomada em outra máquina.
- `reports/openspec-slice-report-1.1.md`: relatório versionado do slice 1.1.

# Design: Dashboard Search Result Totals

## Context

O dashboard de casos já possui listagem paginada, filtros por status/período e um total geral de registros retornados. Além disso, cada linha já traz um `case_outcome` operacional (`ACEITO`, `NEGADO`, `EM_ANDAMENTO`).

O gap atual é a ausência de uma visão agregada por desfecho para o universo da busca aplicada. A operação precisa dessa leitura rápida sem depender de contagem manual na tabela paginada.

Restrições relevantes:

- Não alterar workflow clínico nem regras de transição de `CaseStatus`.
- Não alterar o endpoint JSON `/monitoring/cases` neste change.
- Reusar a lógica operacional já existente para classificação de desfecho.
- A totalização deve refletir o conjunto completo filtrado (todas as páginas), inclusive na busca inicial do dia atual.

## Goals / Non-Goals

**Goals:**

- Expor, no contexto do dashboard HTML, totais agregados de busca: total de casos, aceitos, negados e em processamento.
- Garantir coerência entre os totais agregados e a regra atual de `case_outcome`.
- Renderizar a totalização abaixo da tabela, inclusive quando não houver resultados (zeros explícitos).
- Manter comportamento existente de filtros, paginação e endpoint JSON de monitoramento.

**Non-Goals:**

- Não incluir novo endpoint nem alterar contrato externo do `/monitoring/cases`.
- Não introduzir novos estados de domínio nem categorias adicionais (por exemplo, `FAILED` separado).
- Não redesenhar layout do dashboard além do bloco de totalização solicitado.

## Decisions

### Decision 1: Introduzir totais agregados no contrato interno da listagem

- Escolha: estender a resposta interna de listagem de monitoramento (camadas `application/ports` e `service`) com um objeto de totais por desfecho.
- Racional: o template deve receber dados já preparados, sem lógica de agregação na camada de apresentação.
- Alternativa considerada: calcular totais no template com base em `items`.
- Motivo da rejeição: `items` representa apenas a página atual e não o universo completo da busca.

### Decision 2: Calcular agregados no repositório usando o mesmo filtro da listagem

- Escolha: executar agregação SQL sobre o mesmo recorte filtrado de casos (status/período), independente de paginação, retornando em uma única estrutura os contadores de `ACEITO`, `NEGADO` e `EM_ANDAMENTO`, além do total.
- Racional: garante consistência entre tabela e totais, e evita divergências de regra entre camadas.
- Alternativa considerada: executar múltiplas consultas separadas por categoria.
- Motivo da rejeição: aumenta custo de manutenção e risco de inconsistência entre filtros.

### Decision 3: Reusar semântica atual de desfecho para agregação

- Escolha: manter a mesma precedência operacional já adotada no sistema:
  1. `appointment_status == confirmed` -> `ACEITO`
  2. `appointment_status == denied` -> `NEGADO`
  3. `doctor_decision == deny` -> `NEGADO`
  4. demais casos -> `EM_ANDAMENTO`
- Racional: preserva comportamento conhecido pela operação e evita mudanças de regra implícitas.
- Alternativa considerada: tratar `FAILED` fora de `EM_ANDAMENTO` já neste change.
- Motivo da rejeição: fora do escopo aprovado; pode ser tratado em evolução futura.

### Decision 4: Renderizar bloco de totalização sempre, mesmo sem resultados

- Escolha: manter o bloco visível abaixo da tabela com contadores zerados quando não houver casos.
- Racional: evita ambiguidade visual e mantém padrão estável de leitura para busca inicial e buscas vazias.
- Alternativa considerada: ocultar bloco quando `total == 0`.
- Motivo da rejeição: reduz previsibilidade da interface e não atende ao solicitado.

## Risks / Trade-offs

- [Risco] Consulta de agregação adiciona custo extra ao carregamento da listagem.
  - Mitigação: usar agregação única alinhada ao mesmo `from_clause`/`where` já existente, sem scans redundantes por categoria.

- [Trade-off] Ampliação de contrato interno de listagem exige ajustes em testes e possíveis consumidores internos.
  - Mitigação: cobertura de integração no dashboard e no repositório; manter endpoint JSON sem mudança funcional.

- [Risco] Divergência futura entre regra de desfecho por linha e agregação.
  - Mitigação: centralizar semântica em helper compartilhado e validar por testes de precedência.

## Migration Plan

1. Escrever testes (TDD) para validar bloco de totalização no dashboard com:
   - universo total da busca (independente da página),
   - contadores por desfecho,
   - cenário sem resultados com zeros.
2. Ajustar contrato interno de monitoramento para transportar totais agregados.
3. Implementar agregação no repositório com os mesmos filtros da listagem.
4. Atualizar renderização do fragmento HTML para exibir totalização abaixo da tabela.
5. Validar regressão de paginação/filtros e não alteração do endpoint JSON.

Rollback:

- Reversão de código/template sem migração de banco, retornando ao comportamento anterior da listagem sem totalização agregada.

## Open Questions

- Nenhuma no momento; escopo e regras foram validados com o solicitante.

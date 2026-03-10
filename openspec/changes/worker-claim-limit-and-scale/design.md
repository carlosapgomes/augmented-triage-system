# Design: worker-claim-limit-and-scale

## Context

O runtime atual do worker usa `claim_limit` fixo em código. Em cenários com rajadas de uploads, uma única instância pode reservar vários jobs pesados e atrasar o processamento de jobs curtos subsequentes. Operacionalmente, isso piora o tempo até primeiras mensagens na Sala 2.

## Goals / Non-Goals

**Goals:**

- Permitir ajuste de `claim_limit` via ambiente sem alterar código.
- Definir baseline de produção para `claim_limit=1` por worker.
- Executar 3 instâncias de worker no deploy ansible rootless para aumentar paralelismo.

**Non-Goals:**

- Não alterar regras clínicas, estados de caso, ou contratos de mensagens.
- Não introduzir nova fila, nova prioridade de jobs, ou mudanças de ordering global.

## Decisions

### Decision 1: Expor `WORKER_CLAIM_LIMIT` em settings

- **Choice:** adicionar `worker_claim_limit` em `Settings` e usar esse valor ao construir `WorkerRuntime`.
- **Rationale:** mantém ajuste operacional simples por variável de ambiente.
- **Alternatives considered:** manter valor hard-coded em runtime (rejeitado por baixa flexibilidade).

### Decision 2: Baseline de claim por instância em 1

- **Choice:** declarar `WORKER_CLAIM_LIMIT=1` no baseline de ambiente.
- **Rationale:** reduz prefetch por instância e melhora distribuição entre múltiplos workers.
- **Alternatives considered:** manter 10 (rejeitado por aumentar latência percebida em bursts).

### Decision 3: Escalar worker para 3 réplicas no deploy

- **Choice:** incluir `--scale worker=<replicas>` no comando `docker compose up` do role de deploy e configurar baseline para 3.
- **Rationale:** aumenta paralelismo sem alterar semântica do workflow.
- **Alternatives considered:** replicar serviços `worker-2`/`worker-3` no compose (rejeitado por duplicação de configuração).

## Risks / Trade-offs

- [Mais workers podem aumentar uso de CPU/memória] → Mitigation: manter réplicas e `claim_limit` configuráveis por variáveis ansible.
- [Ordem entre pacientes pode variar mais] → Mitigation: manter encadeamento por thread de caso e validar contratos existentes.
- [Configuração de scale no deploy pode divergir do ambiente local] → Mitigation: manter baseline explícito em `group_vars` e role defaults.

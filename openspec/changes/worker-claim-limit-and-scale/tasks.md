# Tasks: worker-claim-limit-and-scale

## 1. Runtime tuning and deploy scaling

- [x] 1.1 Expor `WORKER_CLAIM_LIMIT` em `Settings`, plugar no `WorkerRuntime`, definir baseline `WORKER_CLAIM_LIMIT=1`, e aplicar `--scale worker=3` no deploy ansible com cobertura de testes.

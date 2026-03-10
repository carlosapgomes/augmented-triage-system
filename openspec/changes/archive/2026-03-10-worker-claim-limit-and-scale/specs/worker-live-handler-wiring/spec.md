# Delta Spec: worker-live-handler-wiring

## ADDED Requirements

### Requirement: Worker Runtime SHALL Support Configurable Claim Limit

O runtime do worker SHALL aceitar limite de claim por configuração de ambiente para controlar quantos jobs cada instância reserva por ciclo.

#### Scenario: Worker startup reads claim limit from settings

- **WHEN** o processo `apps.worker.main` inicia com `WORKER_CLAIM_LIMIT` definido
- **THEN** o `WorkerRuntime` MUST ser construído com esse valor como `claim_limit`
- **AND** o valor default MUST permanecer disponível quando a variável não estiver definida

#### Scenario: Baseline runtime sets one-claim-per-worker

- **WHEN** o ambiente baseline de runtime é renderizado para deploy
- **THEN** `WORKER_CLAIM_LIMIT` MUST ser configurado como `1`
- **AND** cada instância do worker MUST reservar no máximo um job por ciclo de claim

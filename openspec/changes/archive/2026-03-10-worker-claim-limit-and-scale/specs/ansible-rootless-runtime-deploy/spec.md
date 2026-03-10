# Delta Spec: ansible-rootless-runtime-deploy

## ADDED Requirements

### Requirement: Deploy Automation SHALL Scale Worker Replicas Explicitly

O deploy automation SHALL iniciar os serviços com escala explícita de workers para permitir paralelismo controlado no consumo da fila.

#### Scenario: Deploy starts runtime with worker scale

- **WHEN** operadores executam o playbook de deploy com configuração padrão
- **THEN** o comando `docker compose up` MUST incluir `--scale worker=<replicas>`
- **AND** o baseline de réplicas de worker MUST ser `3`

#### Scenario: Worker replica count remains configurable

- **WHEN** operadores ajustam variável de réplicas no inventário/role
- **THEN** o deploy MUST aplicar o novo valor sem alterar comandos suportados dos serviços
- **AND** os demais serviços (`bot-api`, `bot-matrix`) MUST continuar sob o mesmo fluxo de deploy

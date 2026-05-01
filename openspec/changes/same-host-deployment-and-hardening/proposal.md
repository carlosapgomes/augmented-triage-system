# Same host deployment and hardening

## Why

Com a nova web app Django assumindo a interface humana do ATS, o projeto precisa de uma topologia de deploy e hardening coerente com o uso real: tudo no mesmo host, acesso remoto controlado por Cloudflare Tunnel e restrição de `nir`/`scheduler` à intranet também no nível de publicação/rede. Sem essa camada operacional, a política de acesso aprovada dependeria apenas da aplicação e deixaria lacunas de segurança e operação.

## What Changes

- Definir a topologia oficial de publicação do ATS no mesmo host atual, incorporando o novo app Django ao runtime suportado.
- Ajustar automação de deploy para subir e validar os serviços necessários do stack consolidado no host rootless atual.
- Introduzir hardening operacional para separar caminhos de acesso interno e externo.
- Garantir que `nir` e `scheduler` fiquem bloqueados fora da intranet também na camada de publicação/rede, além do bloqueio app-level já definido.
- Documentar a estratégia oficial de exposição remota via Cloudflare Tunnel para `doctor`, `manager` e `admin`.
- Adicionar verificação operacional e troubleshooting específico para acessos negados, publicação incorreta e coerência entre topologia, proxy e regras por papel.

## Capabilities

### New Capabilities

- `same-host-web-publication-topology`: topologia oficial de publicação no mesmo host para o stack ATS + Django, separando superfícies internas e externas.
- `role-zone-network-hardening`: hardening de publicação/rede para reforçar a política de acesso por papel e zona.

### Modified Capabilities

- `ansible-rootless-runtime-deploy`: o deploy rootless passa a contemplar o runtime consolidado com a nova web app Django no mesmo host.
- `ops-runbook-automation`: o runbook operacional precisa documentar a nova topologia, validações de acesso interno/externo e troubleshooting correspondente.
- `runtime-orchestration`: o runtime suportado passa a incluir a nova superfície web consolidada na composição oficial de execução.
- `manual-e2e-readiness`: as validações manuais precisam cobrir publicação, acesso remoto via túnel e restrições de intranet por papel.

## Impact

- Infraestrutura:
  - mesmo host atual com stack ampliado
  - publicação interna e externa mais explícita
- Automação:
  - atualização de Ansible, compose/runtime e verificações pós-deploy
- Segurança:
  - reforço de segregação por zona no nível de rede/publicação
  - logging/troubleshooting de falhas de acesso
- Operação:
  - novos checklists de validação e troubleshooting
- Runtime:
  - **BREAKING**: a topologia oficial deixa de ser apenas a exposição simples do `bot-api` atual e passa a considerar a publicação consolidada do novo stack web

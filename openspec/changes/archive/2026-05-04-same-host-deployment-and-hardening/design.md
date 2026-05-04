# Design

## Context

Após a fundação Django, a migração do fluxo operacional web e a consolidação manager/admin, o ATS passa a depender de uma topologia operacional clara para rodar tudo no mesmo host com segurança. A decisão aprovada é:

- novo stack web no mesmo host do ATS atual;
- acesso remoto por túnel Cloudflare para `doctor`, `manager` e `admin`;
- acesso de `nir` e `scheduler` limitado à intranet no nível de rede/publicação e também no nível da aplicação.

Este change fecha a camada operacional dessa arquitetura.

## Goals / Non-Goals

**Goals:**

- Definir a topologia oficial de publicação do stack consolidado no mesmo host.
- Atualizar automação de deploy para subir e validar a nova composição.
- Reforçar a segregação entre acesso interno e remoto.
- Documentar claramente como validar e diagnosticar a política de acesso por papel/zona.

**Non-Goals:**

- Migrar novamente regras de autorização já cobertas pela aplicação.
- Mudar a semântica clínica do workflow.
- Introduzir autenticação no Cloudflare Access; a autenticação continua somente no app.
- Suportar múltiplos hosts ou topologias HA neste ciclo.

## Decisions

### Decision 1: Manter single-host como baseline oficial

- **Escolha:** todo o stack consolidado continua rodando no mesmo host gerenciado por Ansible/rootless Docker.
- **Racional:** está alinhado ao baseline atual do projeto e à decisão operacional aprovada.

### Decision 2: Separar publicação interna e externa por topologia, não por papéis no frontend

- **Escolha:** a segregação de acesso deve ocorrer na topologia de publicação/rede antes da aplicação, e não apenas por ocultação de UI.
- **Racional:** reduz superfície de risco e reforça a política da diretoria.

### Decision 3: Preservar Cloudflare Tunnel apenas como caminho remoto aprovado

- **Escolha:** `doctor`, `manager` e `admin` acessam remotamente via FQDN publicado pelo túnel Cloudflare; `nir` e `scheduler` não devem depender desse caminho.
- **Racional:** simplifica o modelo operacional e mantém uma via remota controlada.

### Decision 4: Validar explicitamente a coerência entre publicação e regras app-level

- **Escolha:** o deploy/runbook devem exigir checagens que confirmem:
  - acesso remoto permitido para papéis remotos;
  - acesso remoto negado para `nir`/`scheduler`;
  - acesso interno permitido para todos os papéis relevantes.
- **Racional:** evita falsa sensação de segurança quando só uma das camadas está correta.

### Decision 5: Tratar troubleshooting de acesso como requisito de primeira classe

- **Escolha:** o runbook deve incluir diagnóstico de falhas de publicação, proxy, cabeçalhos de origem, Cloudflare Tunnel e rota interna.
- **Racional:** a política de acesso terá falhas operacionais difíceis de investigar sem um playbook claro.

## Risks / Trade-offs

- **Risco:** configuração de publicação expor acidentalmente rotas/superfícies erradas externamente.
  - **Mitigação:** validações pós-deploy explícitas e runbook com critérios objetivos.
- **Risco:** inconsistência entre o que a rede bloqueia e o que a aplicação espera.
  - **Mitigação:** checagem cruzada entre topologia externa/interna e testes manuais por papel.
- **Risco:** aumento de complexidade operacional no host único.
  - **Mitigação:** manter topologia simples e documentada como baseline suportado.

## Migration Plan

1. Atualizar a descrição oficial da composição runtime/deploy para incluir a web app Django.
2. Ajustar automação rootless e comandos suportados para o stack consolidado.
3. Documentar e validar a topologia de publicação interna vs externa.
4. Adicionar hardening/checklists de acesso por papel/zona.
5. Atualizar runbook manual e troubleshooting operacional.

## Slice Plan

### Phase 1: Runtime and deploy composition

- Slice 1.1: atualizar a composição suportada de runtime/deploy para incluir a web app Django.
- Slice 1.2: ajustar automação Ansible/rootless para o stack consolidado.

### Phase 2: Publication topology and zone hardening

- Slice 2.1: documentar e validar topologia interna vs externa no mesmo host.
- Slice 2.2: adicionar hardening/checklists de acesso por zona e troubleshooting.

### Phase 3: Final verification

- Slice 3.1: atualizar runbooks/manuais e verificar o baseline operacional final.

## Open Questions

- A camada de publicação interna será descrita como reverse proxy obrigatório ou como baseline flexível entre IP direto e proxy interno controlado.
- A observabilidade de negações por rede ficará somente em logs operacionais do host/proxy ou ganhará checklist específico de coleta no runbook.

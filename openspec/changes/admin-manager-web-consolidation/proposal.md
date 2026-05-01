# Admin manager web consolidation

## Why

Depois da fundação Django e da migração do fluxo operacional humano para a web app, ainda falta consolidar as superfícies de gestão e supervisão em torno dos papéis `manager` e `admin`. O projeto precisa separar claramente quem apenas acompanha a operação (`manager`) de quem administra o sistema (`admin`), migrando dashboard, auditoria operacional e áreas administrativas para a nova aplicação web sem perder rastreabilidade ou controles de autorização.

## What Changes

- Consolidar no Django o dashboard operacional e o detalhe auditável dos casos para perfis de supervisão.
- Introduzir uma superfície específica para `manager` com acesso somente a dashboard, relatórios e acompanhamento operacional.
- Consolidar a superfície `admin` no Django para gestão de usuários, gestão de prompts e funções administrativas do sistema.
- Expandir a gestão de usuários para o modelo final de papéis `nir`, `doctor`, `scheduler`, `manager` e `admin`, incluindo mudança de role por `admin`.
- Tratar a migração conceitual legada de contas como `reader -> manager` e `admin -> admin`.
- Unificar navegação autenticada e regras de autorização entre áreas operacionais, supervisão e administração.
- Preservar e ampliar a trilha auditável das ações administrativas e do consumo de informações sensíveis por papel.
- Substituir integralmente a superfície administrativa antiga em FastAPI ao final do hard refactor, sem convivência operacional legada.

## Capabilities

### New Capabilities

- `manager-operational-reporting`: superfície de supervisão para `manager` com dashboard e relatórios read-only.
- `admin-system-console`: superfície Django consolidada para administração do sistema, reunindo navegação e entrypoints administrativos.

### Modified Capabilities

- `case-thread-monitoring-dashboard`: o dashboard e o detalhe dos casos passam a suportar explicitamente o papel `manager` e a nova superfície Django consolidada.
- `user-management-admin`: a gestão de usuários deixa de ser apenas uma área administrativa genérica e passa a ser parte da superfície Django consolidada para `admin`, preservando restrições estritas contra `manager`.
- `prompt-management-admin`: a gestão de prompts passa a integrar a superfície Django consolidada para `admin`, permanecendo inacessível para `manager`.
- `operations-web-shell`: a navegação role-aware passa a distinguir claramente supervisão (`manager`) de administração (`admin`) dentro do shell consolidado.
- `manual-e2e-readiness`: o runbook manual precisa validar permissões e fluxos separados para `manager` e `admin` na superfície Django final.

## Impact

- UI:
  - dashboard e detalhe de caso consolidados no Django
  - novas áreas de supervisão e console administrativo
- Backend:
  - rotas Django para relatórios, usuários, prompts e auditoria administrativa
  - adaptação das consultas de dashboard para novos papéis
- Segurança:
  - autorização explícita de `manager` como read-only
  - preservação de `admin` como único papel capaz de mutar usuários/prompts/sistema
- Runtime:
  - **BREAKING**: a superfície administrativa/monitoramento antiga em FastAPI torna-se candidata à desativação após a paridade funcional no Django
- Testes/documentação:
  - novos testes de autorização e runbook manual para `manager` vs `admin`

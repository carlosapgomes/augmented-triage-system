# Django web foundation and access zones

## Why

A interface operacional do ATS ainda depende em grande parte de interações por mensagens Matrix, enquanto a superfície web atual cobre apenas login, dashboard e áreas administrativas limitadas em FastAPI. O hospital agora precisa de uma fundação web mais robusta, com autenticação local, múltiplos perfis operacionais e restrições explícitas de acesso por rede para suportar a migração gradual do fluxo para uma aplicação Django com melhor adoção operacional.

## What Changes

- Criar um novo app web baseado em Django, executado no mesmo host do ATS atual, sem alterar nesta fase o motor central de orquestração clínica.
- Introduzir autenticação web local no Django com contas individuais por pessoa e papéis `nir`, `doctor`, `scheduler`, `manager` e `admin`.
- Implementar redirecionamento pós-login por papel para superfícies web específicas de cada perfil.
- Implementar controles de acesso em duas camadas para `nir` e `scheduler`:
  - bloqueio por origem de rede autorizada (CIDR de intranet);
  - bloqueio por regra de aplicação mesmo quando as credenciais forem válidas.
- Permitir acesso remoto via navegador/PWA para `doctor`, `manager` e `admin`, publicado por túnel Cloudflare, com autenticação somente no app.
- Entregar a fundação PWA do novo shell Django apenas para `doctor`, `manager` e `admin` na publicação externa, preservando o modo instalável já adotado pela equipe remota.
- Preservar rastreabilidade individual de acesso e de autorização negada, preparando a base para os changes seguintes de migração dos fluxos NIR -> Médico -> Agendador -> Gestão/Admin.

## Capabilities

### New Capabilities

- `django-operations-foundation`: fundação do novo app Django com autenticação local, contas individuais, papéis operacionais e rotas web role-aware.
- `role-zoned-access-control`: controle de acesso por zona de rede e por papel, com restrições de intranet para `nir` e `scheduler` e auditoria de negações.
- `django-operations-pwa-shell`: shell PWA instalável do novo app Django, mantendo comportamento online-only e preparado para superfícies operacionais por perfil.

### Modified Capabilities

- `web-login-session`: o fluxo de login web deixa de assumir apenas o dashboard atual e passa a suportar autenticação e redirecionamento por papel no novo app Django.
- `operations-web-shell`: a navegação autenticada deixa de ser binária (`reader`/`admin`) e passa a refletir cinco papéis operacionais com visibilidade e acesso distintos.

## Impact

- Código afetado:
  - novo app Django e configuração associada
  - integração com banco PostgreSQL existente
  - camada de autenticação/autorização web
  - publicação PWA do novo shell
- Dependências:
  - adição de Django e bibliotecas de suporte ao app web
- Infraestrutura:
  - mesmo host do ATS atual com nova publicação web
  - configuração de proxy/rede para separar acesso intranet e remoto
- Segurança:
  - normalização de papéis operacionais
  - validação de origem de rede confiável para `nir` e `scheduler`
  - registro auditável de acessos autorizados e negados
- Mudança arquitetural:
  - **BREAKING**: esta fundação prepara a substituição da interface operacional baseada em mensagens por interface web, embora a migração funcional completa ocorra em changes seguintes.

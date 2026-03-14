# Dashboard PWA Mobile Installable

## Why

O dashboard é usado operacionalmente por líderes do Centro de Hemorragia Digestiva (CHD), inclusive em contexto mobile. Hoje ele depende de navegação via browser tradicional e não oferece experiência instalável na tela inicial, o que aumenta fricção de acesso no uso diário.

## What Changes

- Tornar o dashboard instalável como Progressive Web App (PWA) em Android e iOS, com abertura em `start_url=/dashboard/cases` e `display=standalone`.
- Adicionar estrutura PWA mínima: manifest, service worker focado em modo online (sem requisito de funcionamento offline) e metadados mobile/Apple.
- Introduzir conjunto de ícones do app seguindo identidade visual já usada no dashboard, com conceito textual:
  - `CHD` em destaque (maiúsculo, alto);
  - `dashboard` em tamanho menor abaixo;
  - composição final em formato quadrado para uso como app icon.
- Gerar e publicar tamanhos de ícone necessários para instalação em Android/iOS e navegação web.
- Melhorar usabilidade mobile das telas principais (`/dashboard/cases`, `/dashboard/cases/{case_id}`) e telas administrativas relevantes, priorizando leitura, toque e fluxo operacional.

## Capabilities

### New Capabilities

- `dashboard-pwa-installability`: capacidade de instalação em tela inicial (Android/iOS), com experiência standalone, manifesto web app, ícones e service worker online-only.
- `dashboard-mobile-usability`: experiência mobile otimizada para listagem, detalhe e navegação administrativa do dashboard.

### Modified Capabilities

- `case-thread-monitoring-dashboard`: expandir requisitos de experiência para uso mobile e acesso via app instalado, preservando os contratos de monitoramento já existentes.
- `web-login-session`: alinhar comportamento de sessão/redirecionamento para fluxo de abertura iniciado por `start_url=/dashboard/cases` em contexto de app instalado.

## Impact

- Código afetado (esperado): templates Jinja do dashboard/sessão, roteamento HTTP para assets estáticos de PWA, e arquivos estáticos (manifest, service worker, ícones).
- Testes afetados (esperado): integração de páginas dashboard/login e validações de presença de metadados/artefatos PWA.
- Operação/deploy: dependência de publicação com HTTPS (já recomendada no runbook) para experiência PWA consistente em produção.
- Fora de escopo desta mudança: suporte offline funcional e cache orientado a uso sem rede.

# Design

## Context

O ATS hoje possui uma superfície web enxuta em FastAPI para login, dashboard e áreas administrativas específicas, enquanto o fluxo operacional principal continua baseado em mensagens Matrix entre Room-1, Room-2 e Room-3. A decisão agora é migrar a interação humana para uma aplicação web baseada em Django, preservando o backend de orquestração clínica e a rastreabilidade já existente.

Este primeiro change entrega apenas a fundação necessária para essa migração:

- novo app Django separado do `bot-api` atual;
- autenticação local por usuário individual;
- taxonomia de papéis operacionais (`nir`, `doctor`, `scheduler`, `manager`, `admin`);
- shell inicial por papel, com PWA apenas para perfis remotos;
- restrições de acesso por zona de rede para `nir` e `scheduler`.

A migração dos fluxos funcionais NIR -> Médico -> Agendador -> Gestão/Admin fica para changes posteriores.

## Goals / Non-Goals

**Goals:**

- Introduzir um app Django separado, executado no mesmo host do ATS.
- Definir autenticação local e sessão web para cinco papéis operacionais.
- Garantir rastreabilidade individual por conta de usuário.
- Redirecionar cada papel para uma superfície web própria, ainda que inicialmente mínima.
- Aplicar proteção dupla para `nir` e `scheduler`: rede + aplicação.
- Manter modo PWA instalável apenas para `doctor`, `manager` e `admin` na publicação externa aprovada.
- Preparar a base para reuso do banco e da trilha de auditoria existentes.

**Non-Goals:**

- Migrar neste change os fluxos completos de upload NIR, decisão médica ou agendamento.
- Remover imediatamente o `bot-api` FastAPI existente.
- Introduzir MFA, SSO, LDAP/AD ou autenticação externa.
- Redesenhar a máquina de estados clínica.
- Revisar prompts, contratos LLM ou semântica dos jobs do worker.

## Decisions

### Decision 1: Introduzir o Django como app separado no mesmo host

- **Escolha:** criar um novo app Django independente do `bot-api` FastAPI, compartilhando o mesmo host e integrando-se gradualmente ao banco existente.
- **Racional:** reduz risco de regressão no runtime clínico atual e permite migração incremental da superfície humana.
- **Alternativas consideradas:**
  - migrar todo o `bot-api` para Django de uma vez;
    - rejeitada por elevar demais o risco e misturar fundação com migração funcional.
  - expandir a web atual em FastAPI;
    - rejeitada porque a exigência principal é aproveitar o ecossistema de auth/admin/estrutura do Django.

### Decision 2: Adotar contas locais individuais com papel explícito

- **Escolha:** usar autenticação local no Django com uma conta por pessoa e papéis explícitos `nir`, `doctor`, `scheduler`, `manager`, `admin`.
- **Racional:** atende à exigência de rastreabilidade individual e simplifica o controle de autorização role-aware desde o início.
- **Alternativas consideradas:**
  - contas compartilhadas por setor;
    - rejeitadas por enfraquecer auditoria.
  - autenticação corporativa externa;
    - rejeitada neste ciclo por ficar fora do escopo aprovado.

### Decision 3: Restringir `nir` e `scheduler` por duas camadas independentes

- **Escolha:** aplicar uma camada de bloqueio na publicação/rede e uma segunda camada obrigatória na aplicação Django.
- **Racional:** a diretoria exige restrição apenas na intranet; aplicar somente uma camada deixaria falhas operacionais perigosas.
- **Detalhes de desenho:**
  - camada de rede/proxy: limitar publicação externa e/ou acesso por CIDR autorizado;
  - camada de app: middleware/guard valida o IP de origem confiável antes de autorizar páginas desses papéis.
- **Alternativas consideradas:**
  - confiar apenas em firewall/proxy;
    - rejeitada por não registrar nem reforçar a política no nível da aplicação.
  - confiar apenas em regra de aplicação;
    - rejeitada por expor superfície desnecessária fora da intranet.

### Decision 4: Tratar IP de origem como dado confiado apenas atrás de proxy conhecido

- **Escolha:** a validação de intranet no app deve considerar configuração explícita de proxies confiáveis e cabeçalhos de forwarding aceitos.
- **Racional:** evita bypass por spoofing de cabeçalhos quando houver publicação por proxy/túnel.
- **Consequência:** a fundação deve prever configuração clara de `trusted proxies` e estratégia de resolução do client IP.

### Decision 5: Entregar rotas mínimas por papel já na fundação

- **Escolha:** após login, cada papel será redirecionado para uma rota dedicada do novo app Django, mesmo que inicialmente com conteúdo placeholder/smoke.
- **Racional:** isso trava desde cedo o contrato de navegação e reduz retrabalho nos changes de fluxo operacional.
- **Mapa inicial de destino:**
  - `nir` -> superfície NIR
  - `doctor` -> superfície médica
  - `scheduler` -> superfície de agendamento
  - `manager` -> dashboard/relatórios
  - `admin` -> administração do sistema

### Decision 6: Preservar a semântica PWA apenas para perfis remotos

- **Escolha:** o novo shell Django deve publicar manifest, service worker e metadata instalável sem offline clínico apenas para `doctor`, `manager` e `admin` no FQDN externo aprovado; `nir` e `scheduler` continuam em acesso desktop via browser na intranet, sem requisito de PWA.
- **Racional:** preserva a experiência já adotada para uso remoto/mobile sem impor PWA à operação interna desktop.
- **Alternativas consideradas:**
  - deixar PWA para depois;
    - rejeitada por reduzir adesão mobile logo na fundação.
  - introduzir suporte offline;
    - rejeitada por risco operacional e por contrariar a postura atual do projeto.

## Risks / Trade-offs

- **Risco:** divergência entre auth do Django novo e auth web atual.
  - **Mitigação:** explicitar nesta fase o novo boundary de autenticação e limitar o escopo a fundação, sem migrar fluxos operacionais ainda.
- **Risco:** configuração incorreta de IP de origem atrás de proxy/túnel.
  - **Mitigação:** validar proxies confiáveis de forma explícita e cobrir cenários positivos/negativos em testes.
- **Risco:** sobreposição de responsabilidades entre `manager` e `admin`.
  - **Mitigação:** fixar desde já que `manager` é read-only para dashboard/relatórios e `admin` concentra gestão de usuários/prompts/sistema.
- **Risco:** acoplamento excessivo ao schema atual do banco.
  - **Mitigação:** manter este change focado em fundação de identidade/acesso e postergar migrações funcionais de casos para changes específicos.

## Migration Plan

1. Criar o esqueleto do app Django e sua configuração de execução no repositório.
2. Definir modelo de usuário/roles e migrações iniciais da fundação de identidade.
3. Implementar login/logout/sessão e redirecionamento role-aware.
4. Implementar middleware/guard de zona de acesso para `nir` e `scheduler`.
5. Publicar shell PWA mínimo do novo app com páginas role-aware básicas.
6. Validar execução no mesmo host e preparar handoff para changes de migração funcional.

## Slice Plan

### Phase 1: Django bootstrap

- Slice 1.1: bootstrap do projeto Django com app operacional mínimo e smoke tests.

### Phase 2: Identity and roles

- Slice 2.1: modelo de usuário custom e enum de papéis operacionais.
- Slice 2.2: autenticação/sessão com login/logout e redirect por papel.

### Phase 3: Access zones

- Slice 3.1: resolução confiável de IP de origem.
- Slice 3.2: restrição intranet para `nir` e `scheduler` com auditoria de negação.

### Phase 4: PWA shell

- Slice 4.1: shell mínimo por papel e PWA online-only apenas para perfis remotos.

## Open Questions

- O domínio/rota inicial pública do novo app Django será separado por prefixo (`/app`, `/ops`) ou raiz dedicada do host.
- O formato exato dos logs/auditoria de acesso negado deve reutilizar a infraestrutura atual existente ou abrir uma trilha específica no novo app.
- Nenhuma no momento para PWA interna, porque `nir` e `scheduler` ficam limitados a browser desktop sem requisito instalável.

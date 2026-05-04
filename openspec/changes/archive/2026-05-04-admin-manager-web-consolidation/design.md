# Design

## Context

A fundação Django já fornece autenticação, shell PWA e separação por papéis. O change de migração operacional entrega NIR, fila médica, agendamento e confirmação final pela web. O próximo passo é consolidar a supervisão e a administração do sistema no Django, com duas responsabilidades bem separadas:

- `manager`: acompanhamento operacional e relatórios, sem mutações administrativas;
- `admin`: gestão de usuários, prompts e funções administrativas do sistema.

O objetivo não é redesenhar o dashboard ou a governança existente, mas mover essas superfícies para o novo app e explicitar seus contratos por papel. Este change assume o hard refactor já aprovado: não haverá compatibilidade legada nem convivência operacional entre a superfície antiga e a nova.

## Goals / Non-Goals

**Goals:**

- Entregar dashboard e detalhe de caso no Django para `manager` e `admin`.
- Garantir que `manager` tenha acesso apenas de leitura a supervisão/relatórios.
- Consolidar gestão de usuários e prompts sob `admin` no Django.
- Unificar a navegação autenticada final da aplicação.
- Preservar trilha auditável de ações administrativas e acesso a informações operacionais.

**Non-Goals:**

- Reintroduzir acesso administrativo para perfis operacionais.
- Mudar regras clínicas do workflow.
- Reabrir a discussão de auth, intranet ou PWA base.
- Implementar analytics avançado fora do escopo do dashboard atual.

## Decisions

### Decision 1: Separar supervisão de administração como contratos distintos

- **Escolha:** `manager` é estritamente read-only para dashboard/relatórios; `admin` continua com poderes administrativos sobre usuários, prompts e sistema.
- **Racional:** reflete a decisão já aprovada e reduz risco de permissões excessivas.
- **Alternativas consideradas:**
  - permitir que `manager` também administre prompts/usuários;
    - rejeitada por conflito com a definição de papéis.

### Decision 2: Consolidar primeiro a leitura operacional, depois as mutações administrativas

- **Escolha:** a consolidação do dashboard/detalhe no Django vem antes da finalização das áreas de usuários/prompts, e só deve começar após o slice `web-triage-workflow-migration/09-web-workflow-audit-visibility.md` estabilizar a timeline web completa.
- **Racional:** a leitura gerencial tem dependência direta do fluxo operacional já migrado e serve como base visual para `manager` e `admin`.

### Decision 3: Consolidar gestão de usuários e prompts nativamente no Django preservando invariantes

- **Escolha:** a superfície Django `admin` deve preservar as mesmas regras de segurança, autorização e auditabilidade já aprovadas para gestão de usuários e prompts, mas a implementação consolidada pode ser reescrita nativamente em Django em vez de espelhar estruturalmente a superfície legada em FastAPI/SQLAlchemy.
- **Racional:** o objetivo deste change é migrar a implementação humana/admin para o Django final, não manter compatibilidade interna com adapters legados. A referência legada serve para invariantes e comportamento externo, não para congelar a estrutura técnica.
- **Conseqüência:** `admin` pode criar usuários `nir`, `doctor`, `scheduler`, `manager` e `admin`, pode alterar o `role` de qualquer usuário, e a migração conceitual de contas legadas segue `reader -> manager` e `admin -> admin`.

### Decision 4: Tratar FastAPI/Matrix legados como referência de comportamento, não como dependência de consolidação

- **Escolha:** para superfícies humanas e administrativas cobertas por este change, FastAPI e Matrix passam a ser tratados como legado de referência, sem exigência de compatibilidade estrutural durante a consolidação no Django.
- **Racional:** evita que a migração fique presa a contratos internos do sistema antigo e reduz retrabalho nos slices finais.

### Decision 5: Manter o shell final explicitamente role-aware

- **Escolha:** a navegação consolidada deve expor:
  - para `manager`: dashboard/relatórios apenas;
  - para `admin`: dashboard, usuários, prompts e demais funções administrativas.
- **Racional:** a clareza visual de permissão é parte do controle operacional.

### Decision 6: Preservar o dashboard como fonte auditável de leitura cruzada do caso

- **Escolha:** o detalhe de caso consolidado no Django continua mostrando timeline, resumo operacional e contexto auditável do workflow.
- **Racional:** `manager` e `admin` precisam da mesma fonte de verdade operacional, com diferença apenas nas permissões laterais.

## Risks / Trade-offs

- **Risco:** divergência visual/funcional temporária entre superfícies antigas e novas.
  - **Mitigação:** slices com paridade funcional explícita e critérios de migração claros.
- **Risco:** permitir leitura excessiva ou mutação indevida por `manager`.
  - **Mitigação:** testes positivos/negativos de autorização em todos os entrypoints consolidados.
- **Risco:** inconsistência na migração conceitual de papéis legados para o modelo final.
  - **Mitigação:** tornar explícito que `reader -> manager` e `admin -> admin`, além de testar criação e mudança de role para os cinco papéis suportados.

## Migration Plan

1. Consolidar dashboard e detalhe de caso no Django para `manager` e `admin` após a timeline web completa estar estável.
2. Criar/ajustar a navegação final do shell com separação clara entre supervisão e administração.
3. Consolidar a superfície Django de usuários para `admin`, incluindo criação e mudança de role para os cinco papéis suportados.
4. Consolidar a superfície Django de prompts para `admin`.
5. Atualizar auditoria, testes e runbook manual com a matriz `manager` vs `admin`.
6. Preparar handoff para retirada imediata da superfície antiga quando este change estiver completo.

## Slice Plan

### Phase 1: Dashboard consolidation

- Slice 1.1: dashboard consolidado no Django para `manager` e `admin`.
- Slice 1.2: detalhe de caso consolidado e consistente com timeline auditável.

### Phase 2: Role-aware shell consolidation

- Slice 2.1: navegação final role-aware para `manager` vs `admin`.

### Phase 3: Admin surfaces

- Slice 3.1: gestão de usuários consolidada no Django para `admin`.
- Slice 3.2: gestão de prompts consolidada no Django para `admin`.

### Phase 4: Verification and cutover handoff

- Slice 4.1: auditoria, runbook manual, verificação de autorização e handoff de cutover/desativação da superfície antiga.

## Open Questions

- A superfície de auditoria administrativa terá uma página própria neste change ou ficará implícita nos detalhes de caso e nos registros já existentes.
- Nenhuma aberta no momento sobre soak period, porque o refactor foi aprovado como hard cutover sem convivência legada.

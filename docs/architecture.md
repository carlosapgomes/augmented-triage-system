# Arquitetura

Idioma: **Português (BR)** | [English](en/architecture.md)

## Visão Geral

> **Direção atual do refactor web:** para superfícies humanas e administrativas cobertas pelos changes web ativos, o Django é a implementação alvo. FastAPI e Matrix devem ser tratados como legado de referência para comportamento, auditoria e integração remanescente, não como baseline obrigatório de compatibilidade estrutural.

O sistema é dividido em quatro apps deployáveis mais PostgreSQL:

- `bot-api`: ingress HTTP para fundação de login/auth e endpoints de suporte de runtime.
- `bot-matrix`: integração Matrix para eventos de intake/reação.
- `worker`: consumidor async de fila para extração, jobs LLM, postagem e cleanup.
- `django-ops`: web app Django para interface humana (dashboard, login, gestão de prompts, fluxo web de triagem).
- `postgres`: fonte de verdade para casos, jobs, mapeamento de mensagens e trilha de auditoria.

## Camadas e direção de dependência

O código segue esta direção de dependência:

- adapters (`apps`, `infrastructure/http`, `infrastructure/matrix`)
- serviços e portas de aplicação (`src/triage_automation/application`)
- dominio (`src/triage_automation/domain`)
- implementacoes de infraestrutura (`src/triage_automation/infrastructure`)

Regras:

- lógica de negócio pertence a `application` e `domain`
- adapters devem permanecer enxutos
- detalhes de infraestrutura são consumidos via portas

## Módulos principais

- Settings: `src/triage_automation/config/settings.py`
- Metadata de banco: `src/triage_automation/infrastructure/db/metadata.py`
- Job queue: `src/triage_automation/infrastructure/db/job_queue_repository.py`
- Rota de auth/login: `src/triage_automation/infrastructure/http/auth_router.py`
- Montagem do runtime Bot API: `apps/bot_api/main.py`
- Web app Django (dashboard, login, gestão): `apps/django_ops/`

## Notas do workflow

- O ciclo de vida da triagem é dirigido por máquina de estados (veja `PROJECT_CONTEXT.md` para estados canônicos).
- Durante o refactor web, a interface humana operacional e administrativa consolidada deve migrar para `django-ops`; referências a superfícies humanas em FastAPI/Matrix são legadas para consulta e retirada controlada.
- O cleanup é disparado pela primeira reação de thumbs-up na resposta final da Sala 1, salvo quando um change web aprovado mover explicitamente esse checkpoint para uma ação web equivalente.
- O monitoramento e a administração finais deste programa devem convergir para a superfície Django consolidada.
- O gerenciamento de prompts segue com acesso de `admin` na superfície administrativa.

## Modelo de persistência (alto nível)

- `cases`: ciclo de vida do caso e artefatos
- `case_events`: entradas append-only de auditoria
- `case_messages`: mapeamentos de sala/evento Matrix
- `jobs`: registros de fila com retry/scheduling
- `prompt_templates`: prompts versionados com uma versão ativa por nome
- `users` e `auth_tokens`: fundação de auth e controle de acesso

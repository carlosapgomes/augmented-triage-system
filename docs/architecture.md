# Arquitetura

Idioma: **Português (BR)** | [English](en/architecture.md)

## Visão Geral

> **Superfície final suportada:** o Django (`django-ops`) é a superfície humana e administrativa final e suportada deste programa. FastAPI e Matrix são componentes de runtime de backend — **suas superfícies humanas e administrativas foram retiradas e não devem ser tratadas como baseline de compatibilidade.** As referências a essas superfícies no código e nos artefatos deste repositório são exclusivamente legado/back-end.

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

## Superfície humana e administrativa final

- **Django (`django-ops`) é a única superfície humana e administrativa suportada.**
  Todas as interações humanas (NIR, médico, agendador, gestor, admin) são consolidadas
  exclusivamente no app Django na porta 8001.
- FastAPI (`bot-api`) e Matrix (`bot-matrix`) são componentes de **runtime de backend**
  e não expõem mais superfícies humanas/administrativas. Suas rotas HTML, endpoints
  de gestão de usuários e superfícies de gerenciamento de prompts foram retiradas.
- **Não há requisito de compatibilidade legada** com as superfícies humanas/admin
  antigas de FastAPI ou Matrix após o cutover.

### Papéis consolidados

- `manager`: somente leitura (dashboard operacional, detalhe de caso, timeline auditável).
- `admin`: único papel com poderes de mutação sobre usuários, prompts e sistema.

### Exceção arquitetural consciente: tabela `prompt_templates`

A tabela `prompt_templates` é um **componente de backend compartilhado** gerenciado
por Alembic/SQLAlchemy. Ela é lida e escrita pelos serviços de LLM, pipeline de
extração e bot Matrix — componentes que usam SQLAlchemy/asyncpg. O adaptador
`DjangoOrmPromptStoreAdapter` (`apps/django_ops/django_prompt_store_adapter.py`)
utiliza a infraestrutura SQLAlchemy compartilhada para persistência de prompts.

**Esta exceção é exclusivamente de backend:**

- Trata-se de um detalhe de runtime compartilhado entre componentes de backend.
- **Não reintroduz dependência da superfície administrativa legada de FastAPI/Matrix.**
- A superfície administrativa de prompts é 100% Django (views, templates,
  autorização por sessão).
- O contrato de domínio (`DjangoPromptStorePort`, `DjangoPromptManagementService`)
  permanece independente de infraestrutura.

## Notas do workflow

- O ciclo de vida da triagem é dirigido por máquina de estados (veja `PROJECT_CONTEXT.md` para estados canônicos).
- O cleanup é disparado pela primeira reação de thumbs-up na resposta final da Sala 1, salvo quando um change web aprovado mover explicitamente esse checkpoint para uma ação web equivalente.
- O checkpoint canônico de fechamento humano agora é a ação web `NIR_FINAL_ACKNOWLEDGMENT` (NIR confirma recebimento via Django), substituindo a reação thumbs-up na Room-1 do Matrix como gatilho humano.
- O monitoramento e a administração finais deste programa convergem para a superfície Django consolidada.
- O gerenciamento de prompts segue com acesso de `admin` na superfície administrativa Django.

## Modelo de persistência (alto nível)

- `cases`: ciclo de vida do caso e artefatos
- `case_events`: entradas append-only de auditoria
- `case_messages`: mapeamentos de sala/evento Matrix
- `jobs`: registros de fila com retry/scheduling
- `prompt_templates`: prompts versionados com uma versão ativa por nome
- `users` e `auth_tokens`: fundação de auth e controle de acesso

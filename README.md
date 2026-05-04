# Augmented Triage System (ATS)

Idioma: **Português (BR)** | [English](README.en.md)

![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Lint](https://img.shields.io/badge/lint-ruff-orange.svg)
![Type Check](https://img.shields.io/badge/types-mypy-blue.svg)
![Tests](https://img.shields.io/badge/tests-pytest-brightgreen.svg)

Augmented Triage System (ATS) é um serviço de backend projetado para apoiar fluxos reais de triagem clínica, mantendo profissionais de saúde totalmente no controle das decisões e do cuidado ao paciente.

O ATS não substitui o julgamento clínico nem automatiza decisões médicas.
O sistema foi projetado para apoiar comunicação, organização e fluxo de informações durante a triagem, permitindo que profissionais trabalhem com mais segurança e eficiência em ambientes de alta demanda.

O objetivo principal do ATS é melhorar coordenação, rastreabilidade e consciência situacional durante processos de triagem.

O ATS é uma ferramenta de apoio para equipes de saúde e deve sempre ser utilizado sob supervisão profissional e dentro de protocolos clínicos estabelecidos.

Serviços de backend para um fluxo de triagem orientado a eventos em salas Matrix.

> **Superfície final suportada:** o Django (`django-ops`) é a superfície humana e administrativa final deste projeto. FastAPI e Matrix são componentes de runtime de backend. As referências a superfícies humanas/admin legadas neste README são mantidas apenas para cutover e troubleshooting de retirada.

Serviços principais:

- `bot-api` (API FastAPI — runtime de backend, endpoints internos)
- `bot-matrix` (integração de ingestão de eventos Matrix)
- `worker` (runtime de execução de jobs)
- `django-ops` (web app Django — superfície humana e administrativa oficial, porta 8001)

Este repositório é implementado com TDD estrito e histórico de slices OpenSpec em `openspec/changes/archive/`.

## Por Que Este Projeto

- Automatiza fluxo de triagem em múltiplas etapas entre salas Matrix.
- Preserva auditabilidade com registros append-only.
- Usa transições de estado determinísticas e jobs em fila.
- Adiciona fundações administrativas (roles, auth e prompts) sem introduzir comportamento de UI no runtime clínico.

## Escopo Atual

- A fundação do fluxo de triagem está implementada e coberta por testes automatizados.
- A superfície humana e administrativa está consolidada no `django-ops` (porta 8001):
  - fluxo web de sessão (`GET /login/`, `POST /login/`, `POST /logout/`)
  - dashboard e detalhe de caso (`/manager/`, `/manager/cases/<uuid>/`)
  - fluxo operacional web (NIR, médico, agendador)
  - admin de prompts (`/admin/prompts/`) e usuários (`/admin/users/`)
- `bot-api` (porta 8000) permanece como runtime de backend:
  - autenticação por token opaco (`POST /auth/login`)
  - endpoints internos de suporte de runtime
  - callback widget da Room-2 (assinatura HMAC)

## Topologia de Runtime

```text
Matrix Rooms ---> bot-matrix ----\
                                  \
Operadores Web ------> django-ops ----> PostgreSQL <---- worker
                          |
Login/Auth (token) -> bot-api (backend)
```

### Caminhos de acesso

| Caminho | Porta | Uso |
| --- | --- | --- |
| `django-ops` | 8001 | Superfície humana/admin (todos os papéis) |
| `bot-api` | 8000 | Backend runtime (token auth, callback widget) |
| `postgres` | 5432 | Somente loopback |

Para a topologia completa de publicação (interno vs externo, Cloudflare Tunnel, matriz de acesso por zona), veja `docs/publication-topology.md`.

## Superficie Publica (Atual)

### Superfície humana — Django (`django-ops`, porta 8001)

Páginas web e rotas de sessão:

- `GET /login/`
- `POST /login/`
- `POST /logout/`
- `GET /nir/`, `GET /nir/upload/` (NIR)
- `GET /doctor/`, `GET /doctor/cases/{id}/decision/` (médico)
- `GET /scheduler/`, `GET /scheduler/cases/{id}/confirm/` (agendador)
- `GET /manager/`, `GET /manager/cases/{id}/` (gestor — dashboard e detalhe de caso)
- `GET /admin/`, `GET /admin/prompts/`, `GET /admin/users/` (admin)

### Superfície de backend — FastAPI (`bot-api`, porta 8000)

Rotas internas/de suporte:

- `POST /auth/login` (emissão de token opaco)
- `POST /widget/room2/submit` (callback HMAC da Room-2)
- `GET /openapi.json` (schema interno)

## Acesso Web e Papéis

Fluxo de acesso pelo navegador (Django, porta 8001):

1. Abra `http://127.0.0.1:8001/` no navegador.
1. Acesso anônimo é redirecionado para `/login/`.
1. Envie email e senha no formulário de login.
1. Em caso de sucesso, o app redireciona conforme o papel:
   - `nir` → `/nir/`
   - `doctor` → `/doctor/`
   - `scheduler` → `/scheduler/`
   - `manager` → `/manager/`
   - `admin` → `/admin/`
1. Use `Sair` (`POST /logout/`) para encerrar a sessão.

Matriz de papéis:

| Papel | Dashboard | Fluxo operacional | Admin prompts | Admin usuários |
| --- | --- | --- | --- | --- |
| `nir` | — | upload PDF, fechamento | — | — |
| `doctor` | — | decisão médica web | — | — |
| `scheduler` | — | confirmação de agendamento | — | — |
| `manager` | leitura | — | — | — |
| `admin` | leitura | — | permitido | permitido |

## Documentação do Projeto

- Setup: `docs/setup.md`
- Operações admin (bootstrap + reset de senha): `docs/setup.md#8-operacoes-de-admin`
- Runbook operacional Ansible (instalação inicial): `docs/ansible_ops_runbook.md`
- Runbook de smoke de runtime: `docs/runtime-smoke.md`
- Runbook manual E2E: `docs/manual_e2e_runbook.md`
- Arquitetura: `docs/architecture.md`
- Topologia de publicação: `docs/publication-topology.md`
- Checklist de hardening por zona: `docs/zone-hardening-checklist.md`
- Motor de decisão e rulebook: `docs/decision-engine-and-rulebook.md`
- Seguranca: `docs/security.md`
- Contexto interno de implementação: `PROJECT_CONTEXT.md`

## Checklist de contribuição da documentação bilíngue

1. Alterou `README.md`? Atualize `README.en.md` no mesmo PR.
1. Alterou `docs/<arquivo>.md`? Atualize `docs/en/<arquivo>.md` no mesmo PR.
1. Mantenha os seletores de idioma no topo dos dois arquivos espelhados.
1. Execute:

```bash
uv run pytest tests/unit/test_readme_bilingual_baseline.py tests/unit/test_docs_bilingual_mirror.py -q
markdownlint-cli2 "README.md" "README.en.md" "docs/*.md" "docs/en/*.md"
```

## Estrutura do Repositório

```text
apps/                         # Entrypoints de runtime (bot-api, bot-matrix, worker)
src/triage_automation/        # Código de application/domain/infrastructure
alembic/                      # Migrações de banco
tests/                        # Testes unitários, integração e e2e
docs/                         # Documentação pública do projeto
openspec/                     # Artefatos de change/spec
```

## Início Rápido

1. Instale dependências:

```bash
uv sync
```

1. Crie arquivo de ambiente local:

```bash
cp .env.example .env
```

1. Execute migrações de banco:

```bash
uv run alembic upgrade head
```

1. Opcional: bootstrap do primeiro admin no startup (uma vez, quando `users` estiver vazio):

```bash
export BOOTSTRAP_ADMIN_EMAIL=admin@example.org
export BOOTSTRAP_ADMIN_PASSWORD='change-me-now'
```

Para ambientes mais próximos de produção, prefira `BOOTSTRAP_ADMIN_PASSWORD_FILE`.

1. Execute quality gates locais:

```bash
uv run ruff check .
uv run mypy src apps
uv run pytest -q
```

## Serviços Locais (Docker Compose)

```bash
docker compose up --build
```

O Compose espera `.env` presente e inicia:

- `postgres`
- `bot-api`
- `bot-matrix`
- `worker`
- `django-ops`

## Nota de Deploy

Este repositório está otimizado atualmente para deploy local/dev com Docker Compose.
Para deploy em produção, adicione hardening específico de ambiente (integração com secret manager,
política de rede, terminação TLS e observabilidade).

## CI

Quality gates são aplicados em `.github/workflows/quality-gates.yml`.

## Licença

MIT. Veja `LICENSE`.

## Créditos

Este projeto foi desenvolvido com assistência de modelos de linguagem de grande porte (LLMs).

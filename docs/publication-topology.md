# Topologia de Publicação

Idioma: **Português (BR)** | [English](en/publication-topology.md)

Este documento define a topologia oficial de publicação do ATS em
single-host, separando objetivamente os caminhos de acesso interno
(intranet) e externo (Cloudflare Tunnel).

> **Superfície final suportada:** o Django (`django-ops`, porta 8001) é a
> única superfície humana e administrativa publicada. FastAPI (`bot-api`) e
> Matrix (`bot-matrix`) são componentes de runtime de backend e não devem
> ser expostos externamente em nenhum caminho de publicação suportado.

## Visão Geral

Toda a stack consolidada roda no mesmo host com Docker rootless:

| Serviço | Porta | Exposição |
| --- | --- | --- |
| `postgres` | 5432 | somente loopback (nunca exposto) |
| `bot-api` | 8000 | somente loopback (backend runtime) |
| `bot-matrix` | — | somente loopback (conexão outbound Matrix) |
| `worker` | — | somente loopback (consumidor de fila interno) |
| `django-ops` | 8001 | loopback + túnel externo controlado |

## Caminhos de Acesso

### Acesso Interno (Intranet)

O acesso interno é feito diretamente ao `django-ops` via `http://127.0.0.1:8001`
ou através de um reverse proxy interno controlado (Nginx/Caddy) encaminhando
para `127.0.0.1:8001`.

Todos os papéis operacionais têm acesso ao caminho interno:

- `nir`
- `doctor`
- `scheduler`
- `manager`
- `admin`

### Acesso Externo (Cloudflare Tunnel)

O único caminho de acesso remoto suportado é o **Cloudflare Tunnel** apontando
para `http://127.0.0.1:8001` (Django).

Apenas os seguintes papéis têm acesso pelo caminho externo:

- `doctor` — acesso remoto permitido
- `manager` — acesso remoto permitido
- `admin` — acesso remoto permitido

Os papéis `nir` e `scheduler` são **bloqueados no caminho externo** — o túnel
ou proxy externo NÃO deve encaminhar requisições para esses papéis. Esta
restrição opera na camada de publicação/rede e é adicional ao bloqueio
app-level já existente.

```text
[Internet]
    │
    ▼
[Cloudflare Tunnel] ─── FQDN público (HTTPS obrigatório)
    │
    ▼ (bloqueio de nir/scheduler no túnel)
[127.0.0.1:8001] django-ops
    │
    ├── /login/
    ├── /nir/*       ← bloqueado no caminho externo
    ├── /doctor/*    ← permitido externamente
    ├── /scheduler/* ← bloqueado no caminho externo
    ├── /dashboard/* ← permitido externamente (manager)
    └── /admin/*     ← permitido externamente (admin)
```

## Matriz de Acesso por Papel e Zona

| Papel | Acesso Interno | Acesso Externo (Túnel) |
| --- | --- | --- |
| `nir` | ✓ `http://127.0.0.1:8001` | ✗ Bloqueado no túnel/proxy |
| `doctor` | ✓ `http://127.0.0.1:8001` | ✓ Via Cloudflare Tunnel |
| `scheduler` | ✓ `http://127.0.0.1:8001` | ✗ Bloqueado no túnel/proxy |
| `manager` | ✓ `http://127.0.0.1:8001` | ✓ Via Cloudflare Tunnel |
| `admin` | ✓ `http://127.0.0.1:8001` | ✓ Via Cloudflare Tunnel |

## Critérios de Validação

Os critérios abaixo são objetivos e devem ser verificados após cada deploy
ou mudança de topologia.

### 1. Serviços de backend nunca expostos externamente

Nenhum dos serviços abaixo pode ser alcançado a partir da rede externa:

- `bot-api` (porta 8000)
- `postgres` (porta 5432)
- `bot-matrix` e `worker` (sem portas expostas)

Validação:

```bash
# A partir de uma máquina externa, confirmar que as portas não respondem:
curl -s --connect-timeout 5 http://<host-remoto>:8000/ && echo "FALHA: bot-api exposto" || echo "OK: bot-api inacessível"
curl -s --connect-timeout 5 http://<host-remoto>:5432/ && echo "FALHA: postgres exposto" || echo "OK: postgres inacessível"
```

No host:

```bash
# Confirmar que apenas django-ops (8001) escuta em todas as interfaces quando aplicável:
ss -tlnp | grep -E ':(8000|8001|5432)'
# Esperado: 8001 pode escutar em 0.0.0.0 ou 127.0.0.1 conforme configuração de proxy;
# 8000 e 5432 devem escutar apenas em 127.0.0.1
```

### 2. Acesso externo restrito aos papéis remotos

Validação a partir de uma máquina fora da intranet, usando o FQDN público:

```bash
# doctor — acesso esperado (login deve ser possível):
curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/login/ --connect-timeout 10
# Esperado: 200

# nir — acesso NÃO esperado (deve ser barrado no túnel/proxy):
curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/nir/ --connect-timeout 10
# Esperado: 403 ou 404 (a rota não deve ser alcançável externamente)

# scheduler — acesso NÃO esperado:
curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/scheduler/ --connect-timeout 10
# Esperado: 403 ou 404
```

### 3. Coerência entre topologia e regras app-level

Após validar os critérios de rede, confirmar que as regras de autorização da
aplicação também estão ativas:

- `nir` autenticado internamente: acesso a `/nir/*` — `200`
- `nir` autenticado externamente (se túnel não bloquear): acesso a `/nir/*` — `403` (app-level)
- `scheduler` autenticado internamente: acesso a `/scheduler/*` — `200`
- `scheduler` autenticado externamente (se túnel não bloquear): acesso a `/scheduler/*` — `403` (app-level)

### 4. HTTPS no caminho externo

```bash
# Confirmar que HTTP sem TLS redireciona ou rejeita:
curl -s -o /dev/null -w "%{http_code}" http://<fqdn>/login/ --connect-timeout 10
# Esperado: 301 (redirect para HTTPS) ou conexão recusada
```

## Decisões de Topologia

1. **Single-host como baseline**: todo o stack consolidado roda no mesmo host,
   sem balanceamento ou HA neste ciclo.

2. **Publicação por topologia, não apenas por UI**: a segregação entre papéis
   de intranet e remotos ocorre na camada de rede/publicação (túnel/proxy),
   antes da aplicação. O bloqueio app-level é uma camada adicional, não
   substituta.

3. **Cloudflare Tunnel como único caminho remoto**: não há suporte para
   VPN corporativa, SSH tunneling, ou port forwarding como caminhos
   alternativos de acesso remoto nesta topologia.

4. **Autenticação somente na aplicação**: o Cloudflare Tunnel não aplica
   autenticação adicional (Cloudflare Access). Toda autenticação e autorização
   é gerenciada pelo Django.

5. **Superfícies legadas fora do escopo**: FastAPI (`bot-api`) e Matrix
   (`bot-matrix`) não são superfícies de publicação. Suas rotas HTTP/HTTPS
   são exclusivamente para comunicação interna entre componentes de backend.

## Limitações Conscientes

- Não há suporte a múltiplos hosts ou topologias HA.
- Não há autenticação no nível do túnel (Cloudflare Access) — a autenticação
  é exclusivamente app-level.
- O caminho interno não exige um reverse proxy (acesso direto a
  `127.0.0.1:8001` é suportado), mas recomenda-se o uso de proxy interno
  controlado em ambientes próximos de produção.
- O troubleshooting detalhado de falhas de publicação está documentado no
  runbook operacional (`docs/ansible_ops_runbook.md`), não neste documento
  de topologia.

## Referências

- Runbook operacional: `docs/ansible_ops_runbook.md`
- Runbook manual E2E: `docs/manual_e2e_runbook.md`
- Guia de setup: `docs/setup.md`
- Arquitetura: `docs/architecture.md`

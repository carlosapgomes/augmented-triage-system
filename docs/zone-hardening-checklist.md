# Checklist de Hardening por Zona e Papel

Idioma: **Português (BR)** | [English](en/zone-hardening-checklist.md)

Este documento complementa a topologia oficial de publicação
(`docs/publication-topology.md`) com um checklist operacional de hardening
por zona e papel, passos determinísticos de validação e troubleshooting de
primeira linha para falhas de acesso.

> **Superfície final suportada:** o Django (`django-ops`, porta 8001) é a
> única superfície humana publicada. Este documento não reintroduz
> dependência operacional de superfícies humanas legadas (FastAPI, Matrix).

## Matriz de Verificação por Papel e Zona

O checklist abaixo deve ser executado em sequência após cada deploy, upgrade,
rollback ou mudança de configuração de publicação.

### Checklist de hardening — acesso interno (intranet)

| # | Papel | Verificação | Esperado | Comando |
| --- | --- | --- | --- | --- |
| 1 | `nir` | Login interno | `200` | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/login/` |
| 2 | `nir` | Acesso rota `/nir/` | `200` ou `302` (redireciona para login se não autenticado) | validar via navegador autenticado em `http://127.0.0.1:8001/nir/` |
| 3 | `doctor` | Login interno | `200` | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/login/` |
| 4 | `doctor` | Acesso rota `/doctor/` | `200` ou `302` | validar via navegador autenticado em `http://127.0.0.1:8001/doctor/` |
| 5 | `scheduler` | Login interno | `200` | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/login/` |
| 6 | `scheduler` | Acesso rota `/scheduler/` | `200` ou `302` | validar via navegador autenticado em `http://127.0.0.1:8001/scheduler/` |
| 7 | `manager` | Login interno | `200` | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/login/` |
| 8 | `manager` | Acesso rota `/manager/` | `200` ou `302` | validar via navegador autenticado em `http://127.0.0.1:8001/manager/` |
| 9 | `admin` | Login interno | `200` | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/login/` |
| 10 | `admin` | Acesso rota `/admin/` | `200` ou `302` | validar via navegador autenticado em `http://127.0.0.1:8001/admin/` |

### Checklist de hardening — acesso externo (Cloudflare Tunnel)

| # | Papel | Verificação | Esperado | Comando |
| --- | --- | --- | --- | --- |
| 11 | `nir` | Acesso remoto rota `/nir/` | **403** ou **404** (bloqueado no túnel/proxy) | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/nir/ --connect-timeout 10` |
| 12 | `nir` | Acesso remoto rota `/login/` | `200` (login pode ser alcançado, autorização barra depois) | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/login/ --connect-timeout 10` |
| 13 | `doctor` | Acesso remoto rota `/doctor/` | `200` (permitido externamente) | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/doctor/ --connect-timeout 10` |
| 14 | `scheduler` | Acesso remoto rota `/scheduler/` | **403** ou **404** (bloqueado no túnel/proxy) | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/scheduler/ --connect-timeout 10` |
| 15 | `manager` | Acesso remoto rota `/manager/` | `200` (permitido externamente) | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/manager/ --connect-timeout 10` |
| 16 | `admin` | Acesso remoto rota `/admin/` | `200` (permitido externamente) | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/admin/ --connect-timeout 10` |

### Checklist de hardening — negação explícita para papéis de intranet

| # | Verificação | Esperado | Comando |
| --- | --- | --- | --- |
| 17 | `nir` **negado** no caminho externo | `nir` não consegue acessar nenhuma rota via FQDN externo além de `/login/` | verificar que Cloudflare Tunnel ou proxy bloqueia `/nir/*` |
| 18 | `scheduler` **negado** no caminho externo | `scheduler` não consegue acessar nenhuma rota via FQDN externo além de `/login/` | verificar que Cloudflare Tunnel ou proxy bloqueia `/scheduler/*` |

### Checklist de hardening — acesso remoto aprovado para papéis remotos

| # | Verificação | Esperado | Comando |
| --- | --- | --- | --- |
| 19 | `doctor` aprovado | rotas `/doctor/*` alcançáveis externamente via túnel | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/doctor/ --connect-timeout 10` |
| 20 | `manager` aprovado | rotas `/manager/*` alcançáveis externamente via túnel | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/manager/ --connect-timeout 10` |
| 21 | `admin` aprovado | rotas `/admin/*` alcançáveis externamente via túnel | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/admin/ --connect-timeout 10` |

## Passos de Validação

Os passos abaixo cobrem a validação determinística do hardening por zona.
Execute na ordem e registre os resultados.

### Passo 1 — Validação de portas e escuta no host

```bash
# Confirmar que apenas django-ops (8001) pode escutar em todas as interfaces;
# bot-api (8000) e postgres (5432) devem escutar apenas em 127.0.0.1.
ss -tlnp | grep -E ':(8000|8001|5432)'
```

Critério de sucesso:

- `8001`: pode escutar em `0.0.0.0` ou `127.0.0.1` conforme configuração de proxy.
- `8000` e `5432`: devem escutar apenas em `127.0.0.1`.

### Passo 2 — Validação de negação de intranet-only no caminho externo

```bash
# A partir de máquina externa (fora da intranet):
FQDN="<seu-fqdn>"

# nir — deve ser negado (403 ou 404):
STATUS_NIR=$(curl -s -o /dev/null -w "%{http_code}" "https://${FQDN}/nir/" --connect-timeout 10)
if [ "$STATUS_NIR" = "403" ] || [ "$STATUS_NIR" = "404" ]; then
  echo "PASS: nir bloqueado externamente (HTTP $STATUS_NIR)"
else
  echo "FAIL: nir alcançável externamente (HTTP $STATUS_NIR)"
fi

# scheduler — deve ser negado (403 ou 404):
STATUS_SCH=$(curl -s -o /dev/null -w "%{http_code}" "https://${FQDN}/scheduler/" --connect-timeout 10)
if [ "$STATUS_SCH" = "403" ] || [ "$STATUS_SCH" = "404" ]; then
  echo "PASS: scheduler bloqueado externamente (HTTP $STATUS_SCH)"
else
  echo "FAIL: scheduler alcançável externamente (HTTP $STATUS_SCH)"
fi
```

### Passo 3 — Validação de acesso remoto aprovado

```bash
# A partir de máquina externa:
FQDN="<seu-fqdn>"

# doctor — deve ser permitido:
STATUS_DOC=$(curl -s -o /dev/null -w "%{http_code}" "https://${FQDN}/doctor/" --connect-timeout 10)
if [ "$STATUS_DOC" = "200" ] || [ "$STATUS_DOC" = "302" ]; then
  echo "PASS: doctor acessível externamente (HTTP $STATUS_DOC)"
else
  echo "FAIL: doctor inacessível externamente (HTTP $STATUS_DOC)"
fi

# manager — deve ser permitido:
STATUS_MGR=$(curl -s -o /dev/null -w "%{http_code}" "https://${FQDN}/manager/" --connect-timeout 10)
if [ "$STATUS_MGR" = "200" ] || [ "$STATUS_MGR" = "302" ]; then
  echo "PASS: manager acessível externamente (HTTP $STATUS_MGR)"
else
  echo "FAIL: manager inacessível externamente (HTTP $STATUS_MGR)"
fi

# admin — deve ser permitido:
STATUS_ADM=$(curl -s -o /dev/null -w "%{http_code}" "https://${FQDN}/admin/" --connect-timeout 10)
if [ "$STATUS_ADM" = "200" ] || [ "$STATUS_ADM" = "302" ]; then
  echo "PASS: admin acessível externamente (HTTP $STATUS_ADM)"
else
  echo "FAIL: admin inacessível externamente (HTTP $STATUS_ADM)"
fi
```

### Passo 4 — Validação de HTTPS no caminho externo

```bash
# Confirmar que HTTP sem TLS redireciona ou rejeita:
curl -s -o /dev/null -w "%{http_code}" http://<fqdn>/login/ --connect-timeout 10
```

Critério de sucesso: `301` (redirect para HTTPS) ou conexão recusada.

### Passo 5 — Validação de coerência entre topologia e regras app-level

```bash
# Internamente, autenticar como nir e acessar /nir/ — esperado 200
# Externamente, se o túnel não bloquear completamente, autenticar como nir
# e acessar /nir/ — esperado 403 (bloqueio app-level)
```

Critério de sucesso:

- `nir` autenticado internamente: acesso a `/nir/*` retorna `200`.
- `nir` autenticado externamente (se túnel não bloquear): acesso a `/nir/*` retorna `403` (app-level).
- O mesmo para `scheduler` e `/scheduler/*`.

## Troubleshooting

O troubleshooting abaixo cobre falhas de primeiro nível. Quando a causa
raiz não for identificada ou a correção não resolver, siga os critérios
de escalonamento.

### Sintoma 1 — Papel permitido externamente não consegue acessar rota remota

**Exemplo:** `doctor` ou `manager` ou `admin` recebem erro ao acessar rota
via FQDN externo.

Diagnóstico:

1. Verificar status do Cloudflare Tunnel:

   ```bash
   # No host, confirmar que o túnel está ativo e apontando para 127.0.0.1:8001
   cloudflared tunnel info <nome-do-túnel>
   ```

2. Verificar que o `django-ops` está respondendo localmente:

   ```bash
   curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/login/
   # Esperado: 200
   ```

3. Verificar configuração de DNS — confirmar que o FQDN resolve para o túnel:

   ```bash
   dig +short <fqdn>
   # Deve retornar IPs do Cloudflare (não o IP direto do host)
   ```

4. Verificar que o proxy reverso (se houver) não está bloqueando a rota:

   ```bash
   # Testar acesso local direto ao Django, ignorando o proxy:
   curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/doctor/
   # Esperado: 200 ou 302
   ```

5. Se o Django responde localmente mas o túnel não entrega, revisar logs:

   ```bash
   journalctl -u cloudflared --since "10 min ago" --no-pager | tail -30
   ```

### Sintoma 2 — Papel de intranet-only está acessível externamente

**Exemplo:** `nir` ou `scheduler` conseguem acessar rotas via FQDN externo
(retornando `200` em vez de `403` ou `404`).

Diagnóstico:

1. Verificar se o Cloudflare Tunnel ou proxy reverso está filtrando
   corretamente as rotas de intranet-only (`/nir/*`, `/scheduler/*`):

   ```bash
   # Testar cada rota bloqueada externamente:
   curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/nir/ --connect-timeout 10
   curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/scheduler/ --connect-timeout 10
   # Esperado: 403 ou 404
   ```

2. Se o túnel entrega as rotas, o bloqueio precisa ser configurado no proxy
   reverso (Nginx/Caddy) ou no próprio Cloudflare Tunnel:

   - **Nginx:** adicionar `deny all;` para `location /nir/` e `location /scheduler/`
     no bloco de servidor externo.
   - **Caddy:** usar diretiva `respond` com status 403 para essas rotas.
   - **Cloudflare Tunnel:** configurar regras de acesso no dashboard para
     bloquear paths `/nir/*` e `/scheduler/*`.

3. Confirmar que o bloqueio app-level está ativo como camada adicional:

   ```bash
   # Autenticar como nir externamente e verificar se a aplicação retorna 403:
   curl -s -o /dev/null -w "%{http_code}" \
     -H "Cookie: sessionid=<token-de-sessão-nir>" \
     https://<fqdn>/nir/ --connect-timeout 10
   # Esperado: 403 (app-level block)
   ```

### Sintoma 3 — Porta de backend responde externamente

**Exemplo:** `bot-api` (8000) ou `postgres` (5432) respondem a partir de
máquina externa.

Diagnóstico:

1. No host, verificar escuta de portas:

   ```bash
   ss -tlnp | grep -E ':(8000|5432)'
   # Esperado: LISTEN apenas em 127.0.0.1 (loopback)
   ```

2. Se alguma porta estiver escutando em `0.0.0.0` ou `*`, revisar
   configuração do Docker Compose (`ports` vs `expose`) e corrigir para
   expor apenas em loopback.

3. Verificar regras de firewall no host:

   ```bash
   sudo ufw status verbose
   # Esperado: apenas portas de túnel/proxy autorizadas externamente
   ```

### Sintoma 4 — HTTPS não está ativo no caminho externo

**Exemplo:** `curl http://<fqdn>/login/` retorna `200` sem redirecionar.

Diagnóstico:

1. Verificar se o Cloudflare está configurado com SSL/TLS no modo
   "Full (strict)" ou equivalente.
2. Verificar se o túnel está configurado para servir apenas HTTPS.
3. No proxy reverso (se houver), adicionar redirecionamento HTTP → HTTPS.

## Critérios de Escalonamento

Escalar para desenvolvimento quando:

1. Falha persistir após validação completa deste checklist e correção dos
   itens aplicáveis.
2. Bloqueio de `nir`/`scheduler` no túnel/proxy estiver configurado mas
   ainda houver vazamento de acesso (indicando possível bug de topologia).
3. Papel remoto (`doctor`, `manager`, `admin`) estiver consistentemente
   inacessível externamente com túnel ativo e Django respondendo localmente.
4. Houver evidência de que o bloqueio app-level e a topologia de rede estão
   em conflito (ex.: código espera acesso que a rede nega, ou vice-versa).

Informações obrigatórias no chamado de escalonamento:

- FQDN e ambiente afetado.
- Resultado do checklist de hardening executado (todos os 21 itens).
- Saída dos passos de validação (1 a 5).
- Trecho relevante de logs do túnel (`journalctl -u cloudflared`) e do
  proxy reverso, se aplicável.
- Status dos serviços no host: `docker compose ps` completo.

## Referências

- Topologia oficial de publicação: `docs/publication-topology.md`
- Runbook operacional: `docs/ansible_ops_runbook.md`
- Runbook manual E2E: `docs/manual_e2e_runbook.md`
- Notas de segurança: `docs/security.md`
- Arquitetura: `docs/architecture.md`

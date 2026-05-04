# Zone and Role Hardening Checklist

Language: [Portugues (BR)](../zone-hardening-checklist.md) | **English**

This document complements the official publication topology
(`docs/en/publication-topology.md`) with an operational hardening
checklist by zone and role, deterministic validation steps, and
first-level troubleshooting for access failures.

> **Final supported surface:** Django (`django-ops`, port 8001) is the
> only published human surface. This document does not reintroduce
> operational dependency on legacy human surfaces (FastAPI, Matrix).

## Verification Matrix by Role and Zone

The checklist below must be executed in sequence after every deploy,
upgrade, rollback, or publication configuration change.

### Hardening checklist — internal access (intranet)

| # | Role | Check | Expected | Command |
| --- | --- | --- | --- | --- |
| 1 | `nir` | Internal login | `200` | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/login/` |
| 2 | `nir` | Access `/nir/` route | `200` or `302` (redirects to login if unauthenticated) | validate via authenticated browser at `http://127.0.0.1:8001/nir/` |
| 3 | `doctor` | Internal login | `200` | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/login/` |
| 4 | `doctor` | Access `/doctor/` route | `200` or `302` | validate via authenticated browser at `http://127.0.0.1:8001/doctor/` |
| 5 | `scheduler` | Internal login | `200` | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/login/` |
| 6 | `scheduler` | Access `/scheduler/` route | `200` or `302` | validate via authenticated browser at `http://127.0.0.1:8001/scheduler/` |
| 7 | `manager` | Internal login | `200` | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/login/` |
| 8 | `manager` | Access `/manager/` route | `200` or `302` | validate via authenticated browser at `http://127.0.0.1:8001/manager/` |
| 9 | `admin` | Internal login | `200` | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/login/` |
| 10 | `admin` | Access `/admin/` route | `200` or `302` | validate via authenticated browser at `http://127.0.0.1:8001/admin/` |

### Hardening checklist — external access (Cloudflare Tunnel)

| # | Role | Check | Expected | Command |
| --- | --- | --- | --- | --- |
| 11 | `nir` | Remote access `/nir/` route | **403** or **404** (blocked at tunnel/proxy) | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/nir/ --connect-timeout 10` |
| 12 | `nir` | Remote access `/login/` route | `200` (login reachable, authorization blocks later) | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/login/ --connect-timeout 10` |
| 13 | `doctor` | Remote access `/doctor/` route | `200` (allowed externally) | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/doctor/ --connect-timeout 10` |
| 14 | `scheduler` | Remote access `/scheduler/` route | **403** or **404** (blocked at tunnel/proxy) | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/scheduler/ --connect-timeout 10` |
| 15 | `manager` | Remote access `/manager/` route | `200` (allowed externally) | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/manager/ --connect-timeout 10` |
| 16 | `admin` | Remote access `/admin/` route | `200` (allowed externally) | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/admin/ --connect-timeout 10` |

### Hardening checklist — explicit denial for intranet-only roles

| # | Check | Expected | Command |
| --- | --- | --- | --- |
| 17 | `nir` **denied** on external path | `nir` cannot access any route via external FQDN except `/login/` | verify Cloudflare Tunnel or proxy blocks `/nir/*` |
| 18 | `scheduler` **denied** on external path | `scheduler` cannot access any route via external FQDN except `/login/` | verify Cloudflare Tunnel or proxy blocks `/scheduler/*` |

### Hardening checklist — approved remote access for remote roles

| # | Check | Expected | Command |
| --- | --- | --- | --- |
| 19 | `doctor` approved | `/doctor/*` routes reachable externally via tunnel | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/doctor/ --connect-timeout 10` |
| 20 | `manager` approved | `/manager/*` routes reachable externally via tunnel | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/manager/ --connect-timeout 10` |
| 21 | `admin` approved | `/admin/*` routes reachable externally via tunnel | `curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/admin/ --connect-timeout 10` |

## Validation Steps

The steps below cover deterministic validation of zone hardening.
Execute in order and record results.

### Step 1 — Port and listen address validation on the host

```bash
# Confirm only django-ops (8001) may listen on all interfaces;
# bot-api (8000) and postgres (5432) must listen only on 127.0.0.1.
ss -tlnp | grep -E ':(8000|8001|5432)'
```

Success criteria:

- `8001`: may listen on `0.0.0.0` or `127.0.0.1` based on proxy config.
- `8000` and `5432`: must listen only on `127.0.0.1`.

### Step 2 — Intranet-only denial validation on external path

```bash
# From an external machine (outside the intranet):
FQDN="<your-fqdn>"

# nir — must be denied (403 or 404):
STATUS_NIR=$(curl -s -o /dev/null -w "%{http_code}" "https://${FQDN}/nir/" --connect-timeout 10)
if [ "$STATUS_NIR" = "403" ] || [ "$STATUS_NIR" = "404" ]; then
  echo "PASS: nir blocked externally (HTTP $STATUS_NIR)"
else
  echo "FAIL: nir reachable externally (HTTP $STATUS_NIR)"
fi

# scheduler — must be denied (403 or 404):
STATUS_SCH=$(curl -s -o /dev/null -w "%{http_code}" "https://${FQDN}/scheduler/" --connect-timeout 10)
if [ "$STATUS_SCH" = "403" ] || [ "$STATUS_SCH" = "404" ]; then
  echo "PASS: scheduler blocked externally (HTTP $STATUS_SCH)"
else
  echo "FAIL: scheduler reachable externally (HTTP $STATUS_SCH)"
fi
```

### Step 3 — Approved remote access validation

```bash
# From an external machine:
FQDN="<your-fqdn>"

# doctor — must be allowed:
STATUS_DOC=$(curl -s -o /dev/null -w "%{http_code}" "https://${FQDN}/doctor/" --connect-timeout 10)
if [ "$STATUS_DOC" = "200" ] || [ "$STATUS_DOC" = "302" ]; then
  echo "PASS: doctor accessible externally (HTTP $STATUS_DOC)"
else
  echo "FAIL: doctor unreachable externally (HTTP $STATUS_DOC)"
fi

# manager — must be allowed:
STATUS_MGR=$(curl -s -o /dev/null -w "%{http_code}" "https://${FQDN}/manager/" --connect-timeout 10)
if [ "$STATUS_MGR" = "200" ] || [ "$STATUS_MGR" = "302" ]; then
  echo "PASS: manager accessible externally (HTTP $STATUS_MGR)"
else
  echo "FAIL: manager unreachable externally (HTTP $STATUS_MGR)"
fi

# admin — must be allowed:
STATUS_ADM=$(curl -s -o /dev/null -w "%{http_code}" "https://${FQDN}/admin/" --connect-timeout 10)
if [ "$STATUS_ADM" = "200" ] || [ "$STATUS_ADM" = "302" ]; then
  echo "PASS: admin accessible externally (HTTP $STATUS_ADM)"
else
  echo "FAIL: admin unreachable externally (HTTP $STATUS_ADM)"
fi
```

### Step 4 — HTTPS validation on external path

```bash
# Confirm HTTP without TLS redirects or rejects:
curl -s -o /dev/null -w "%{http_code}" http://<fqdn>/login/ --connect-timeout 10
```

Success criteria: `301` (redirect to HTTPS) or connection refused.

### Step 5 — Coherence validation between topology and app-level rules

```bash
# Internally, authenticate as nir and access /nir/ — expected 200
# Externally, if tunnel does not fully block, authenticate as nir
# and access /nir/ — expected 403 (app-level block)
```

Success criteria:

- `nir` authenticated internally: access to `/nir/*` returns `200`.
- `nir` authenticated externally (if tunnel does not block): access to `/nir/*` returns `403` (app-level).
- Same for `scheduler` and `/scheduler/*`.

## Troubleshooting

The troubleshooting below covers first-level failures. When the root cause
cannot be identified or the fix does not resolve the issue, follow the
escalation criteria.

### Symptom 1 — Externally allowed role cannot access remote route

**Example:** `doctor`, `manager`, or `admin` receive an error when accessing
a route via external FQDN.

Diagnosis:

1. Check Cloudflare Tunnel status:

   ```bash
   # On the host, confirm the tunnel is active and pointing to 127.0.0.1:8001
   cloudflared tunnel info <tunnel-name>
   ```

2. Confirm `django-ops` is responding locally:

   ```bash
   curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/login/
   # Expected: 200
   ```

3. Check DNS configuration — confirm FQDN resolves to the tunnel:

   ```bash
   dig +short <fqdn>
   # Should return Cloudflare IPs (not the host's direct IP)
   ```

4. Verify reverse proxy (if present) is not blocking the route:

   ```bash
   # Test local direct access to Django, bypassing the proxy:
   curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/doctor/
   # Expected: 200 or 302
   ```

5. If Django responds locally but tunnel does not deliver, review logs:

   ```bash
   journalctl -u cloudflared --since "10 min ago" --no-pager | tail -30
   ```

### Symptom 2 — Intranet-only role is reachable externally

**Example:** `nir` or `scheduler` can access routes via external FQDN
(returning `200` instead of `403` or `404`).

Diagnosis:

1. Verify Cloudflare Tunnel or reverse proxy is correctly filtering
   intranet-only routes (`/nir/*`, `/scheduler/*`):

   ```bash
   # Test each externally blocked route:
   curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/nir/ --connect-timeout 10
   curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/scheduler/ --connect-timeout 10
   # Expected: 403 or 404
   ```

2. If the tunnel delivers the routes, blocking must be configured in the
   reverse proxy (Nginx/Caddy) or in Cloudflare Tunnel itself:

   - **Nginx:** add `deny all;` for `location /nir/` and `location /scheduler/`
     in the external server block.
   - **Caddy:** use `respond` directive with status 403 for those routes.
   - **Cloudflare Tunnel:** configure access rules in the dashboard to
     block paths `/nir/*` and `/scheduler/*`.

3. Confirm app-level blocking is active as an additional layer:

   ```bash
   # Authenticate as nir externally and verify application returns 403:
   curl -s -o /dev/null -w "%{http_code}" \
     -H "Cookie: sessionid=<nir-session-token>" \
     https://<fqdn>/nir/ --connect-timeout 10
   # Expected: 403 (app-level block)
   ```

### Symptom 3 — Backend port responds externally

**Example:** `bot-api` (8000) or `postgres` (5432) respond from an external
machine.

Diagnosis:

1. On the host, check port listening:

   ```bash
   ss -tlnp | grep -E ':(8000|5432)'
   # Expected: LISTEN only on 127.0.0.1 (loopback)
   ```

2. If any port is listening on `0.0.0.0` or `*`, review Docker Compose
   configuration (`ports` vs `expose`) and correct to expose only on loopback.

3. Check host firewall rules:

   ```bash
   sudo ufw status verbose
   # Expected: only tunnel/proxy ports authorized externally
   ```

### Symptom 4 — HTTPS not active on external path

**Example:** `curl http://<fqdn>/login/` returns `200` without redirecting.

Diagnosis:

1. Verify Cloudflare is configured with SSL/TLS in "Full (strict)" mode
   or equivalent.
2. Verify the tunnel is configured to serve only HTTPS.
3. In the reverse proxy (if present), add HTTP → HTTPS redirection.

## Escalation Criteria

Escalate to development when:

1. Failure persists after full validation of this checklist and correction
   of applicable items.
2. `nir`/`scheduler` blocking is configured at tunnel/proxy but access still
   leaks (indicating a possible topology bug).
3. Remote role (`doctor`, `manager`, `admin`) is consistently unreachable
   externally with an active tunnel and Django responding locally.
4. There is evidence that app-level blocking and network topology are in
   conflict (e.g., code expects access the network denies, or vice versa).

Required information in the escalation ticket:

- FQDN and affected environment.
- Results of the hardening checklist executed (all 21 items).
- Validation step outputs (1 through 5).
- Relevant tunnel log excerpt (`journalctl -u cloudflared`) and reverse
  proxy logs, if applicable.
- Full service status on the host: `docker compose ps`.

## References

- Official publication topology: `docs/en/publication-topology.md`
- Operational runbook: `docs/en/ansible_ops_runbook.md`
- Manual E2E runbook: `docs/en/manual_e2e_runbook.md`
- Security notes: `docs/en/security.md`
- Architecture: `docs/en/architecture.md`

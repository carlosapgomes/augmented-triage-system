# Publication Topology

Language: [Portugues (BR)](../publication-topology.md) | **English**

This document defines the official ATS publication topology for a
single-host deployment, objectively separating internal (intranet)
and external (Cloudflare Tunnel) access paths.

> **Final supported surface:** Django (`django-ops`, port 8001) is the
> only published human and administrative surface. FastAPI (`bot-api`) and
> Matrix (`bot-matrix`) are backend runtime components and must not be
> exposed externally through any supported publication path.

## Overview

The entire consolidated stack runs on the same host with rootless Docker:

| Service | Port | Exposure |
| --- | --- | --- |
| `postgres` | 5432 | loopback only (never exposed) |
| `bot-api` | 8000 | loopback only (backend runtime) |
| `bot-matrix` | — | loopback only (outbound Matrix connection) |
| `worker` | — | loopback only (internal queue consumer) |
| `django-ops` | 8001 | loopback + controlled external tunnel |

## Access Paths

### Internal Access (Intranet)

Internal access is via `django-ops` at `http://127.0.0.1:8001` directly,
or through a controlled internal reverse proxy (Nginx/Caddy) forwarding
to `127.0.0.1:8001`.

All operational roles have access through the internal path:

- `nir`
- `doctor`
- `scheduler`
- `manager`
- `admin`

### External Access (Cloudflare Tunnel)

The only supported remote access path is the **Cloudflare Tunnel** pointing
to `http://127.0.0.1:8001` (Django).

Only the following roles have access through the external path:

- `doctor` — remote access allowed
- `manager` — remote access allowed
- `admin` — remote access allowed

The `nir` and `scheduler` roles are **blocked on the external path** — the
tunnel or external proxy MUST NOT forward requests for these roles. This
restriction operates at the publication/network layer and is additional to
the existing app-level blocking.

```text
[Internet]
    │
    ▼
[Cloudflare Tunnel] ─── public FQDN (HTTPS mandatory)
    │
    ▼ (nir/scheduler blocked at tunnel level)
[127.0.0.1:8001] django-ops
    │
    ├── /login/
    ├── /nir/*       ← blocked on external path
    ├── /doctor/*    ← allowed externally
    ├── /scheduler/* ← blocked on external path
    ├── /manager/*   ← allowed externally
    └── /admin/*     ← allowed externally
```

## Access Matrix by Role and Zone

| Role | Internal Access | External Access (Tunnel) |
| --- | --- | --- |
| `nir` | ✓ `http://127.0.0.1:8001` | ✗ Blocked at tunnel/proxy |
| `doctor` | ✓ `http://127.0.0.1:8001` | ✓ Via Cloudflare Tunnel |
| `scheduler` | ✓ `http://127.0.0.1:8001` | ✗ Blocked at tunnel/proxy |
| `manager` | ✓ `http://127.0.0.1:8001` | ✓ Via Cloudflare Tunnel |
| `admin` | ✓ `http://127.0.0.1:8001` | ✓ Via Cloudflare Tunnel |

## Validation Criteria

The criteria below are objective and must be verified after every deploy
or topology change.

### 1. Backend services never exposed externally

None of the services below may be reachable from the external network:

- `bot-api` (port 8000)
- `postgres` (port 5432)
- `bot-matrix` and `worker` (no exposed ports)

Validation:

```bash
# From an external machine, confirm ports are unreachable:
curl -s --connect-timeout 5 http://<remote-host>:8000/ && echo "FAIL: bot-api exposed" || echo "OK: bot-api unreachable"
curl -s --connect-timeout 5 http://<remote-host>:5432/ && echo "FAIL: postgres exposed" || echo "OK: postgres unreachable"
```

On the host:

```bash
# Confirm only django-ops (8001) may listen on all interfaces when applicable:
ss -tlnp | grep -E ':(8000|8001|5432)'
# Expected: 8001 may listen on 0.0.0.0 or 127.0.0.1 based on proxy config;
# 8000 and 5432 must listen only on 127.0.0.1
```

### 2. External access restricted to remote roles

Validation from a machine outside the intranet, using the public FQDN:

```bash
# doctor — access expected (login should be possible):
curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/login/ --connect-timeout 10
# Expected: 200

# nir — access NOT expected (must be blocked at tunnel/proxy):
curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/nir/ --connect-timeout 10
# Expected: 403 or 404 (route must not be reachable externally)

# scheduler — access NOT expected:
curl -s -o /dev/null -w "%{http_code}" https://<fqdn>/scheduler/ --connect-timeout 10
# Expected: 403 or 404
```

### 3. Coherence between topology and app-level rules

After validating network criteria, confirm that application authorization
rules are also active:

- `nir` authenticated internally: access to `/nir/*` — `200`
- `nir` authenticated externally (if tunnel does not block): access to `/nir/*` — `403` (app-level)
- `scheduler` authenticated internally: access to `/scheduler/*` — `200`
- `scheduler` authenticated externally (if tunnel does not block): access to `/scheduler/*` — `403` (app-level)

### 4. HTTPS on the external path

```bash
# Confirm HTTP without TLS redirects or rejects:
curl -s -o /dev/null -w "%{http_code}" http://<fqdn>/login/ --connect-timeout 10
# Expected: 301 (redirect to HTTPS) or connection refused
```

## Topology Decisions

1. **Single-host as baseline**: the entire consolidated stack runs on the same
   host, without load balancing or HA in this cycle.

2. **Publication by topology, not just UI**: segregation between intranet-only
   and remote roles occurs at the network/publication layer (tunnel/proxy),
   before the application. App-level blocking is an additional layer, not a
   substitute.

3. **Cloudflare Tunnel as the only remote path**: there is no support for
   corporate VPN, SSH tunneling, or port forwarding as alternative remote
   access paths in this topology.

4. **Authentication only at the application**: the Cloudflare Tunnel does not
   apply additional authentication (Cloudflare Access). All authentication and
   authorization is managed by Django.

5. **Legacy surfaces out of scope**: FastAPI (`bot-api`) and Matrix
   (`bot-matrix`) are not publication surfaces. Their HTTP/HTTPS routes are
   exclusively for internal backend component communication.

## Conscious Limitations

- No support for multiple hosts or HA topologies.
- No tunnel-level authentication (Cloudflare Access) — authentication is
  exclusively app-level.
- The internal path does not require a reverse proxy (direct access to
  `127.0.0.1:8001` is supported), but a controlled internal proxy is
  recommended in near-production environments.
- Detailed publication failure troubleshooting is documented in the
  operational runbook (`docs/en/ansible_ops_runbook.md`), not in this
  topology document.
- The zone and role hardening checklist is at
  `docs/en/zone-hardening-checklist.md`.

## References

- Zone hardening checklist: `docs/en/zone-hardening-checklist.md`
- Operational runbook: `docs/en/ansible_ops_runbook.md`
- Manual E2E runbook: `docs/en/manual_e2e_runbook.md`
- Setup guide: `docs/en/setup.md`
- Architecture: `docs/en/architecture.md`

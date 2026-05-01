# Slice 3.2 - Intranet role restrictions

## Goal

Aplicar restrição app-level para `nir` e `scheduler`, limitada à intranet, com evidência auditável de negação.

## Context

A resolução confiável do client IP já existe. Agora o app deve negar `nir` e `scheduler` fora da CIDR autorizada, mesmo com credenciais válidas.

## Scope boundaries

**Included:** guard/middleware de zona, regra por papel, auditoria/log de negação, testes HTTP.

**Excluded:** mudanças de proxy/firewall externo, PWA, fluxos funcionais NIR/Doctor/Scheduler.

## Tests to write FIRST (TDD)

- `nir` dentro da intranet é autorizado;
- `nir` fora da intranet é negado;
- `scheduler` fora da intranet é negado;
- `doctor`, `manager` e `admin` continuam acessíveis fora da intranet;
- negações deixam evidência auditável.

## Success criteria

- a restrição por papel e zona funciona no app;
- credenciais válidas não burlam a política;
- acessos negados ficam rastreáveis.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: django-web-foundation-and-access-zones
Task file: openspec/changes/django-web-foundation-and-access-zones/tasks/05-intranet-role-restrictions.md
Implement only this slice.
Use strict TDD.
Do not modify network/firewall automation in this slice; stay at app level.
Preserve remote access for doctor/manager/admin.
Run gates, update checklist, commit, push, and stop.
Include SNP before/after in the report.
```

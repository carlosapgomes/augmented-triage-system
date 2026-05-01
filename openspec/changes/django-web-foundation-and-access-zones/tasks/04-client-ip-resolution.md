# Slice 3.1 - Client IP resolution

## Goal

Implementar resolução confiável do IP de origem considerando proxies confiáveis e rejeitando forwarding não confiável.

## Context

A política de intranet para `nir` e `scheduler` depende de um client IP resolvido corretamente atrás de proxy/túnel. Este slice prepara apenas essa fundação técnica.

## Scope boundaries

**Included:** utilitário/serviço/middleware de resolução de IP, configuração de trusted proxies, testes positivos e negativos.

**Excluded:** bloqueio por papel, auditoria de negação, login, PWA.

## Tests to write FIRST (TDD)

- request direta usa IP remoto real;
- request via proxy confiável usa forwarded client IP aceito;
- forwarding vindo de origem não confiável é ignorado.

## Success criteria

- existe resolução determinística de client IP;
- headers não confiáveis não influenciam autorização futura.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: django-web-foundation-and-access-zones
Task file: openspec/changes/django-web-foundation-and-access-zones/tasks/04-client-ip-resolution.md
Implement only this slice.
Use TDD.
Do not enforce role restrictions yet; only resolve origin IP safely.
Keep the design reusable by later access-control slices.
Run gates, commit, push, and stop.
Report SNP before/after.
```

# Slice 3.2 - Admin prompt management consolidation

## Goal

Consolidar a superfície de gestão de prompts no Django para `admin`.

## Context

A gestão de usuários já está consolidada. Agora a gestão de prompts precisa seguir a mesma estratégia, permanecendo exclusiva de `admin`.

Neste slice, a referência FastAPI/SQLAlchemy anterior deve ser tratada como legado de comportamento e auditoria, não como estrutura técnica obrigatória. A implementação consolidada deve priorizar a solução final em Django.

## Scope boundaries

**Included:** página/rotas Django de prompts, autorização `admin`, negativas para `manager`, preservação das regras existentes de autorização/auditoria com implementação consolidada em Django.

**Excluded:** novas políticas de prompt fora do escopo atual.

## Tests to write FIRST (TDD)

- [x] `admin` acessa e muta prompts na superfície Django consolidada;
- [x] `manager` é negado;
- [x] auditoria de prompt continua preservada;
- [x] a solução não depende de compatibilidade estrutural com a superfície legada.

## Success criteria

- [x] gestão de prompts está consolidada no Django;
- [x] paridade de autorização foi preservada;
- [x] a implementação final não fica acoplada estruturalmente à superfície administrativa legada.

## Implementation notes

### Initial implementation (v1)

- Created `DjangoPromptManagementService` in `apps/django_ops/django_prompt_management.py`
  (later corrected — see v2 below).
- Replaced placeholder view with 4 real views: listing, version detail, activate, create.
- 18 integration tests passing (TDD), no regressions in Django surface.

### Architecture correction (v2)

- Removed business logic from the adapter layer (`apps/django_ops/`).
- Created `DjangoPromptStorePort` in `src/triage_automation/application/ports/` — clean protocol
  for prompt-template persistence operations without exposing storage concerns.
- Moved `DjangoPromptManagementService` to `src/triage_automation/application/services/` —
  contains pure business logic (activation CAS, version derivation, audit) with no SQLAlchemy
  or Django imports.
- Created `DjangoOrmPromptStoreAdapter` in `apps/django_ops/` — thin adapter implementing
  `DjangoPromptStorePort` against the shared `prompt_templates` table via SQLAlchemy.
- `DjangoPromptActor` DTO used for actor identity (same pattern as `DjangoActor` in
  `DjangoUserManagementService`).
- Audit events written with `user_id=NULL` and Django actor identity in payload.
- Views remain thin — only role checks, parameter parsing, and service delegation.

### Persistence investigation (v3)

Investigated replacing SQLAlchemy writes in the adapter with Django-native persistence
(Django ORM model with `managed=False` + shared database router).  This path is blocked
by a systemic issue:

- The `prompt_templates` table is managed by Alembic on a database separate from Django's
  default SQLite.  Django's test runner creates and manages test databases independently,
  and integrating Alembic-managed schemas into Django's test DB lifecycle requires fragile
  coordination (`DiscoverRunner` vs `command.upgrade()`) not justified for this slice.

The SQLAlchemy session factory is already shared across all runtime components (audit,
cases, jobs, prompts).  Using it in this adapter is the smallest clean boundary that
preserves the approved business rules without duplicating schema management.

What IS Django-native in this final design:
- The port lives in the application layer with no framework imports.
- The application service enforces business rules and audit semantics with no infrastructure imports.
- The adapter is thin — it only translates between port contracts and the shared repository.
- Audit events use the Django actor-identity pattern (user_id=NULL, actor info in payload)
  established by `DjangoUserManagementService`.

## Mandatory report file

- Write the implementation report to: `/tmp/admin-manager-web-consolidation-05-admin-prompt-management-consolidation-report.md`
- In the final response, include the exact file path above so the user can copy it.

## Mandatory implementation prompt

```text
Use the openspec-apply-change skill.
Change ID: admin-manager-web-consolidation
Task file: openspec/changes/admin-manager-web-consolidation/tasks/05-admin-prompt-management-consolidation.md
Implement only this slice.
Use strict TDD.
Preserve the approved prompt-management rules, authorization intent, and audit semantics.
Implement the consolidated surface natively in Django unless the slice requires an explicit shared-runtime integration.
Do not force structural compatibility with the legacy FastAPI/SQLAlchemy admin surface.
Run gates, update checklist, commit, push, and stop.
Include SNP before/after.
```

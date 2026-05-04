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

- Created `DjangoPromptManagementService` in `apps/django_ops/django_prompt_management.py` — Django-native service that uses shared `PromptManagementRepositoryPort` for reads and direct SQLAlchemy session access for writes (bypassing UUID `updated_by_user_id` FK constraint from legacy users table).
- Audit events written with `user_id=NULL` and Django actor identity in payload, following same pattern as `DjangoUserManagementService`.
- Replaced placeholder view with 4 real views: listing, version detail, activate, create.
- 18 integration tests passing (TDD), no regressions in Django surface.

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

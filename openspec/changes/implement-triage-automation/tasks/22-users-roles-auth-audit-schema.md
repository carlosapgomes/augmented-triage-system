# Slice 22 - Users, Roles, and Auth Events Schema and Repositories

## Goal
Add `users` and `auth_events` schema plus repositories for user retrieval and auth auditing.

## Scope boundaries
Included: migrations, metadata, repository ports/adapters.
Excluded: password hashing and login endpoint behavior.

## Files to create/modify
- `alembic/versions/0003_users_auth_events.py`
- `src/triage_automation/infrastructure/db/metadata.py`
- `src/triage_automation/domain/auth/roles.py`
- `src/triage_automation/application/ports/user_repository_port.py`
- `src/triage_automation/application/ports/auth_event_repository_port.py`
- `src/triage_automation/infrastructure/db/user_repository.py`
- `src/triage_automation/infrastructure/db/auth_event_repository.py`
- `tests/integration/test_migration_users_auth_events.py`
- `tests/integration/test_user_and_auth_event_repositories.py`

## Tests to write FIRST (TDD)
- `users` schema has role check constraint and unique email.
- `auth_events` schema and indexes exist.
- Role enum values are exactly `admin` and `reader`.
- Repositories fetch active user by email and append auth events.

## Implementation steps
1. Add migration for `users` and `auth_events`.
2. Add domain role enum.
3. Add repository interfaces and DB adapters.

## Refactor steps
- Reuse shared timestamp and UUID helper patterns.

## Verification commands
- `uv run pytest tests/integration/test_migration_users_auth_events.py -q`
- `uv run pytest tests/integration/test_user_and_auth_event_repositories.py -q`
- `uv run ruff check .`
- `uv run mypy src apps`

## Mandatory checklist
- [ ] spec section referenced
- [ ] failing tests written
- [ ] edge cases included
- [ ] minimal implementation
- [ ] tests pass
- [ ] lint passes
- [ ] type checks pass
- [ ] no triage workflow behavior change

## STOP RULE
- [ ] stop here and do not start next slice

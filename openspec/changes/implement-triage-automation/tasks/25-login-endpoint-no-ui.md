# Slice 25 - Minimal Login Endpoint (No UI)

## Goal
Expose one backend login endpoint for auth foundation with role-bearing identity response/token, no UI.

## Scope boundaries
Included: one login route, auth service integration, auth event audit, response contract.
Excluded: any UI, user management endpoints, prompt editing endpoints.

## Files to create/modify
- `apps/bot_api/main.py`
- `src/triage_automation/application/dto/auth_models.py`
- `src/triage_automation/infrastructure/http/auth_router.py`
- `tests/integration/test_login_endpoint.py`

## Tests to write FIRST (TDD)
- Valid credentials return success payload including role.
- Invalid credentials return auth error.
- Inactive user returns forbidden/inactive response.
- Login writes corresponding `auth_events` entry.
- Route count unchanged except login route addition.

## Implementation steps
1. Add request/response DTOs.
2. Add login route calling auth service.
3. Return minimal auth response for future UI integration.

## Refactor steps
- Keep route thin; move all decision logic to service.

## Verification commands
- `uv run pytest tests/integration/test_login_endpoint.py -q`
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

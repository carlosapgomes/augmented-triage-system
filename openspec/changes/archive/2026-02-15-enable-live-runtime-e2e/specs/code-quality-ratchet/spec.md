## MODIFIED Requirements

### Requirement: Regression Prevention
The project SHALL prevent quality regressions in completed ratcheted areas through mandatory quality gates.

#### Scenario: Change touches completed ratcheted area
- **WHEN** a contributor runs validation for a slice or pull request
- **THEN** `ruff check` and `mypy` MUST enforce the configured ratchet rules for already-completed scopes

#### Scenario: Runtime-readiness slice touches production modules
- **WHEN** runtime-readiness work modifies production entrypoints or infrastructure adapters
- **THEN** public docstring and typed-signature requirements in ratcheted scopes MUST remain enforced by the active quality gates

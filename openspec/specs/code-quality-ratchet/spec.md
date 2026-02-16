# code-quality-ratchet Specification

## Purpose
TBD - created by archiving change progressive-docstring-type-hardening. Update Purpose after archive.
## Requirements
### Requirement: Progressive Enforcement Plan
The project SHALL enforce docstring and type-quality rules through a progressive ratchet plan rather than a single global strictness switch.

#### Scenario: Ratchet plan is defined before implementation
- **WHEN** contributors start the quality-hardening change
- **THEN** they MUST have an ordered set of incremental slices with explicit scope per slice

### Requirement: Public Surface Docstring Coverage
The project SHALL require docstrings for public modules, classes, and functions in packages that have been ratcheted.

#### Scenario: Public API introduced in ratcheted package
- **WHEN** a new public class or function is added under a ratcheted package
- **THEN** linting MUST fail if required docstrings are missing

### Requirement: Typed Public Interfaces
The project SHALL require explicit type annotations for public function signatures in packages that have been ratcheted.

#### Scenario: Untyped public function in ratcheted package
- **WHEN** a public function without type annotations is introduced or modified in a ratcheted package
- **THEN** type/lint checks MUST fail until annotations are added

### Requirement: Regression Prevention
The project SHALL prevent quality regressions in completed ratcheted areas through mandatory quality gates.

#### Scenario: Change touches completed ratcheted area
- **WHEN** a contributor runs validation for a slice or pull request
- **THEN** `ruff check` and `mypy` MUST enforce the configured ratchet rules for already-completed scopes

#### Scenario: Runtime-readiness slice touches production modules
- **WHEN** runtime-readiness work modifies production entrypoints or infrastructure adapters
- **THEN** public docstring and typed-signature requirements in ratcheted scopes MUST remain enforced by the active quality gates

### Requirement: Slice-Level Verification
Each hardening slice SHALL include deterministic verification commands and a completion checklist.

#### Scenario: Slice marked complete
- **WHEN** a slice is completed
- **THEN** its scoped tests, lint checks, and type checks MUST pass before commit

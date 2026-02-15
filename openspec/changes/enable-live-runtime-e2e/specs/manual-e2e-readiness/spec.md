## ADDED Requirements

### Requirement: Deterministic Manual Runtime Validation
The project SHALL define deterministic smoke checks for validating live runtime readiness before full manual end-to-end testing.

#### Scenario: Pre-E2E smoke execution
- **WHEN** operators prepare for manual end-to-end testing
- **THEN** they MUST be able to verify service startup, database readiness, and webhook endpoint reachability with documented deterministic checks

### Requirement: Cloudflare Tunnel Webhook Validation Path
The project SHALL provide an explicit validation path for tunneled webhook callbacks using existing HMAC authentication behavior.

#### Scenario: Tunneling webhook traffic
- **WHEN** operators expose `bot-api` via Cloudflare tunnel for callback testing
- **THEN** they MUST be able to send a signed callback request that reaches `/callbacks/triage-decision` and follows existing callback validation rules

### Requirement: Configurable External Dependency Test Modes
Runtime execution SHALL support explicit configuration modes that enable deterministic manual validation when external providers are unavailable.

#### Scenario: LLM provider unavailable in manual testing
- **WHEN** deterministic runtime mode is enabled for manual validation
- **THEN** LLM-dependent workflow steps MUST remain executable via configured deterministic adapters without altering triage business semantics

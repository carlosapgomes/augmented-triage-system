# Delta Spec: room2-structured-reply-decision

## MODIFIED Requirements

### Requirement: Room-2 SHALL Publish Three-Message Decision Combo

The system SHALL publish a deterministic three-message combo in Room-2 for each case requiring doctor decision. Message II MUST use concise clinical-opinion formatting for physician reading speed while preserving strict coherence between displayed decision fields and objective reason text.

#### Scenario: Case enters Room-2 doctor decision stage

- **WHEN** a case is ready for doctor decision in Room-2
- **THEN** the bot MUST post message I with the original PDF report
- **AND** the bot MUST post message II with concise clinical summary and recommendation blocks, including at least: `Resumo clínico`, `Achados críticos`, `Pendências críticas`, `Decisão sugerida`, `Suporte recomendado`, and `Motivo objetivo`
- **AND** message II MUST NOT include `Conduta sugerida` as a standalone section
- **AND** `Motivo objetivo` MUST be coherent with the final displayed `Decisão sugerida`
- **AND** when `Decisão sugerida` is `negar`, `Motivo objetivo` MUST report objective denial causes and MUST NOT contain acceptance or support phrasing
- **AND** when `Decisão sugerida` is `aceitar`, `Motivo objetivo` MUST be a short acceptance phrase with support context only
- **AND** message II MUST avoid full flattened dump of complete LLM1/LLM2 structured payloads
- **AND** the bot MUST post message III with strict reply template and instructions to reply to message I

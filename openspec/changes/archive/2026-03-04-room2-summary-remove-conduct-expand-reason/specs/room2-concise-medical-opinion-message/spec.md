# Specification Delta

## MODIFIED Requirements

### Requirement: Room-2 Clinical Opinion Message SHALL Be Concise And Decision-Oriented

The system SHALL publish a concise medical-opinion summary in Room-2 focused on clinical context and decision support, without dumping full flattened structured payloads and without adding standalone conduct guidance.

#### Scenario: Room-2 summary is generated for doctor review

- **WHEN** message II (`room2_case_summary`) is rendered for a case awaiting doctor decision
- **THEN** the message MUST prioritize concise, decision-oriented content
- **AND** the message MUST NOT include full flattened listings equivalent to complete LLM1/LLM2 structured payloads
- **AND** the message MUST NOT include a standalone `Conduta sugerida` section

### Requirement: Room-2 Summary SHALL Include Mandatory Seven-Block Layout

The system SHALL render the Room-2 summary with a fixed six-block layout to standardize medical reading flow.

#### Scenario: Summary message is posted in Room-2

- **WHEN** the bot posts message II for a case in Room-2
- **THEN** the message MUST include the following blocks in order:
- **AND** `Resumo clínico`
- **AND** `Achados críticos`
- **AND** `Pendências críticas`
- **AND** `Decisão sugerida`
- **AND** `Suporte recomendado`
- **AND** `Motivo objetivo`

### Requirement: Decision, Support, And Objective Reason SHALL Be Explicit And Coherent

The message SHALL explicitly show final reconciled suggestion fields and an objective reason aligned with that final suggestion, with less aggressive truncation than the previous concise format.

#### Scenario: Suggested action is reconciled before Room-2 post

- **WHEN** `suggested_action_json` is already policy-reconciled and consumed for summary rendering
- **THEN** `Decisão sugerida` MUST reflect the final reconciled suggestion value
- **AND** `Suporte recomendado` MUST reflect the final reconciled support value
- **AND** `Motivo objetivo` MUST remain coherent with displayed decision and support
- **AND** if rationale text is present and its normalized size is up to 360 characters, the full rationale sentence MUST be included without truncation
- **AND** if rationale text exceeds 360 normalized characters, truncation MAY occur only at the end of the reason text

### Requirement: Emergent Instability Cases SHALL Include Priority Phrase

The summary SHALL include explicit emergent-priority language for bleeding cases with documented hemodynamic instability.

#### Scenario: Bleeding plus hemodynamic instability is present

- **WHEN** case context indicates active bleeding with documented hemodynamic instability
- **THEN** `Motivo objetivo` MUST include explicit emergent-priority phrasing
- **AND** this phrasing MUST indicate that stabilization and urgent pathway should not be delayed by non-critical missing fields

## REMOVED Requirements

### Requirement: Conduta Sugerida SHALL Be Bounded And Actionable

**Reason**: O posicionamento do bot na Sala 2 passa a ser estritamente de recomendação de decisão (`aceitar`/`negar`) com justificativa objetiva, sem prescrição adicional de conduta.

**Migration**: Qualquer consumidor que validava `Conduta sugerida` na mensagem II MUST migrar para validação dos blocos `Decisão sugerida`, `Suporte recomendado` e `Motivo objetivo` como fonte primária de recomendação textual.

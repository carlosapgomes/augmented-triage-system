# room2-structured-reply-decision delta

## MODIFIED Requirements

### Requirement: Decision Replies SHALL Be Strictly Structured

The system SHALL accept only strict structured decision replies and SHALL NOT
infer decisions from free-form text. For accepted decisions, the structured
contract SHALL include explicit admission-flow selection in addition to
decision, support, and case identity. For denied decisions, the parser SHALL
remain strict for unknown fields while treating `suporte` and
`fluxo de admissão` as optional or semantically ignored. The parser SHALL also
ignore known bot-authored helper/context lines that are outside the decision
contract and may appear in copy/pasted replies.

#### Scenario: Doctor submits accepted decision with scheduled admission

- **WHEN** a doctor reply contains a syntactically valid accepted-decision
  template with `decisao=aceitar`, `fluxo de admissão=agendamento`, valid
  `suporte`, and `caso`
- **THEN** the system MUST parse structured fields deterministically
- **AND** the parsed result MUST normalize the admission flow to the canonical
  scheduled value used by the workflow

#### Scenario: Doctor submits accepted decision with immediate-admission alias

- **WHEN** a doctor reply contains `decisao=aceitar` and the admission-flow
  line uses `fluxo de admissão`, `fluxo de admissao`, or `fluxo_admissao` with
  value `vinda_imediata` or `vinda imediata`
- **THEN** the system MUST accept the reply as syntactically valid
- **AND** the parsed result MUST normalize the admission flow to the canonical
  internal value for immediate admission

#### Scenario: Doctor submits denied decision without support or admission-flow line

- **WHEN** a doctor reply contains `decisao=negar` and `caso`, with or without
  `suporte`, `fluxo de admissão`, and `motivo`
- **THEN** the system MUST accept the reply if all provided fields are known
  and structurally valid
- **AND** the parsed result MUST normalize denied decisions so support
  semantics remain equivalent to `none`
- **AND** any provided admission-flow value MUST be ignored semantically for
  the denied decision path

#### Scenario: Doctor copies the bot template with identification context

- **WHEN** a doctor reply includes the bot-authored helper lines `no.
  ocorrência` and `paciente` together with an otherwise valid structured
  decision reply
- **THEN** the system MUST ignore those helper lines during parsing
- **AND** the decision MUST be validated only against the supported structured
  decision fields

#### Scenario: Doctor copies the validation prompt heading with the template

- **WHEN** a doctor reply includes the helper heading `Modelo obrigatório`
  together with an otherwise valid structured decision reply
- **THEN** the system MUST ignore that helper heading during parsing
- **AND** the reply MUST remain subject to strict validation for all other
  labeled fields

#### Scenario: Doctor submits unknown structured field

- **WHEN** a doctor reply includes any field outside the allowed strict
  contract
- **THEN** the system MUST reject the submission with explicit feedback
- **AND** no decision mutation or job enqueue MUST occur

# room2-structured-reply-decision Specification

## Purpose

Define the strict Matrix structured-reply contract used for Room-2 medical
 decisions, including doctor-facing message composition, validation rules, and
 feedback semantics.

## Requirements

### Requirement: Room-2 SHALL Publish Three-Message Decision Combo

The system SHALL publish a deterministic three-message combo in Room-2 for each
case requiring doctor decision, adding human-readable identification context to
 doctor-facing text messages and exposing the full structured reply contract
used by the physician.

#### Scenario: Case enters Room-2 doctor decision stage

- **WHEN** a case is ready for doctor decision in Room-2
- **THEN** the bot MUST post message I with the original PDF report
- **AND** the bot MUST post message II with extracted data + summary +
  recommendation, including `no. ocorrência` and `paciente` near the top
- **AND** the bot MUST post message III with strict reply template and
  instructions to reply to message I, including `no. ocorrência` and
  `paciente`
- **AND** message III MUST expose the accepted-decision template with explicit
  `fluxo de admissão: agendamento` default
- **AND** message III MUST keep the `caso: <uuid>` line required by parser
  validation

### Requirement: Room-2 Combo SHALL Be Grouped By Flat Reply Relations

The bot SHALL preserve case context grouping by posting messages II and III as
replies to message I, without deep nested reply chains.

#### Scenario: Bot posts message combo for a case

- **WHEN** messages I, II, and III are published for a Room-2 case
- **THEN** messages II and III MUST include reply relation metadata targeting
  message I
- **AND** message III MUST NOT rely on reply-of-reply nesting for required
  context

### Requirement: Decision Replies SHALL Be Strictly Structured

The system SHALL accept only strict structured decision replies and SHALL NOT
infer decisions from free-form text. For accepted decisions, the structured
contract SHALL include explicit admission-flow selection in addition to
decision, support, and case identity. For denied decisions, the parser SHALL
remain strict for unknown fields while treating `suporte` and
`fluxo de admissão` as optional or semantically ignored.

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

#### Scenario: Doctor submits unknown structured field

- **WHEN** a doctor reply includes any field outside the allowed strict
  contract
- **THEN** the system MUST reject the submission with explicit feedback
- **AND** no decision mutation or job enqueue MUST occur

### Requirement: Decision Reply SHALL Reference Active Room-2 Root Case Message

A decision reply SHALL be accepted only when it is a Matrix reply to the active
Room-2 root case message (message I).

#### Scenario: Reply targets active case message

- **WHEN** the decision event is a valid `m.in_reply_to` reply to the active
  Room-2 root case message
- **THEN** the system MUST treat the reply as eligible for decision parsing and
  validation

#### Scenario: Reply targets wrong or missing parent

- **WHEN** the decision event is not a reply to the active Room-2 root case
  message
- **THEN** the system MUST reject the submission
- **AND** no decision mutation or job enqueue MUST occur

### Requirement: Doctor Identity SHALL Be Derived From Matrix Sender

The system SHALL derive `doctor_user_id` from Matrix event sender identity, not
from user-entered fields.

#### Scenario: Structured reply is accepted

- **WHEN** a valid decision reply is processed
- **THEN** `doctor_user_id` MUST be set from the Matrix sender on the reply
  event
- **AND** any user-entered identity value MUST be ignored or rejected

### Requirement: Room-2 Membership SHALL Be Authorization Boundary

Only users who are able to post in Room-2 SHALL be authorized to submit doctor
decisions through this path.

#### Scenario: Room-2 member submits decision

- **WHEN** a Room-2 member submits a valid structured reply
- **THEN** the system MUST authorize and process the decision subject to state
  validation

#### Scenario: Non-authorized actor cannot submit decision

- **WHEN** a decision-like event is produced by an actor not authorized by
  Room-2 membership policy
- **THEN** the system MUST reject processing
- **AND** no decision mutation or job enqueue MUST occur

### Requirement: Structured Reply Path SHALL Preserve Existing Decision Semantics

The structured reply path SHALL preserve existing state-machine gating,
idempotency, and downstream deny behavior while extending positive decisions to
branch deterministically by the normalized admission-flow value.

#### Scenario: ACCEPT decision is applied with scheduled flow

- **WHEN** a valid structured reply submits `decision=accept` with normalized
  scheduled admission flow
- **THEN** the case MUST follow the existing accepted-state transition behavior
  used before this change
- **AND** the same downstream scheduling job path MUST be enqueued

#### Scenario: ACCEPT decision is applied with immediate-admission flow

- **WHEN** a valid structured reply submits `decision=accept` with normalized
  immediate-admission flow
- **THEN** the case MUST follow the positive doctor-decision path without
  opening the Room-3 scheduling workflow
- **AND** the downstream job path MUST branch to the dedicated
  immediate-admission operational flow

#### Scenario: DENY decision is applied

- **WHEN** a valid structured reply submits `decision=deny`
- **THEN** support semantics MUST remain equivalent to `none`
- **AND** the same denied downstream job path MUST be enqueued

#### Scenario: Duplicate or race reply after decision already applied

- **WHEN** a subsequent decision reply is received after case leaves
  `WAIT_DOCTOR`
- **THEN** the system MUST return a non-applied outcome consistent with
  existing behavior
- **AND** it MUST NOT enqueue duplicate downstream jobs for either scheduled or
  immediate-admission paths

### Requirement: Bot SHALL Emit Decision Result Feedback In Room-2

The bot SHALL publish deterministic success/error feedback in Room-2 after
processing a structured decision reply, with human-readable identification
context and normalized admission-flow echo for accepted decisions.

#### Scenario: Accepted decision is applied

- **WHEN** structured decision processing succeeds for an accepted decision
- **THEN** the bot MUST send a Room-2 confirmation message describing
  successful processing and including `no. ocorrência` and `paciente`
- **AND** the confirmation message MUST echo the normalized
  `fluxo de admissão` value used by the workflow
- **AND** the confirmation message MUST be persisted as a reaction-ack target
  for Room-2 acknowledgment tracking

#### Scenario: Denied decision is applied

- **WHEN** structured decision processing succeeds for a denied decision
- **THEN** the bot MUST send a Room-2 confirmation message describing
  successful processing and including `no. ocorrência` and `paciente`
- **AND** the confirmation message MUST NOT require admission-flow semantics to
  be confirmed for denial handling
- **AND** the confirmation message MUST be persisted as a reaction-ack target
  for Room-2 acknowledgment tracking

#### Scenario: Decision rejected by validation or state

- **WHEN** structured decision processing fails due to format, authorization,
  or state constraints
- **THEN** the bot MUST send a Room-2 error message with actionable correction
  guidance
- **AND** when the correction model targets an accepted decision, it MUST
  preserve the admission-flow line and the UUID case line required by parser
  validation

### Requirement: Room-2 Final Acknowledgment SHALL Be Positive-Only And Non-Blocking

The system SHALL treat positive reaction on the Room-2 decision confirmation
message as an optional doctor acknowledgment audit signal and SHALL NOT gate
decision progression on reaction.

#### Scenario: Positive acknowledgment reaction received

- **WHEN** a doctor reacts with a supported positive key to the Room-2 decision
  confirmation message
- **THEN** the system MUST record acknowledgment audit metadata for that case
- **AND** no additional state transition or job enqueue MUST be required for
  already-applied decision progression

#### Scenario: Non-positive or missing acknowledgment reaction

- **WHEN** reaction key is not a supported positive acknowledgment key, or no
  reaction is sent
- **THEN** the system MUST continue normal workflow without blocking
- **AND** no rollback or re-opening of decision state MUST occur

### Requirement: Room-2 Message II SHALL Include Recent Denial Context When Available

The system SHALL enrich Room-2 message II with an optional recent-denial
context block when a denial for the same occurrence exists in the last 7 days.

#### Scenario: Recent denial exists for same occurrence

- **WHEN** a case is ready for Room-2 message II rendering and recent denial
  context is available for the same `agency_record_number`
- **THEN** message II MUST include a dedicated recent-denial block
- **AND** the block MUST include denial date/time, denial class, and denial
  reason
- **AND** the block MUST keep compatibility with the existing three-message
  Room-2 flow

#### Scenario: No recent denial exists in lookback window

- **WHEN** a case is ready for Room-2 message II rendering and no recent denial
  context is available
- **THEN** message II MUST omit the recent-denial block
- **AND** the message MUST preserve all currently required Room-2 decision
  content and sequencing

### Requirement: Doctor Decision Snapshot SHALL Include Display Name

The system SHALL include the doctor's display name in the decision snapshot,
enabling downstream services to display who accepted the case.

#### Scenario: Decision snapshot is retrieved for accepted case

- **WHEN** a case with a doctor decision is queried via
  `get_case_doctor_decision_snapshot`
- **THEN** the snapshot MUST include `doctor_display_name` field
- **AND** `doctor_display_name` MUST be derived from
  `case_matrix_message_transcripts.sender_display_name` where
  `message_type = 'room2_doctor_reply'`
- **AND** when no display name is available, `doctor_display_name` MUST be
  `None`

#### Scenario: Decision snapshot is used for Room-3 request

- **WHEN** the PostRoom3RequestService builds the Room-3 request message
- **THEN** it MUST pass `doctor_display_name` to the message template
- **AND** the message MUST display the doctor's name or fallback text when
  unavailable

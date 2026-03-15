# Manual E2E Runbook

Language: [Portugues (BR)](../manual_e2e_runbook.md) | **English**

This runbook validates the Matrix flow end-to-end in a controlled/deterministic
local environment, focusing on the most important manual expectations for
Room-2 after the EDA rulebook rewrite.

Run `docs/en/runtime-smoke.md` first to confirm process startup and callback
reachability.

## Prerequisites

1. Start the runtime processes with the same commands used in
   `docs/en/runtime-smoke.md`:

```bash
uv run uvicorn apps.bot_api.main:create_app --factory --host 0.0.0.0 --port 8000
uv run python -m apps.bot_matrix.main
uv run python -m apps.worker.main
```

1. Use a test case already moved to `WAIT_DOCTOR` with the case context posted
   by the bot in Room-2.

## Web Login and Role Menu Checks

1. Anonymous browser access:

- open `GET /`
- expected: redirect to `/login`

1. `reader` session checks:

- log in as the `reader` user via the `POST /login` form
- verify `GET /dashboard/cases` returns `200`
- verify the shell nav contains `Dashboard`
- verify the shell nav does not contain `Prompts`
- verify `GET /admin/prompts` returns `403`

1. `admin` session checks:

- log in as the `admin` user via the `POST /login` form
- verify `GET /dashboard/cases` returns `200`
- verify the shell nav contains `Dashboard` and `Prompts`
- verify `GET /admin/prompts` returns `200` with the list and activation
  controls

1. Logout:

- send `POST /logout` from the shell header
- expected: redirect to `/login`
- verify that a new `GET /` request redirects to `/login`

## Room-2 Structured Reply Positive Path

1. Validate the three-message Room-2 combo for the target case in desktop and
   mobile clients:

- message I: original PDF context
- message II: technical triage summary, reply to message I
- message III: strict template instructions, reply to message I
- verify in desktop and mobile that the messages remain grouped under message I

1. Validate the required content of message II.

Expected in the technical summary:

- context with `requested procedure: ...`
- `pediatric patient: yes` when applicable
- blocks in the order below:
  1. `Clinical summary`
  2. `Critical findings`
  3. `Critical pending items`
  4. `Suggested decision`
  5. `Recommended support`
  6. `Estimated ASA`
  7. `Objective reason`

1. Open message III and copy the strict template.

2. Send the decision as a Matrix reply to message I:

- keep exactly one line per template field
- respect the valid values provided by the bot
- `reason` may be empty/optional

1. For positive-flow validation, send an acceptance response without additional
   support.

2. Validate expected progression:

- case status moves to `DOCTOR_ACCEPTED`
- next job `post_room3_request` is enqueued
- audit includes the Matrix sender as actor and outcome

## Supported EDA Cases: Subtype and Room-2 Context

1. Validate that the following subtypes remain inside the automatic EDA flow:

- `standard`
- `gastrostomy`
- `esophageal_dilation`
- `foreign_body`

1. Execute at least one manual case for each supported subtype.

2. Validate the expected canonical text in the Room-2 message II context:

- `standard` → `requested procedure: EDA`
- `gastrostomy` → `requested procedure: EDA for gastrostomy`
- `esophageal_dilation` → `requested procedure: EDA for esophageal dilation`
- `foreign_body` → `requested procedure: EDA for foreign body removal`

1. Validate that the text shown in Room-2 comes from the canonical subtype and
   not from inconsistent free text in the report.

2. When the case is pediatric (age `< 16`), also validate:

- presence of `pediatric patient: yes`
- marker rendered near the case context, not hidden inside free-text rationale

## Estimated ASA and Recommended Support in Room-2

1. Execute a case with practical `Estimated ASA` equal to `I-II`.

- expected: the `Estimated ASA` block shows `I-II`
- expected: `Recommended support` is compatible with no mandatory additional
  support

1. Execute a case with practical `Estimated ASA` equal to `III or more`.

- expected: the `Estimated ASA` block shows `III or more`
- expected: `Recommended support` is at least `anesthesist`

1. Execute a case with cardiovascular risk high enough for ICU.

- expected: `Recommended support = anesthesist_icu`
- expected: the `Estimated ASA` block remains explicit and separate from support

1. Execute a case with insufficient data for practical ASA.

- expected: the `Estimated ASA` block shows `could not be estimated with the
  presented data`
- expected: support is still derived from the remaining confirmed evidence,
  without inventing a formal ASA class

## EDA Scope Manual Review Path (`non_eda|unknown`)

1. Execute two manual cases with different `preop_screening.exam_type` values:

- case A: `non_eda`
- case B: `unknown`

1. Validate the deterministic result in each case `suggested_action_json`:

- `decision = manual_review_required`
- `suggestion` must not be `accept` or `deny`
- `preop_gate.decision = manual_review_required`
- expected `reason_code`:
  - `non_eda_request` for case A
  - `unknown_exam_type` for case B

1. Validate audit and routing:

- event `EDA_SCOPE_GATED_MANUAL_REVIEW` exists with `reason_code`,
  `reason_text`, and `evidence_spans`
- job `post_room1_final_scope_manual_review` is enqueued/executed
- final message in Room-1 states that the request is not EDA (or is undefined)
  and requires manual review

1. Validate the absence of an automatic recommendation in Room-2 in the same
   cycle:

- there must be no recommendation summary published for this case in Room-2

## Foreign-Body Exception (`foreign_body`)

1. Execute a supported case with subtype `foreign_body`.

2. Build the case without complete minimum exams and without conditional exam
   reports, for example:

- no useful Hb/platelets/INR/TTPa/urea/creatinine
- no minimum ECG report
- no minimum chest X-ray report
- no minimum echocardiogram report

1. Validate the expected deterministic behavior:

- the case remains inside the automatic EDA flow
- `preop_gate.decision = accept`
- `preop_gate.reason_code = foreign_body_exception`
- the absence of those exams does not deny the case for minimum completeness at
  this stage

1. Validate Room-2:

- `requested procedure: EDA for foreign body removal`
- `Objective reason` must not describe denial for missing minimum exams or
  conditional gates when the foreign-body exception applies
- `Recommended support` and `Estimated ASA` may still appear according to the
  remaining clinical context

## Deterministic Denials in the Rewritten Rulebook

### Missing mandatory minimum exams

1. Execute at least one `standard`, `gastrostomy`, or
   `esophageal_dilation` case missing a mandatory minimum exam.

Recommended scenarios:

- missing creatinine
- missing platelets
- TP/INR/RNI without numeric evidence

1. Validate persisted output:

- `suggestion = deny`
- `preop_gate.decision = deny`
- `preop_gate.reason_code` compatible with the missing exam

1. Validate Room-2 message II:

- `Objective reason` explicitly states which minimum exam is missing
- the text stays short and decision-oriented for physician review

### ECG, chest X-ray, and echocardiogram without minimum report when applicable

1. Execute an EDA case with a cardiovascular trigger and without a minimum ECG
   report.

Examples of triggers:

- age `> 40`
- known cardiovascular disease
- chest pain, dyspnea, palpitations, syncope
- diabetes, explicit obesity, multiple comorbidities

1. Execute an EDA case with a respiratory trigger and without a minimum chest
   X-ray report.

2. Execute an EDA case with a structural cardiac trigger and without a minimum
   echocardiogram report.

3. Validate persisted output:

- expected `preop_gate.reason_code`:
  - `missing_ecg_with_cardiovascular_disease`
  - `missing_chest_xray_with_respiratory_risk`
  - `missing_echocardiogram_with_structural_heart_risk`

1. Validate Room-2 message II:

- text must objectively explain the absence of the applicable minimum report
- it must not fall back to generic fallback wording when `reason_code` exists
- wording must be appropriate for quick physician review

### Contraindication by clinical threshold

1. Execute EDA cases with threshold exceeded for each relevant clinical profile,
   when possible:

- general
- explicit hepatopathy
- explicit cardiopathy
- explicit hepatopathy + cardiopathy

1. Example scenarios:

- Hb below threshold
- platelets below threshold
- INR/RNI above threshold

1. Validate persisted output:

- `preop_gate.decision = deny`
- expected `reason_code`:
  - `hb_below_threshold`, or
  - `platelets_below_threshold`, or
  - `inr_above_threshold`

1. Validate Room-2 message II:

- `Objective reason` explicitly states the contraindication and the failed
  threshold
- the text stays short, without acceptance language and without mixing in
  support recommendation

### Objective reason precedence

1. Execute a case with more than one potential denial cause.

Recommended example:

- missing minimum exam **and** missing ECG **and** another pending signal

1. Validate text precedence in `Objective reason`:

- missing mandatory minimum exam has priority over ECG/chest X-ray/echo
- ECG/chest X-ray/echo have priority over threshold contraindication
- if more than two causes exist, Room-2 lists at most two and adds text
  equivalent to `and other critical pending items`

## Widget Negative Auth Checks

1. Send without Authorization header:

- `POST /widget/room2/submit`
- expected: `401`

1. Send with a `reader` role token:

- `POST /widget/room2/submit`
- expected: `403`

1. Validate the absence of unexpected state/job mutation:

- case status does not change
- no additional decision job is enqueued
- only expected auth/audit records are added

## Room-2 Negative Reply Checks

1. Post a malformed template reply:

- reply to message I with missing/invalid required lines
- expected: bot feedback includes `error_code: invalid_template`
- expected: no decision mutation and no new downstream job

1. Post a valid template on the wrong reply parent:

- send the template as a reply to message II/III or an unrelated event
- expected: bot feedback includes `error_code: invalid_template`
- expected: no decision mutation and no new downstream job

## Dashboard and Monitoring API Checks

1. Open the server-rendered dashboard listing in the browser:

- `GET /dashboard/cases` with a valid bearer token
- expected: HTML list renders cases and filters

1. Validate the monitoring listing API:

- `GET /monitoring/cases`
- expected: `200` with JSON containing `items`, `page`, `page_size`, `total`

1. Validate the per-case detail API and auditable events:

- `GET /monitoring/cases/{case_id}`
- expected: `200` with a chronological timeline ordered by `timestamp`
- timeline must include `source`, `channel`, `actor`, `event_type`
- when applicable, validate the presence of ACK and human reply events

1. Cross-check API with dashboard detail:

- open `GET /dashboard/cases/{case_id}`
- verify the chronological timeline visible in the UI matches the monitoring API
  for the same case

## Prompt Management Authorization Flow

1. Using a reader token, verify read-only behavior:

- `GET /monitoring/cases` returns `200`
- `GET /admin/prompts/versions` returns `403`
- `GET /admin/prompts/{prompt_name}/active` returns `403`
- `POST /admin/prompts/{prompt_name}/activate` returns `403`

1. Using an `admin` token, verify prompt mutation:

- `GET /admin/prompts/versions` returns `200`
- `GET /admin/prompts/{prompt_name}/active` returns `200`
- `POST /admin/prompts/{prompt_name}/activate` returns `200`

1. Validate prompt activation side effects:

- exactly one active version remains for the prompt name
- auth audit includes `prompt_version_activated` with actor and target
  prompt/version

1. Validate prompt activation via HTML form (`admin` session):

- open `GET /admin/prompts`
- submit form `POST /admin/prompts/{prompt_name}/activate-form`
- expected: redirect to `/admin/prompts` with activation feedback
- validate the last row in `auth_events` has
  `event_type=prompt_version_activated`

## User Management Authorization Flow

1. Using a reader token, validate access blocking:

- `GET /admin/users` returns `403`
- `POST /admin/users` returns `403`
- `POST /admin/users/{user_id}/block` returns `403`
- `POST /admin/users/{user_id}/activate` returns `403`
- `POST /admin/users/{user_id}/remove` returns `403`
- expected: no user-account mutation

1. Using an `admin` session, validate account creation:

- open `GET /admin/users`
- submit form `POST /admin/users` to create a `reader`
- expected: redirect to `/admin/users` with `Usuario criado` feedback
- validate that the new user appears in the listing with `active` state
- validate audit in `auth_events`:
  - query the latest event for the target:

    ```sql
    SELECT event_type, user_id, payload
    FROM auth_events
    WHERE payload->>'target_user_id' = '<target_user_id>'
    ORDER BY occurred_at DESC
    LIMIT 1;
    ```

  - `event_type=user_created`
  - event `user_id` equals the admin actor
  - `payload` includes `target_user_id`, `target_email`, `target_role`,
    `previous_status`, `new_status`
  - expected `previous_status`: `null`
  - expected `new_status`: `active`

1. Using an `admin` session, validate blocking an active account:

- send `POST /admin/users/{user_id}/block` for an `active` target user
- expected: redirect to `/admin/users` with update feedback
- validate in the listing that the target user changes to `blocked` state
- validate `POST /auth/login` with the target user credentials returns `403`
  (`inactive user`)
- validate audit in `auth_events`:
  - query the latest event for the target:

    ```sql
    SELECT event_type, user_id, payload
    FROM auth_events
    WHERE payload->>'target_user_id' = '<target_user_id>'
    ORDER BY occurred_at DESC
    LIMIT 1;
    ```

  - `event_type=user_blocked`
  - event `user_id` equals the admin actor
  - `payload.target_user_id` equals the target user
  - `payload.previous_status=active`
  - `payload.new_status=blocked`

1. Using an `admin` session, validate reactivating a blocked account:

- send `POST /admin/users/{user_id}/activate` for a `blocked` target user
- expected: redirect to `/admin/users` with update feedback
- validate in the listing that the target user returns to `active` state
- validate `POST /auth/login` with the target user credentials returns `200`
- validate audit in `auth_events`:
  - query the latest event for the target:

    ```sql
    SELECT event_type, user_id, payload
    FROM auth_events
    WHERE payload->>'target_user_id' = '<target_user_id>'
    ORDER BY occurred_at DESC
    LIMIT 1;
    ```

  - `event_type=user_reactivated`
  - event `user_id` equals the admin actor
  - `payload.target_user_id` equals the target user
  - `payload.previous_status=blocked`
  - `payload.new_status=active`

1. Using an `admin` session, validate administrative removal (soft delete):

- send `POST /admin/users/{user_id}/remove` for the target user
- expected: redirect to `/admin/users` with update feedback
- validate in the listing that the target user changes to `removed` state
- validate `POST /auth/login` with the target user credentials returns `403`
  (`inactive user`)
- validate audit in `auth_events`:
  - query the latest event for the target:

    ```sql
    SELECT event_type, user_id, payload
    FROM auth_events
    WHERE payload->>'target_user_id' = '<target_user_id>'
    ORDER BY occurred_at DESC
    LIMIT 1;
    ```

  - `event_type=user_removed`
  - event `user_id` equals the admin actor
  - `payload.target_user_id` equals the target user
  - `payload.previous_status=active` or `blocked`
  - `payload.new_status=removed`

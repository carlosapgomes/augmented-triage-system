# Manual E2E Runbook

Language: [Portugues (BR)](../manual_e2e_runbook.md) | **English**

This runbook validates the full operational workflow end-to-end in a
controlled/deterministic local environment, covering both the operational web
interface (NIR, doctor, scheduler) and the monitoring/audit dashboard.

> **Final supported surface:** validation is now exclusively Django-first. FastAPI and Matrix are backend components — their human/administrative surfaces have been retired. Steps below that still mention FastAPI/Matrix are marked as legacy reference and are not required for operational validation.
>
> **Publication topology:** the official publication topology (internal and
> external paths, role/zone access matrix) is documented in
> `docs/en/publication-topology.md`. The E2E validation below assumes
> local (internal) access on port 8001.

Run `docs/en/runtime-smoke.md` first to confirm process startup and callback
reachability.

## Prerequisites

> **Cutover note:** all human and administrative surfaces are consolidated in Django (port 8001). FastAPI (`bot-api`) and Matrix (`bot-matrix`) operate exclusively as backend runtime. Sections below that mention `bot-api` (FastAPI) or Matrix interactions for medical decision/scheduling are historical legacy reference. **Complete operational validation is achieved exclusively through the Django web flow.**

1. Start the runtime processes with the same commands used in
   `docs/en/runtime-smoke.md`:

```bash
# Monitoring API (FastAPI)
uv run uvicorn apps.bot_api.main:create_app --factory --host 0.0.0.0 --port 8000

# Operational web app (Django) — port 8001
uv run apps/django_ops/manage.py runserver 0.0.0.0:8001

# Matrix bot (for downstream jobs and transcripts)
uv run python -m apps.bot_matrix.main

# Job worker
uv run python -m apps.worker.main
```

1. The database must be migrated (`alembic upgrade head`).

1. Create test users for each operational role if they don't exist yet:

```bash
uv run apps/django_ops/manage.py create_user nir@test.com test123 nir
uv run apps/django_ops/manage.py create_user doctor@test.com test123 doctor
uv run apps/django_ops/manage.py create_user scheduler@test.com test123 scheduler
uv run apps/django_ops/manage.py create_user manager@test.com test123 manager
uv run apps/django_ops/manage.py create_user admin@test.com test123 admin
```

## Web Login and Role Menu Checks

1. Anonymous browser access:

- open `GET /`
- expected: redirect to `/login`

1. `manager` session checks:

- log in as the `manager` user via the `POST /login` form
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

## Web Operational Workflow

The main human operational flow (NIR → Doctor → Scheduler → NIR) is executed
exclusively through the Django web app on port 8001.

### NIR — PDF Upload and Case Creation

1. Go to `/login/` on port 8001 and authenticate as `nir@test.com`.

1. After login, verify redirect to `/nir/` with:
   - a "New Case" link pointing to `/nir/upload/`
   - listing of active cases (if any)

1. Click the upload link and verify:
   - form with file upload field
   - submit button

1. Select a valid PDF file and submit:
   - expected: result page showing `case_id` and status "Recebido — processando"
   - the worker should enqueue the `process_pdf_case` job automatically

1. Verify auditable creation:
   - go back to `/nir/` and confirm the new case appears in the listing
   - open the case detail at `/nir/cases/{case_id}/`
   - verify the "Linha do Tempo" (Timeline) section contains
     a `NIR_PDF_UPLOAD` event with source `[web]`
   - verify the event actor is the logged-in NIR email

1. Negative checks:
   - submit a non-PDF file (e.g. `.txt`): must reject with error message
   - submit without selecting a file: must reject with error message
   - access `/nir/upload/` as `doctor@test.com`: must return 403

### Doctor — Web Queue and Decision

1. After the case is processed by the worker and reaches `WAIT_DOCTOR` status,
   go to `/login/` and authenticate as `doctor@test.com`.

1. Verify redirect to `/doctor/` with:
   - listing of cases awaiting decision (`WAIT_DOCTOR` status)
   - each card shows clinical summary and decision link

1. Click the decision link and verify the form at
   `/doctor/cases/{case_id}/decision/`:
   - fields: decision (accept/deny), support, admission flow, reason
   - patient data visible (name, age, record number)

1. Submit an acceptance decision with scheduling:
   - `decision: accept`
   - `admission flow: scheduled`
   - expected: redirect to `/doctor/` and the case disappears from the queue
   - verify in the case detail (via `/monitoring/cases/{case_id}`)
     that the `DOCTOR_DECISION` event appears in the timeline with
     source `web` and actor `doctor@test.com`

1. Submit a denial decision (another case):
   - `decision: deny`
   - `reason: insufficient documentation`
   - expected: redirect and case leaves the doctor queue

1. Negative checks:
   - submit accept without admission flow: must reject with error
   - submit deny without reason: must reject with error
   - submit with invalid `support_flag`: must reject
   - access `/doctor/` as `nir@test.com`: must return 403

### Scheduler — Web Queue and Confirmation

1. After a doctor acceptance with scheduling, the case advances to
   `WAIT_APPT`. Go to `/login/` and authenticate as `scheduler@test.com`.

1. Verify redirect to `/scheduler/` with:
   - listing of cases awaiting confirmation (`WAIT_APPT` status)
   - each card shows summary and confirmation link

1. Click the link and verify the form at
   `/scheduler/cases/{case_id}/confirm/`:
   - fields: action (confirm/deny), date, time, location,
     instructions (optional)
   - patient data visible

1. Submit a confirmation:
   - `action: confirm`
   - fill in date (DD/MM/YYYY), time (HH:MM), location
   - expected: redirect to `/scheduler/` and case disappears from queue
   - verify in timeline (via `/monitoring/cases/{case_id}`)
     that the `SCHEDULER_CONFIRMATION` event appears with
     source `web` and actor `scheduler@test.com`

1. Submit a denial (another case):
   - `action: deny`
   - `reason: no slots available`
   - expected: redirect, case leaves queue

1. Negative checks:
   - confirm without date: must reject with error
   - confirm without time: must reject with error
   - confirm without location: must reject with error
   - invalid date/time format: must reject with error
   - deny without reason: must reject with error
   - access `/scheduler/` as `doctor@test.com`: must return 403

### NIR — Final Result and Acknowledgment

1. After scheduler confirmation, the worker processes the
   `post_room1_final_appt` job and the case advances to
   `WAIT_R1_CLEANUP_THUMBS`.

1. Access the case detail as NIR at `/nir/cases/{case_id}/`.

1. Verify the "Resultado Final" (Final Result) section:
   - must display a "Confirmar Recebimento do Resultado" button
   - case status must be `WAIT_R1_CLEANUP_THUMBS`

1. Click the confirmation button:
   - expected: redirect to `/nir/`
   - the case should disappear from the NIR listing
     (status changes to `CLEANED` after the `execute_cleanup` job)
   - verify in timeline (via `/monitoring/cases/{case_id}`)
     that the `NIR_FINAL_ACKNOWLEDGMENT` event appears with
     source `web` and actor `nir@test.com`

1. This step replaces the thumbs-up reaction in Room-1 (Matrix) as the
   canonical human closure checkpoint.

## Room-2 Structured Reply Positive Path (Matrix — legacy reference)

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

2. Validate that the acceptance template explicitly includes the line
   `admission flow: scheduled`.

3. Send the decision as a Matrix reply to message I:

- keep exactly one line per template field
- respect the valid values provided by the bot
- `reason` may be empty/optional
- for `decision: accept`, fill the `admission flow` line mandatorily

### Accepted with scheduled admission

1. For the default positive-path validation, send an acceptance response without
   additional support using `admission flow: scheduled`.

2. Validate expected progression:

- case status moves to `DOCTOR_ACCEPTED`
- next job `post_room3_request` is enqueued
- the bot confirmation in Room-2 echoes the normalized flow as `scheduled`
- Room-3 receives the standard scheduling request + template combo
- audit includes the Matrix sender as actor and outcome

### Accepted with immediate admission

1. Repeat the acceptance flow using `admission flow: vinda_imediata`.

2. Validate accepted aliases in mobile clients when applicable:

- `vinda_imediata`
- `vinda imediata`

1. Validate the expected progression for the immediate branch:

- the medical status remains `DOCTOR_ACCEPTED` until the Room-1 final message
- next job `post_immediate_admission_flow` is enqueued
- the bot confirmation in Room-2 echoes the normalized immediate flow
- Room-3 receives only the informational immediate-admission communication and
  the auditable ACK target
- Room-3 must not receive the standard scheduling combo (`post_room3_request`)
- Room-1 receives the final message equivalent to
  `accepted with immediate admission authorized`
- closure proceeds via the positive Room-1 reaction through
  `post_room1_final_immediate`
- the Room-3 acknowledgment remains optional, not mandatory, for case closure

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

1. Send with a `manager` role token:

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

1. Post `decision: accept` without the required `admission flow` line:

- example: accept without the required `admission flow` line
- expected: the decision is rejected without state/job mutation
- expected: the bot correction message restores the required field in the
  template

1. Post `decision: accept` with an invalid `admission flow` value:

- invalid examples: `plantao`, `urgent`, or any value outside
  `scheduled|vinda_imediata`
- expected: the decision is rejected without state/job mutation
- expected: no scheduling is opened and no `post_immediate_admission_flow` job
  is created

## Dashboard and Monitoring API Checks

1. Open the server-rendered dashboard listing in the browser:

- `GET /dashboard/cases` with a valid bearer token
- expected: HTML list renders cases and filters
- validate the per-case compact operational summary (`current status · pending stage · operational branch`) whenever it differs from the legacy outcome shown in the row
- validate the operational search totals with at least: `casos em andamento`, `aguardando Sala 2`, `aguardando Sala 3`, `aguardando Sala 1`, and `pendentes no ramo vinda imediata`
- validate the operational filters for `status atual`, `etapa pendente`, `ramo operacional`, and `desfecho final`

1. Validate the monitoring listing API:

- `GET /monitoring/cases`
- expected: `200` with JSON containing `items`, `page`, `page_size`, `total`

1. Validate the per-case detail API and auditable events:

- `GET /monitoring/cases/{case_id}`
- expected: `200` with a chronological timeline ordered by `timestamp`
- timeline must include `source`, `channel`, `actor`, `event_type`
- when applicable, validate the presence of ACK, human reply, and **web human events**
  (`NIR_PDF_UPLOAD`, `DOCTOR_DECISION`, `SCHEDULER_CONFIRMATION`,
  `NIR_FINAL_ACKNOWLEDGMENT`) with `source="web"`
- verify that web and matrix events coexist in the same timeline with
  distinct origins

1. Cross-check API with dashboard detail:

- open `GET /dashboard/cases/{case_id}`
- verify the chronological timeline visible in the UI matches the monitoring API
  for the same case
- validate the `Resumo Operacional` block above the timeline with `status atual`, `etapa pendente`, `ramo operacional`, and `desfecho final`
- for a pending `vinda imediata` case, validate that the detail still shows `EM_ANDAMENTO`/`AGUARDANDO_SALA_1` until the final Room-1 acknowledgment is received
- switch between `view=thread` and `view=pure` and confirm the operational summary remains visible in both

## Prompt Management Authorization Flow

1. Using a manager token, verify read-only behavior:

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

1. Using a manager token, validate access blocking:

- `GET /admin/users` returns `403`
- `POST /admin/users` returns `403`
- `POST /admin/users/{user_id}/block` returns `403`
- `POST /admin/users/{user_id}/activate` returns `403`
- `POST /admin/users/{user_id}/remove` returns `403`
- expected: no user-account mutation

1. Using an `admin` session, validate account creation:

- open `GET /admin/users`
- submit form `POST /admin/users` to create a `manager`
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

# Immediate admission flow and Room-2 contract tasks

## 1. Decision contract, persistence, and routing foundations

- [x] 1.1 Add persisted admission-flow support to the case model, repository ports/snapshots, and database metadata/migration so accepted decisions can store the normalized doctor-selected branch.
  - 2026-03-14 verification (Task 1.1 slice): `uv run pytest tests/integration/test_case_repositories.py tests/integration/test_migration_case_doctor_admission_flow.py -q`, `uv run ruff check src/triage_automation/application/ports/case_repository_port.py src/triage_automation/infrastructure/db/case_repository.py src/triage_automation/infrastructure/db/metadata.py alembic/versions/0017_case_doctor_admission_flow.py tests/integration/test_case_repositories.py tests/integration/test_migration_case_doctor_admission_flow.py`, and `uv run mypy src/triage_automation/application/ports/case_repository_port.py src/triage_automation/infrastructure/db/case_repository.py src/triage_automation/infrastructure/db/metadata.py` passed.
- [x] 1.2 Extend the Room-2 structured reply parser, shared decision DTOs, and normalized reply event models to support `fluxo de admissão`, accepted aliases, and deny-specific optional semantics.
  - 2026-03-14 verification (Task 1.2 slice): `uv run pytest tests/unit/test_doctor_decision_parser.py tests/unit/test_room2_reply_parser.py tests/unit/test_widget_models.py -q`, `uv run ruff check src/triage_automation/domain/doctor_decision_parser.py src/triage_automation/application/dto/webhook_models.py src/triage_automation/application/dto/widget_models.py src/triage_automation/application/services/room2_reply_service.py src/triage_automation/infrastructure/matrix/room2_reply_parser.py tests/unit/test_doctor_decision_parser.py tests/unit/test_room2_reply_parser.py tests/unit/test_widget_models.py`, and `uv run mypy src/triage_automation/domain/doctor_decision_parser.py src/triage_automation/application/dto/webhook_models.py src/triage_automation/application/dto/widget_models.py src/triage_automation/application/services/room2_reply_service.py src/triage_automation/infrastructure/matrix/room2_reply_parser.py` passed.
- [ ] 1.3 Update `HandleDoctorDecisionService` and related routing helpers to persist `doctor_admission_flow`, keep deny behavior unchanged, and branch accepted cases to scheduling vs immediate-admission jobs deterministically.

## 2. Room-2 templates and feedback

- [ ] 2.1 Update Room-2 decision template and formatted HTML builders to show the explicit `fluxo de admissão: agendamento` line in the copy-ready physician reply model.
- [ ] 2.2 Update Room-2 success and error feedback templates so accepted decisions echo the normalized admission flow and correction guidance preserves the new required field.
- [ ] 2.3 Add or adjust parser and Room-2 reply-flow tests covering scheduled acceptance, immediate-admission aliases, deny permissiveness, unknown-field rejection, and duplicate/race handling.

## 3. Immediate-admission orchestration across rooms

- [ ] 3.1 Implement the dedicated immediate-admission workflow job/service that posts the informational Room-3 message and Room-3 acknowledgment target without opening scheduling.
- [ ] 3.2 Ensure the immediate-admission workflow propagates the required context (requested procedure, physician, support, pediatric marker, and relevant subtype) consistently to Room-3 and Room-1 messages.
- [ ] 3.3 Make the Room-3 portion of the immediate-admission workflow explicitly non-blocking, idempotent, and auditable when posting fails or when only partial progress is completed.

## 4. Room-1 finalization, state progression, and recovery

- [ ] 4.1 Extend `PostRoom1FinalService` and Matrix templates with the final Room-1 message variant for `aceito com vinda imediata autorizada`, reusing the existing cleanup checkpoint path.
- [ ] 4.2 Update recovery logic, job resolution, and any state-transition guards needed so accepted immediate-admission cases resume the correct branch after restart and do not enqueue Room-3 scheduling jobs.
- [ ] 4.3 Add integration coverage for the immediate-admission branch, including Room-3 notification success, Room-3 failure tolerance, Room-1 closure gating, and retry/idempotency behavior.

## 5. Documentation and verification

- [ ] 5.1 Update `docs/manual_e2e_runbook.md` to document the new Room-2 template, scheduled acceptance path, immediate-admission path, and new negative validation cases.
- [ ] 5.2 Update `docs/en/manual_e2e_runbook.md` as the required English mirror for the runbook changes.
- [ ] 5.3 Run targeted `pytest`, `ruff`, `mypy`, markdown lint, and bilingual doc guards for the changed paths and record the results in this task file during implementation.

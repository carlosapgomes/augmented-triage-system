# AGENTS.md

Repository-level execution guide for Codex sessions.

## Objective

Implement OpenSpec changes safely, one task at a time, with deterministic progress and clean handoffs when context resets.

## Mandatory Workflow (Per Session)

1. Read this file first.
2. Use the `openspec-apply-change` skill when implementing tasks.
3. Read only the selected change/task artifacts needed for the current step.
4. Execute exactly one task slice at a time.
5. Respect task scope boundaries and STOP RULE.
6. Stop after finishing the slice and wait for user approval to continue.

## Architecture and Behavior Constraints

1. Preserve architecture direction: `adapters -> application -> domain -> infrastructure`.
2. Do not introduce business logic in adapters.
3. Do not redesign workflow/state machine unless explicitly requested in task/spec.
4. Do not change LLM schemas/prompts/workflow behavior unless explicitly requested in task/spec.
5. Keep changes small, deterministic, and reversible.

## TDD and Quality Gates

1. Tests first:
   - Add/adjust tests for the slice before implementation.
   - Confirm failure (red), then implement (green), then refactor.
2. Type hints are required on new/changed Python code.
3. Docstrings are required on new/changed public modules, classes, and functions.
4. Prefer targeted tests for speed; run broader checks when slice requires it.

## Verification Commands

Run applicable commands for the slice:

```bash
uv run pytest <targeted-tests>
uv run ruff check <changed-paths>
uv run mypy <changed-paths-or-package>
```

If a command cannot be run, report why explicitly.

## Task Tracking

1. Update the corresponding OpenSpec task file after implementation.
2. Mark completed checklist items as done.
3. Record any deviations/notes directly in the task file when needed.

## Commit and Push Policy

1. After each completed slice:
   - Commit with a meaningful message tied to the slice.
   - Push to remote.
2. Do not bundle unrelated changes in the same commit.
3. Do not rewrite history unless explicitly requested.

## Default Session Prompt (User Re-entry)

Use this when restarting work:

```text
Use the openspec-apply-change skill.
Change ID: <change-id>
Task file: <task-file>
Implement only this task slice, following AGENTS.md constraints.
Use TDD, add/update docstrings and type hints, run verification, update task checklist, commit, push, then stop.
```


---
name: breakdown-task-plan
description: Pipeline Node 2 - engineering-level atomic decomposition. Decompose OpenSpec specs+tasks into an atomic task list TASK_PLAN.md at single-file/single-function granularity, with topological ordering and dependency annotations. No requirement understanding (OpenSpec already did that) - only engineering refinement.
---

# Engineering-level atomic decomposition

## 1. Skill overview
- **Stage**: Pipeline Node 2 (after entry, before location)
- **Upstream dependencies**: OpenSpec `tasks.md` (with fileHint/symbolHint/dependsOn) + OpenSpec `specs/*.md` + OpenSpec `design.md`
- **Downstream output**: `TASK_PLAN.md` (passed to Node 3, the location stage)
- **Core goal**: refine OpenSpec's functional task list and interface specs into atomic tasks at file/function granularity, with topological ordering. **No requirement understanding** (OpenSpec already did that) — only engineering decomposition.
- **Greenfield mode** (`[CODEBASE] greenfield`): produce a **summary TASK_PLAN** — task IDs, file paths, symbols, dependency order. Skip detailed `openspec_ref` and `coordination constraint` fields (every file is NEW, no existing code to coordinate with). The topological order is the primary output; the detailed task cards are collapsed to one-liners.
- **Brownfield mode** (`[CODEBASE] brownfield`): full TASK_PLAN with all fields per the format below — every task must trace back to an openspec_ref, and every MODIFY task must note coordination constraints with existing code.

## 2. Input specification
| Input type | Format requirement | Required |
|:---|:---|:---|
| Functional task list | OpenSpec `tasks.md` (with target file/target symbol/dependencies) | **Required** |
| Interface specs | OpenSpec `specs/*.md` (with interface contracts, state machines, edge cases) | **Required** |
| Design document | OpenSpec `design.md` (with technical approach and architecture decisions) | Recommended |

## 3. Processing flow

### Step 1: Read the task list
- Read `tasks.md`, extracting for each task: task name, target file, target symbol, dependencies, description
- Read `specs/*.md`, extracting the interface contract definitions (used to judge function granularity during decomposition)
- Read `design.md` (if present), extracting module partitioning and file mappings

### Step 2: Atomicity decomposition — refine as needed

For each tasks.md entry, decide whether further decomposition is needed:

**Decomposition rules**:
- A feature touching multiple files → split into multiple atomic tasks (one per file)
- A feature touching multiple independent functions in one file → split into multiple atomic tasks (one per function)
- A feature touching only one function in one file → keep as a single atomic task

**Three atomicity principles**:
1. **Single file**: a task modifies only 1 source file
2. **Single function/single logic**: a task handles only 1 function/method or 1 kind of independent logic
3. **Independently verifiable**: each task can independently run L0/L1 self-checks after completion

**Self-check requirement calculation** (extracted from specs, written into the "self-check requirements" field of TASK_PLAN):

| Definition in specs | L1 self-check requirement | Source |
|:---|:---|:---|
| Ordinary function (no state machine/validation logic) | ≥1 assert covering the happy path | SELF_VERIFY default |
| State machine (N states + M legal transitions + K illegal transitions) | ≥(M+K) asserts | 1 per legal transition + 1 per illegal transition |
| Data validation logic | ≥1 assert (valid input) + ≥1 assert per invalid input type | 1 per invalid type |
| Only comments/docs/annotations modified | No self-check needed, mark `[TRIVIAL]` | — |
| Pure data class / function body ≤3 lines with no branches | No self-check needed, mark `[TRIVIAL]` | — |

**Decomposition example**:

```
Input tasks.md:
  T001: Add user authentication service
    Target file: src/services/auth_service.py
    Target symbol: AuthService
    Depends on: none

Decomposed TASK_PLAN (flat IDs — no T001-1 hierarchical naming):
  T002: Add AuthService.login method (split from tasks.md T001)
    Target file: src/services/auth_service.py
    Target symbol: AuthService.login
    Depends on: none

  T003: Add AuthService._verify_password method (split from tasks.md T001)
    Target file: src/services/auth_service.py
    Target symbol: AuthService._verify_password
    Depends on: T002
```

**ID naming rules**:
- Use flat incrementing IDs: T001, T002, T003... (no hierarchy)
- Each atomic task is numbered independently, with no hierarchical relation to the original tasks.md entries
- The openspec_ref field traces back to the original tasks.md entry (e.g. `tasks.md "T001: Add user authentication service"`)
- No nesting even on deep decomposition: T001→may split into T002/T003/T004, T002→may split into T005/T006

### Step 3: Dependency graph construction + topological sorting

- Get the base dependency relations from the dependsOn field in tasks.md
- Get inter-module call dependencies from the interface contracts in specs/*.md (module A calls a function in module B → B must come before A)
- Build the full dependency graph and produce a topological order

**Rules**:
- Data model layer (models/utils) → business service layer (services) → external interface layer (api/routes)
- A depended-on task ID must be lower than the ID of its dependents

### Step 4: Atomicity red-line checks

- **Critical red lines (blocking)**:
  - A task touching ≥2 unrelated source files → must be split
  - A task description containing vague connectives ("etc."/"and also") → must be split
  - A task with no target file → mark `[AMBIGUOUS]` and halt
- **Standard red lines (warning level)**:
  - Orphaned tasks (no dependsOn but implied dependency) → AI adds a `[GUESSED_DEP]` annotation

### Step 5: Generate TASK_PLAN.md

Write `ai_pipeline/TASK_PLAN.md`.

**Task card field definitions**:

| Field | Required | Description |
|:---|:---|:---|
| openspec_ref | ✅ | Traces back to the OpenSpec tasks.md entry |
| Target file | ✅ | Physical file path |
| Target symbol | ✅ | Function/class/method name |
| Change type | ✅ | ADD / MODIFY / DELETE |
| Depends on | ✅ | List of prerequisite task IDs (comma-separated), or "none" |
| Type flag | No | MIGRATION / FINANCE / ISOLATION / ALGORITHM / STATE_MACHINE / EXTERNAL_TOOL / none. Node 4 performs special checks based on it |
| Coordination constraint | No | Cross-module coordination notes. Format: "Coordinate with T00X,T00Y: <constraint description>". Or "none" |
| Self-check requirements | ✅ | N asserts + specific coverage items, or [TRIVIAL]. Node 4 L1 generates self-check cases from this |
| Interface contract | No | Reference to the specs/*.md path and section |

**Type flag trigger rules**:

| Flag | Trigger condition | Node 4 special handling |
|:---|:---|:---|
| MIGRATION | Task involves DDL (CREATE/ALTER/DROP) | Requires dry-run verification + rollback script |
| FINANCE | Task involves amounts/billing/prices | Enforce Decimal/Fixed-Point, forbid float/double |
| ISOLATION | Task involves multi-tenant data access | L2 additionally checks: all queries include a tenant filter condition |
| ALGORITHM | Task involves merge/encode/encrypt/compress algorithms | Self-check ≥3 asserts (different input scenarios) |
| STATE_MACHINE | Task involves state machine implementation | Self-check assert count = legal transitions + illegal transitions |
| EXTERNAL_TOOL | Task depends on external system tools (ffmpeg/ImageMagick, etc.) | Check tool installation before Node 4 starts; prompt the user if missing |
| none | Ordinary CRUD/business logic | Default self-check ≥1 assert (happy path) |

**TASK_PLAN.md format**:

```markdown
# Task Execution Plan — <change-name> — <date>

## Total tasks: N
## Execution order (topological)

1. [T001] → 2. [T002] → 3. [T003] (depends on T001,T002)

## Detailed task cards

### T001: Add AuthService.login method
- **openspec_ref**: tasks.md "T001: Add user authentication service"
- **Target file**: src/services/auth_service.py
- **Target symbol**: AuthService.login
- **Change type**: ADD (new method)
- **Depends on**: none
- **Type flag**: none
- **Coordination constraint**: none
- **Self-check requirements**: 1 assert (happy path: valid username+password → returns token)
- **Interface contract**: see specs/auth/spec.md §login interface (inputs: username/password → outputs: token/expires_in)

### T002: Add query method to the User model
- **openspec_ref**: tasks.md "T002: Add query method to user model"
- **Target file**: src/models/user.py
- **Target symbol**: User.find_by_username
- **Change type**: ADD (new method)
- **Depends on**: none
- **Type flag**: none
- **Coordination constraint**: none
- **Self-check requirements**: [TRIVIAL] (single-line query, no branches)

### T003: Add state machine to TaskExecutor
- **openspec_ref**: tasks.md "T003: Add state machine to task executor"
- **Target file**: src/tools/task_executor.py
- **Target symbol**: TaskExecutor
- **Change type**: MODIFY (add state transition logic)
- **Depends on**: T001, T002
- **Type flag**: STATE_MACHINE
- **Coordination constraint**: none
- **Self-check requirements**: 8 asserts (5 legal transitions: IDLE→PENDING/PENDING→RUNNING/RUNNING→SUCCESS/RUNNING→FAILED/FAILED→PENDING + 3 illegal transitions rejected: SUCCESS→anything/FAILED→RUNNING/CANCELLED→anything)
- **Interface contract**: see specs/task/spec.md §5.1
```

## 4. Immediate sedimentation

After decomposition completes, append to RUN_LOG:

```
## [timestamp] Node 2 complete
- tasks.md N entries → TASK_PLAN N atomic tasks
- Topological order: T001 → T002 → T003
- Atomicity: ✅ (no multi-file/ambiguous tasks)
```

## 5. Successful exit criteria

- TASK_PLAN.md has been generated, with task count ≥ the number of entries in OpenSpec tasks.md (decomposition only refines and adds tasks, never removes; when Node 4 triggers the R2 reuse ruling, the corresponding task is marked `REUSED` and kept in the plan, not deleted)
- All tasks satisfy the single-file atomicity principle
- Topological sorting is complete, and every task has an explicit depends_on
- Every task is traceable to the OpenSpec tasks.md (the openspec_ref field is non-empty)

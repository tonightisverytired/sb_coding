---
name: sb-coding
description: >
  OpenSpec + Pipeline + Ponytail parallel development system.
  OpenSpec handles business planning (explore/propose/sync), Pipeline handles engineering execution (locate→implement→verify→commit),
  Ponytail handles code minimization. Each plays to its strengths without overlapping.
---

# Parallel development system

## Architecture

```
OpenSpec (planning)                        Pipeline (execution) + Ponytail (implementation)
─────────────────                    ───────────────────────────────────────────────
explore → propose → update           Node 2 (decompose) → Node 3 (locate) → Node 4 (implement) → Node 5 (verify) → Node 6 (runtime) → Node 8 (commit)
        ↓                                    ↑
   sync → archive                    Ponytail full + RUN_LOG/ERROR_MEMORY throughout
```

**Key design**: OpenSpec and Pipeline do not overlap. Once OpenSpec finishes planning, Pipeline starts from Node 3 (precise location) and directly consumes OpenSpec artifacts. No duplicated requirement understanding or task decomposition.

## 1. Responsibilities

| System | Responsibility | Core capabilities |
|:---|:---|:---|
| **OpenSpec** | Business planning | explore, propose (create change + artifacts), update, sync (incremental spec management), archive |
| **Pipeline** | Engineering execution | Node 3 (precise location), Node 4 (compile check + self-heal), Nodes 5/6 (quality gates), Node 8 (semantic commit) |
| **Ponytail** | Code minimization | Ladder framework (L2-L7: reuse→stdlib→native→one-line→minimal; ladder levels are unrelated to the C-series complexity levels), over-engineering review, tech-debt tracking |

## 2. Entry: route by complexity

When invoking this skill, **the first step is to judge the complexity** and decide which nodes to run. Principle: **don't do work that isn't worth doing**.

### C0: single-file / single-function changes (e.g. typo, small bugfix, adding a field)

**Applicability**: no risk flags (see "risk escalation" below), and only 1 file is modified.

Skip all planning. Write code directly, run Layer 0 + Layer 1 self-checks, commit.

```
Output: 1 modified file + 1 ERROR_MEMORY entry (if an error occurred)
Not run: grill-me / propose / decomposition / location / verification / sedimentation
```

### C1a: small multi-file changes (2-3 files, single module, no cross-module coordination, no risk flags; e.g. a field addition with linked modifications)

Lightweight path. **No full propose**: planning folds into one `ai_pipeline/CHANGE_NOTES.md` (requirements + interface contract + tasks, marked `[LIGHT_PLAN]`); the rest of the flow is the same as C0.

**Artifact folding**: C1a maintains only 1 append-only `CHANGE_NOTES.md` throughout (planning → implementation summary → self-check results → commit summary, crash-safe); no separate PIPELINE_STATUS / RUN_LOG / COMMIT_MESSAGE / VERIFY reports; commit messages are inline via `git commit -m`; ERROR_MEMORY is appended only on errors/self-heals.

```
grill-me (optional; triggered when >2 decisions) → lightweight plan CHANGE_NOTES.md ([LIGHT_PLAN])
  → write code directly → Layer 0/Layer 1 self-checks (done by the model itself) → tests → commit
  → contract sync (Phase D-lite, see below) → done
Not run: propose / Node 2 decomposition / Node 3 location / Node 2/3/4 reports / full Phase D (sync/archive)
```

**Contract sync (Phase D-lite)**: append the "interface contract" section of CHANGE_NOTES to `openspec/specs/<capability>/spec.md` in the main spec format (`## ADDED Requirements` + `#### Scenario`) (infer the capability from the implemented module; if the main spec does not exist, create a minimal file marked `[NEW_SPEC]`) → git commit; if there is no openspec repo → mark `[NO_SPEC_SYNC]` and record it as a to-do in CHANGE_NOTES.

### C1b: multi-file functional changes (cross-module, or 4-10 files, or with risk/environment flags; e.g. adding OAuth, adding rate-limit middleware)

Run proposal + implementation + verification. Decomposition and location are covered by the model's built-in capabilities; Nodes 2/3 are not run explicitly.

```
grill-me (optional; triggered when >2 decisions) → propose → write code directly
  → Layer 0/Layer 1 self-checks (done by the model itself) → tests → commit
Not run: Node 2 decomposition (the model does not need explicit decomposition) / Node 3 location (the model locates itself)
```

### C2: large platform / subsystem (e.g. trading engine, e-commerce platform, EHR)

Full chain. grill-me is triggered when there are >3 architectural decisions; all nodes execute.

But **reports are folded**: TASK_PLAN + LOCATE_MAP + IMPLEMENTATION_REPORT from Nodes 2/3/4 merge into one `ai_pipeline/IMPLEMENTATION_LOG.md` — no three separate documents.

```
grill-me (if >3 decisions) → explore (if clarification is needed) → propose → Nodes 2/3/4 (folded into LOG) → 5 → 6 → 8 → Phase D
Full sedimentation: ERROR_MEMORY + TECH_NOTES
```

### Routing rules

| Metric | C0 single file | C1a small multi-file | C1b multi-file/cross-module | C2 platform-level |
|:---|:---|:---|:---|:---|
| Files modified | =1 | 2-3 | 4-10 | >10 |
| New capabilities | 0 | 1 | 1-2 | ≥3 |
| grill-me | skipped | optional | optional (triggered when >2 decisions) | triggered when >3 decisions |
| Node 2/3/4 reports | skipped | skipped | ≤5 files skipped, >5 generated | generated (folded into LOG) |
| C0/C1a/C1b/C2 self-check depth | Layer 0 (import only) | pytest+ruff | pytest+ruff | full |
| Sedimentation | ERROR_MEMORY | ERROR_MEMORY | ERROR_MEMORY | ERROR_MEMORY+TECH_NOTES |
| Node 2/3 mode (greenfield) | skipped | skipped | summary (no LOCATE_MAP) | summary (folded 1-liner) |
| Node 2/3 mode (brownfield) | skipped | skipped | full LOCATE_MAP | full LOCATE_MAP |

> **Codebase state detection**: Pipeline Entry checks `src/` (or the project's source root) for existing source files (`.py`/`.ts`/`.go`/`.rs`). If none exist → `[GREENFIELD]`: Node 2/3 produce summary output only (no detailed LOCATE_MAP — every file is NEW). If files exist → `[BROWNFIELD]`: Node 2/3 run full decomposition and location (existing code must be located, insertion points verified). The routing complexity level (C0-C2) is unchanged — greenfield/brownfield only affects Node 2/3 report depth within the chosen level.

### Risk escalation

When a change involves any of the following risk/environment flags, **regardless of file count, the minimum level is C1b** (run full planning+implementation+verification; the C0/C1a lightweight paths are not allowed):

| Flag | Trigger condition | Minimum level |
|:---|:---|:---|
| FINANCE | Amounts/billing/price calculations | C1b |
| AUTH | Authentication/authorization/encryption | C1b |
| MIGRATION | Data migration (DDL/data backfill) | C1b |
| STATE_MACHINE | State machine transitions | C1b |
| EXTERNAL_API | External API integration | C1b |
| ENV_OPS | Service startup/keep-alive/process management (background execution, daemon, restart policies) | C1b |

Executed together with ADAPTIVE's "non-degradable baseline": even when the environment lacks tools, risk/environment tasks only allow alternative-verification degradation — the routing level may never fall back to C0/C1a.

## 3. Flow

### Phase 0: Pre-flight initialization

Before any planning or execution, run this three-step bootstrap on every `/auto_coding` invocation:

1. **Check openspec readiness**:
   - `openspec/config.yaml` exists → ✓ ready (openspec is initialized)
   - Missing → run `openspec init --tools claude` (non-interactive, creates `openspec/config.yaml` + `.claude/` integration)
   - `openspec` CLI unavailable → mark `[NO_OPENSPEC: CLI_MISSING]`, skip to step 2

2. **Ensure `openspec/changes/` exists**:
   - Directory exists (even if empty) → ✓
   - Missing after init → `mkdir -p openspec/changes/`

3. **Ensure `ai_pipeline/` exists**:
   - Directory exists → ✓
   - Missing → `mkdir -p ai_pipeline/`

This guarantees: even when openspec is completely absent, the `ai_pipeline/` directory exists for the `[NO_OPENSPEC]` fallback to write `PROJECT_SPEC.md`. When openspec is available, `openspec init` runs automatically so the standard flow always works.

### Phase A: OpenSpec planning

**Entry detection**: after pre-flight initialization, if openspec is available (`openspec/config.yaml` exists and CLI is functional) → standard OpenSpec planning (flow below); otherwise → enter `[NO_OPENSPEC]` lightweight planning mode (see below), marked `[NO_OPENSPEC]` throughout.

```
Requirements take shape → grill-me (independent, not embedded in explore)
      ↓
/opsx:propose <change-name>     # Create the change; tasks.md includes fileHint+symbolHint+dependsOn
      ↓                           # spec interface contracts forbid any/object/unknown types
/opsx:update <change-name>      # Revise as needed
```

**Lightweight planning mode `[NO_OPENSPEC]`** (replaces Phases A/B when there is no openspec repo):
- Produce `ai_pipeline/PROJECT_SPEC.md`: a single file merging requirements / interface contract / edge conditions / tasks; task entries use the same format as OpenSpec tasks.md (fileHint + symbolHint + dependsOn), and contracts forbid any/object/unknown types.
- Node 2's input, Node 4's L2 contract baseline, and Node 6's verification baseline all use `PROJECT_SPEC.md` (replacing openspec artifacts).
- Handoff instruction: `"Implement via the three-layer pipeline: ai_pipeline/PROJECT_SPEC.md"`.
- Phase D's sync/archive are skipped, marked `[NO_OPENSPEC: SKIP_SYNC]`; RUN_LOG / ERROR_MEMORY / TECH_NOTES are kept.

### Phase B: handoff

The user sends `"Implement via the three-layer pipeline: openspec/changes/<name>/"`

or: `/opsx:apply` detects that Pipeline is available → automatically suggests delegation → user confirms → outputs the bridge instruction

### Phase C: Pipeline execution

```
Entry: create ai_pipeline/ + detect planning artifacts (if openspec/ exists → read OpenSpec artifacts; otherwise read PROJECT_SPEC.md, marked [NO_OPENSPEC]) + read ERROR_MEMORY (last errors)
  → adapt: has mypy → run type checks / has pytest → run coverage / has CI → align thresholds

Node 2: engineering decomposition → TASK_PLAN.md (planning artifacts' tasks+specs or PROJECT_SPEC → atomic tasks + topological order)
       → append to RUN_LOG when done
Node 3: precise location → LOCATE_MAP.md (consumes TASK_PLAN)
       → append to RUN_LOG when done
Node 4: code implementation → IMPLEMENTATION_REPORT.md (Ponytail full + Layer 0/1/2 three-layer self-checks)
       per task → append to RUN_LOG + ERROR_MEMORY
Node 5: static verification → VERIFY_REPORT.md → append to RUN_LOG
Node 6: runtime verification → VERIFY_RUNTIME_REPORT.md → append to RUN_LOG
Node 8: semantic commit → Git Commit → generate TECH_NOTES from RUN_LOG → update PIPELINE_STATUS
```

### Phase C→D automatic advancement

After Pipeline Node 8's commit completes, the **end of PIPELINE_SUMMARY must print**:

> "Phase C complete. Code committed. Continue to Phase D?
>   'sync' → merge delta specs into the main specs + git commit
>   'archive' → archive the change
>   'all' → one-shot sync+archive
>   'later' → manually later"

The Pipeline must not end silently — it must actively advance to Phase D.

### Phase D: OpenSpec wrap-up

```
/opsx:sync <change-name>       # delta→main specs, show the sync summary
      ↓                           # git add openspec/specs/ && git commit
/opsx:archive <change-name>    # archive to archive/
```

**C1a variant (Phase D-lite)**: C1a creates no change and does no sync/archive; it only appends the "interface contract" section of CHANGE_NOTES to the main spec, then git commits (see C1a contract sync).

`[NO_OPENSPEC]` mode skips Phase D (no main specs to sync/archive) and wraps up directly after Node 8.

### Breakpoint recovery

On the next `/auto_coding` invocation, first read `ai_pipeline/RUN_LOG.md`:
- Exists and Phase C complete → advance directly to Phase D
- Exists and Phase C partially complete → continue from the breakpoint node
- Does not exist → start from Phase A

## 3. Conflict rulings (4 rules)

### R1: Requirement existence
**Trigger**: Ponytail judges a feature redundant, but OpenSpec has confirmed it
**Ruling**: **OpenSpec wins**. Ponytail full accepts the requirement and implements it with the least code

### R2: Code reuse
**Trigger**: Ponytail finds an existing implementation that Pipeline did not
**Ruling**: **Ponytail wins**. Reuse it; mark the corresponding TASK as `REUSED` — keep it in TASK_PLAN for traceability, do not implement or delete it

### R6: Design defect
**Trigger**: implementation reveals the spec is incomplete
**Ruling**: **OpenSpec wins**. Roll back + output a defect report + re-run after the user updates
**Grading**: Critical (structural → must fall back) / Standard (omission → fall back after completion) / Advisory (optimizable → record as known issue)

### R8: tasks.md unchecked
**Trigger**: tasks.md checkboxes are unchecked at archive time
**Preventive measures (two checkpoints)**:
- Node 4: after each task completes, check the corresponding item in tasks.md per openspec_ref; REUSED tasks are checked too, annotated `<!-- reused: source -->` (see IMPLEMENT Step 5)
- Node 8: run a tasks.md completion check before committing (see COMMIT Step 6), comparing against IMPLEMENTATION_REPORT to check off completed tasks
**Ruling**: **facts first**.
- If items remain unchecked after both checkpoints but the work is factually complete → check them automatically before archive, no warning
- Tasks genuinely incomplete (skipped/not implemented) → archive is not blocked; a warning is allowed through (REUSED counts as complete, not incomplete)
- When the CLI pops "incomplete task(s). Continue?" and the work is factually complete, answer y to continue

## 4. Continuous sedimentation

Write immediately after each job, never batch-generated at the end.

**Append-only files** (use Append Protocol — see pipeline/SKILL.md §0): read existing → combine old + new → write. Never Write directly without reading first; the Write tool overwrites by default, and overwriting loses all prior entries.

- **RUN_LOG.md** (`ai_pipeline/`): prepend entry after each task/node (newest first; timestamp + node/task + content). Crash-safe.
- **ERROR_MEMORY.md** (`ai_pipeline/`): append entry after each self-heal/Critical/⚠️ (oldest first). Accumulates across runs.

**Per-run files** (overwrite on each new pipeline run is correct): TASK_PLAN.md, LOCATE_MAP.md, IMPLEMENTATION_REPORT.md, VERIFY_REPORT.md, VERIFY_RUNTIME_REPORT.md, COMMIT_MESSAGE.md, PIPELINE_STATUS.md.

- **TECH_NOTES.md** (`ai_pipeline/`): generated from RUN_LOG when the pipeline ends (§1 ADR + §2 known issues)

## 5. Deliverables

| Phase | Files |
|:---|:---|
| A | `openspec/changes/<name>/` (4 artifacts); `[NO_OPENSPEC]` mode: `ai_pipeline/PROJECT_SPEC.md` |
| C1a | `ai_pipeline/CHANGE_NOTES.md` (1 append-only file: planning/implementation/self-check/commit/contract sync); append `ERROR_MEMORY.md` on errors |
| C | `ai_pipeline/RUN_LOG.md`, `ERROR_MEMORY.md` |
| C | `ai_pipeline/LOCATE_MAP.md`, `TASK_PLAN.md` |
| C | `ai_pipeline/IMPLEMENTATION_REPORT.md` |
| C | `ai_pipeline/VERIFY_REPORT.md`, `VERIFY_RUNTIME_REPORT.md` |
| C | `ai_pipeline/TECH_NOTES.md` |
| C | `COMMIT_MESSAGE.md` + Git Commit |
| D | Updated `openspec/specs/**/*.md` + git commit |

## 6. Usage

```
/opsx:explore <topic>
/opsx:propose <name>

"Implement via the three-layer pipeline: openspec/changes/<name>/"

/opsx:sync <name> && git commit specs
/opsx:archive <name>
```

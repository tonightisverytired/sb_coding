---
name: 6-stage-pipeline
description: 6-stage engineering pipeline — from engineering decomposition to code commit. Runs in parallel with OpenSpec: OpenSpec handles business planning (explore/propose/sync), Pipeline handles engineering decomposition + code implementation + quality gates + delivery. Starts from Node 2 (atomic decomposition) and directly consumes OpenSpec artifacts. Ponytail full mode is active throughout Node 4.
---

# 5-stage engineering pipeline

## 0. Append Protocol

Two files are **append-only** and must never be overwritten:

| File | Append trigger | Direction |
|:---|:---|:---|
| `ai_pipeline/RUN_LOG.md` | After every task/node completes | Prepend (newest first) |
| `ai_pipeline/ERROR_MEMORY.md` | After every self-heal / Critical / ⚠️ / [BLOCKED] | Append (oldest first) |

All other pipeline files (`TASK_PLAN.md`, `LOCATE_MAP.md`, `IMPLEMENTATION_REPORT.md`, `VERIFY_REPORT.md`, `VERIFY_RUNTIME_REPORT.md`, `COMMIT_MESSAGE.md`, `PIPELINE_STATUS.md`, `TECH_NOTES.md`) are **per-run** — overwriting them on a new pipeline run is correct.

### Append procedure (mandatory for append-only files)

1. **Read** the existing file. If it doesn't exist yet, start with an empty string `""`.
2. **Build** the new entry with the standard format:
   ```markdown
   ## <ISO timestamp> — <node/task identifier>
   
   <content>
   
   ---
   ```
3. **Combine** old and new content:
   - `RUN_LOG.md`: `new_entry + "\n" + old_content` (prepend — newest entries first)
   - `ERROR_MEMORY.md`: `old_content + "\n" + new_entry` (append — chronological order)
4. **Write** the combined content with the Write tool.
5. **Verify**: the file must now contain both the new entry and all prior entries. If old entries are missing, the write was an overwrite — restore from the read in step 1 and redo.

**Bash shortcut** (replaces steps 1+3+4; works in any environment, no Python required):

```bash
# Prepend to RUN_LOG (newest first):
content="## $(date -Iseconds) Node N complete\\n- details here\\n"
printf '%s\\n\\n%s' "$content" "$(cat file.md 2>/dev/null)" > file.md

# Append to ERROR_MEMORY (chronological):
printf '%s\\n\\n%s' "$(cat file.md 2>/dev/null)" "$content" > file.md
```

For multi-line content, use a variable with embedded newlines or a temp file. The manual Read→Concat→Write protocol (steps 1-4) remains the authoritative fallback.

### Crash-safe guarantee

Write immediately after each trigger event — never batch multiple entries in memory. If the agent crashes before writing, at most one entry is lost. Do NOT accumulate entries and write them at the end of a node; that defeats the purpose of crash-safe sedimentation.

---

## 1. Pipeline overview

This pipeline covers the engineering execution stages "from code location to commit". **Requirement understanding and task decomposition are handled by OpenSpec**, and the Pipeline does not duplicate that work.

```
OpenSpec (planning)                        Pipeline (execution)
─────────────────              ──────────────────────────────
explore → propose → update     Node 2→Node 3→Node 4→Node 5→Node 6→Node 8
                                     (+Ponytail full)
```

**Differences from the old 8-stage version**:
- Stage 0 (project awareness) removed — OpenSpec propose already did it
- Node 1 (requirement structuring) removed — OpenSpec specs already define interface contracts
- Node 2 (engineering decomposition) → kept but repositioned: engineering-level atomic decomposition from OpenSpec tasks+specs, not requirement understanding
- Node 7 (knowledge sedimentation) → changed to continuous immediate sedimentation (RUN_LOG + TECH_NOTES), no longer a standalone node

## 2. Automatic template matching

When starting the pipeline, the AI automatically detects the project root's flag files:
- `pyproject.toml` + `src/` → Python (mypy / ruff / pytest)
- `package.json` + `tsconfig.json` → TypeScript (tsc / eslint / jest)
- `go.mod` → Go (go vet / go test; gofmt -l instead of a built-in linter)
- `Cargo.toml` → Rust (cargo check / clippy / cargo test)
- No flag files → generic template `[CUSTOM_TOOLCHAIN]`: map an equivalent toolchain for "compile/static check → lint → test" without halting to ask; the user can override
- Multiple flag files at once → ask the user to choose

## 3. Pipeline overview

```
[user triggers + OpenSpec change directory path]
        ↓
┌──────────────────────────────────────────────────────────────┐
│ Entry: create ai_pipeline/ + read the planning artifacts      │
│       (OpenSpec/[NO_OPENSPEC]) + ERROR_MEMORY                │
└──────────────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────────────────────┐
│ Node 2 (Skill-02): engineering decomposition → TASK_PLAN.md  │
│   Decompose the planning artifacts (tasks+specs or PROJECT_SPEC)│
│   into atomic tasks + topological order                      │
└──────────────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────────────────────┐
│ Node 3 (Skill-03): precise location → LOCATE_MAP.md           │
└──────────────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────────────────────┐
│ Node 4 (Skill-04): code implementation → IMPLEMENTATION_REPORT.md │
│   Ponytail full mode + L0/L1/L2 three-layer self-check        │
│   L2 contract baseline = OpenSpec specs/*.md or PROJECT_SPEC.md │
└──────────────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────────────────────┐
│ Node 5 (Skill-05): static verification → VERIFY_REPORT.md    │
│   Critical (mypy) + Standard (ruff)                          │
└──────────────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────────────────────┐
│ Node 6 (Skill-06): runtime verification → VERIFY_RUNTIME_REPORT.md │
│   Mode A (pytest) / Mode B (Eval) / Mode C (combined)         │
└──────────────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────────────────────┐
│ Node 8 (Skill-08): semantic commit → Git Commit              │
└──────────────────────────────────────────────────────────────┘
        ↓
    🎉 Delivery complete
```

## 4. Node details

### Entry: lightweight startup

- **Actions**:
  1. Create the `ai_pipeline/` directory (if missing)
  2. Detect planning artifacts: if `openspec/changes/<name>/` exists → read the 4 artifacts + `openspec status --json` for actionContext; if not → read `ai_pipeline/PROJECT_SPEC.md`, annotated `[NO_OPENSPEC]`
  3. Read `ai_pipeline/ERROR_MEMORY.md` (if present) and extract known error patterns
  4. Adaptation decision: has mypy → run type checks / has pytest → run coverage / has CI → align thresholds
  5. **Tool availability check** — output a `[TOOL_CHECK]` matrix listing every tool that *could* be used in this pipeline run and its status. This ensures tools are not forgotten; the model must reference this matrix before each node starts. Format:
     ```
     [TOOL_CHECK] contract check: _contract_check.py available ✅ (Python template)
     [TOOL_CHECK] bash append shortcut: available ✅
     [TOOL_CHECK] layer-level mypy: enforced at Node 4 ✅
     [TOOL_CHECK] escape-hatch detection: active (Node 4→5)
     ```
     If a tool is unavailable (wrong template, missing dependency), mark `⚠️ degraded` with the fallback. For non-Python templates, `_contract_check.py` shows `⚠️ skipped (not Python template)`.
  6. **Session state check** — read `ai_pipeline/SESSION_STATE.json` (if exists; schema: `pipeline/_session_state_schema.json`). If non-empty, print the `resume_hint` (if present) and prompt: "⚠️ Detected incomplete pipeline from previous session. Last state: <current_node>/<current_task> (file: <current_file>, self-heal round <self_heal_round>/3). Resume? Reply 'resume' to continue from breakpoint, or 'restart' to start fresh." This replaces the implicit breakpoint recovery in SKILL.md §Breakpoint recovery with an explicit, data-backed prompt.
  7. **Risk flag redeclaration** — extract risk flags from planning artifacts and print: `[RISK_FLAGS_ACTIVE] <flags>`. These flags persist in context throughout the pipeline; each node that performs flag-specific checks (Node 4: FINANCE→Decimal, Node 5: AUTH→type check, Node 6: ENV_OPS→environment verify) must reference this declaration before executing.
  7b. **Codebase state detection** — check if the project source root (default `src/`) contains any existing source files: `ls src/**/*.py 2>/dev/null | head -1` (adjust extension per template). If no source files exist → `[GREENFIELD]`: every task is a NEW_FILE, Node 2/3 will run in summary mode (TASK_PLAN with minimal file paths, LOCATE_MAP as a one-liner). If source files exist → `[BROWNFIELD]`: Node 2 must identify which tasks are ADD/MODIFY/DELETE/REUSE, Node 3 must locate exact insertion points in existing code. Print: `[CODEBASE] greenfield — no existing source files detected` or `[CODEBASE] brownfield — N existing source files found`.
  8. **Route audit** — print the routing decision: `[ROUTE] <C0|C1a|C1b|C2> selected: <N> files, <M> new capabilities, risk flags: <list>. Greenfield/Brownfield: <empty|existing>.` Write this line to RUN_LOG for post-hoc auditability.
  9. Create `PIPELINE_STATUS.md` (overwrite — per-run file). Create/update `RUN_LOG.md` using **Append Protocol §0**: read existing → if RUN_LOG already exists from a prior run, prepend a new run header `# Pipeline Run — <ISO timestamp>` → write combined.
- **Outputs**: `ai_pipeline/PIPELINE_STATUS.md` + `ai_pipeline/RUN_LOG.md` (appended)

### Node 2: engineering-level atomic decomposition (Skill-02)

- **Input**: OpenSpec tasks.md + specs/*.md + design.md (`[NO_OPENSPEC]` mode: PROJECT_SPEC.md)
- **Execution**: atomize the functional tasks and interface specs from OpenSpec — the smallest unit is per-file/per-function, with a dependency graph and topological order
- **Output**: `TASK_PLAN.md`
- **Gate**: atomicity red line (single file/single function, no vague descriptions)
- **Immediate sedimentation**: read RUN_LOG.md → prepend entry → write (Append Protocol §0)

### Node 3: precise code location (Skill-03)

- **Input**: OpenSpec tasks.md (with fileHint + symbolHint + dependsOn) + SPEC context
- **Execution**: five-step location method (script-assisted), mapping each task to absolute paths, function names, and line ranges
- **Output**: `LOCATE_MAP.md` (suggested ≤30K tokens; a soft suggestion under the current 200K context)
- **Gate**: uniqueness red line (no same-name file/function conflicts)
- **Immediate sedimentation**: read RUN_LOG.md → prepend location summary entry → write (Append Protocol §0)

### Node 4: deterministic code implementation (Skill-04)

- **Input**: LOCATE_MAP.md + OpenSpec specs (as the L2 contract baseline)
- **Execution**: execute each task in topological order with Ponytail full mode active. After each task, run the L0(import)→L1(assert)→L2(contract) three-layer self-check
- **L2 baseline**: the interface contracts in `openspec/changes/<name>/specs/<capability>/spec.md` (`[NO_OPENSPEC]` mode: the "interface contract" section of PROJECT_SPEC.md)
- **Output**: modified source files + `IMPLEMENTATION_REPORT.md`
- **Gate**: immediate compile check (mypy --strict or tsc --noEmit), up to 3 self-heal rounds
- **Immediate sedimentation**: after each task completes → read RUN_LOG.md → prepend task entry → write; on self-heal/error → read ERROR_MEMORY.md → append error entry → write (Append Protocol §0)

### Node 5: hard static gate (Skill-05)

- **Input**: the list of modified source files
- **Execution**: Critical (type check; failure → halt + rollback) + Standard (lint; AI self-heal ≤3 rounds)
- **Output**: `VERIFY_REPORT.md`
- **Immediate sedimentation**: read RUN_LOG.md → prepend gate result entry → write; on error → read ERROR_MEMORY.md → append error entry → write (Append Protocol §0)

### Node 6: configurable runtime verification (Skill-06)

- **Input**: files that passed static verification + the edge conditions in OpenSpec specs (`[NO_OPENSPEC]` mode: the "edge conditions" section of PROJECT_SPEC.md)
- **Execution**: Mode A (test coverage) / Mode B (Eval baseline) / Mode C (combined), three-level threshold ruling
- **Output**: `VERIFY_RUNTIME_REPORT.md`
- **Immediate sedimentation**: read RUN_LOG.md → prepend runtime result entry → write; on ⚠️ → read ERROR_MEMORY.md → append warning entry → write (Append Protocol §0)

### Node 8: semantic commit (Skill-08)

- **Input**: final source code + RUN_LOG
- **Execution**: generate Conventional Commits → pre-commit red lines → git commit
- **Output**: `COMMIT_MESSAGE.md` + Git Commit
- **Wrap-up sedimentation**: read `RUN_LOG.md` (built via Append Protocol §0) → generate `TECH_NOTES.md` (§1 implementation decisions + §2 known issues) → update `PIPELINE_STATUS.md`

---

## 5. Continuous immediate sedimentation

During Pipeline execution, `ai_pipeline/RUN_LOG.md` and `ai_pipeline/ERROR_MEMORY.md` are updated immediately after every task via the **Append Protocol §0** — never batch-generated at the end and never overwritten.

- **RUN_LOG.md**: one entry prepended after each task/node (timestamp + source + content). Crash-safe — write immediately, not at node end.
- **ERROR_MEMORY.md**: one entry appended immediately after every self-heal/Critical/⚠️/[BLOCKED]. Accumulates across runs; the next Pipeline entry reads it.
- **TECH_NOTES.md**: generated from RUN_LOG when the pipeline ends (§1 ADR + §2 known issues), as supplementary project knowledge.

---

## 6. Deliverables list

- Modified source code (committed)
- `ai_pipeline/RUN_LOG.md` (continuous sedimentation)
- `ai_pipeline/ERROR_MEMORY.md` (cross-run error accumulation)
- `ai_pipeline/TASK_PLAN.md` (Node 2, atomic tasks + topological order)
- `ai_pipeline/LOCATE_MAP.md`
- `ai_pipeline/IMPLEMENTATION_REPORT.md`
- `ai_pipeline/VERIFY_REPORT.md`
- `ai_pipeline/VERIFY_RUNTIME_REPORT.md`
- `ai_pipeline/TECH_NOTES.md`
- `COMMIT_MESSAGE.md`

## 7. Key constraints

- **Never guess semantics**: when file names, module names, or code intent are uncertain, pause and ask the user
- **Never leave placeholders**: no TODO or "to be filled" in deliverables
- **Read before writing**: understand the project's existing architecture and code style before modifying code
- **Immediate sedimentation**: write to RUN_LOG immediately after each task/node, not at the end of the pipeline

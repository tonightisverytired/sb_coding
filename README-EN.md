# sb_coding

A parallel development system for AI coding assistants: **OpenSpec (business planning) + Pipeline (engineering execution) + Ponytail (code minimization)**. Each component plays to its strengths without overlapping: changes are routed automatically by complexity, and the system continuously accumulates experience while working.

## Architecture

```
OpenSpec (planning) + grill-me (decisions)   Pipeline (execution) + Ponytail (implementation)
──────────────────────────────────────       ───────────────────────────────────────────────
grill-me → explore → propose → update        Node 2 (decompose) → Node 3 (locate) → Node 4 (implement) → Node 5 (verify) → Node 6 (runtime) → Node 8 (commit)
              ↓                                    ↑
         sync → archive                    Ponytail full + RUN_LOG/ERROR_MEMORY throughout
```

**Key design**: grill-me runs independently during planning (triggered when >2 decisions for C1b, >3 for C2), questioning every branch of the decision tree until shared understanding. OpenSpec and Pipeline do not overlap — once OpenSpec finishes planning, Pipeline consumes OpenSpec artifacts directly, starting from engineering decomposition and location — no duplicated requirement analysis or task breakdown.

## Component responsibilities

| Component | Responsibility | Core capabilities |
|:---|:---|:---|
| **OpenSpec** | Business planning | `explore`, `propose` (create change + artifacts), `update`, `sync` (incremental spec management), `archive` |
| **Pipeline** | Engineering execution | Node 2 (atomic decomposition) → Node 3 (precise location) → Node 4 (implementation + 3-layer self-check) → Node 5/6 (quality gates) → Node 8 (semantic commit) |
| **Ponytail** | Code minimization | Ladder framework (reuse → stdlib → native → one-liner → minimal), over-engineering review, tech-debt tracking |
| **grill-me** | Design stress test | Questions every branch of a plan until shared understanding; used for key decisions |
| **adaptive** | Toolchain adaptation | Chooses the verification strategy from the project's existing tools; interrupts with install hints when configured tools are missing, degrades only when unconfigured |

## Directory structure

```
├── SKILL.md                  # Top-level skill: entry, routing rules, conflict rulings
├── adaptive/                 # Toolchain adaptation and non-degradable verification baseline
├── ai_pipeline/              # Runtime artifacts and continuous sedimentation (RUN_LOG / ERROR_MEMORY / TECH_NOTES / VERIFY, etc.)
├── grill-me/                 # Design stress-test skill
├── openspec/
│   ├── commands/opsx/        # explore / propose / update / sync / archive / apply commands
│   └── skills/               # Skill implementations behind each OpenSpec command
├── pipeline/
│   ├── SKILL.md              # 6-stage engineering pipeline overview
│   ├── CONFIG.md             # Single source of truth for default thresholds
│   ├── _contract_check.py    # Automated contract checking — Python only (AST; type signatures + Gherkin fallback, namespace-aware)
│   ├── _session_state_schema.json  # SESSION_STATE.json reference schema for cross-session recovery
│   └── breakdown|locate|implement|verify|simulator_verify|commit|settle   # Node skills
├── ponytail_code/
│   └── exported-skills/      # ponytail full / audit / debt / gain / help / review sub-skills
└── self_verify/              # Three-layer self-check protocol for code (L0/L1/L2)
```

## Routing by complexity

The first step is to judge the complexity of a change. The principle: **don't do work that isn't worth doing**.

| Level | When | Path |
|:---|:---|:---|
| **C0** | Single-file / single-function change (typo, small bugfix) | Write code directly + Layer 0/1 self-check + commit |
| **C1a** | Small multi-file change (2-3 files, single module, no risk flags) | One lightweight `CHANGE_NOTES.md` plan → implement → test → Phase D-lite contract sync |
| **C1b** | Multi-file / cross-module change (4-10 files, or risk flags) | `propose` → implement → test → commit |
| **C2** | Large platform / subsystem | grill-me (if >3 decisions) → full pipeline → all nodes + full sedimentation |

Changes touching any of the **FINANCE / AUTH / MIGRATION / STATE_MACHINE / EXTERNAL_API / ENV_OPS** risk or environment flags are upgraded to at least **C1b** regardless of file count, and must satisfy the corresponding non-degradable verification baseline.

**Codebase state detection**: Pipeline Entry checks the project source root for existing source files. If none exist → `[GREENFIELD]`: Node 2/3 run in summary mode (every task is a new file, no existing code to locate). If files exist → `[BROWNFIELD]`: Node 2/3 run full decomposition and precise location (MODIFY tasks need exact insertion points, REUSE opportunities must be identified). The C0-C2 complexity level is unchanged — greenfield/brownfield only affects Node 2/3 report depth.

## Workflow

1. **Phase A — Planning**: `explore` / `propose` produce change artifacts (requirements, interface contracts, tasks, design). Without an openspec repo, this falls back to the single-file lightweight plan `ai_pipeline/PROJECT_SPEC.md`.
2. **Phase B — Handoff**: hand the planning artifacts to the Pipeline.
3. **Phase C — Execution**: Node 2 atomic decomposition → Node 3 precise location → Node 4 implementation (Ponytail full + L0/L1/L2 self-checks) → Node 5 static verification → Node 6 runtime verification → Node 8 semantic commit.
4. **Phase D — Wrap-up**: `sync` merges delta specs into the main specs; `archive` archives the change.

Breakpoint recovery: on the next invocation, `ai_pipeline/SESSION_STATE.json` is read first (schema: `pipeline/_session_state_schema.json`). If non-empty, the Entry step prints the exact breakpoint — which node, which task, which file, which self-heal round — and prompts for resume or restart. Node 4 updates SESSION_STATE before each task and after each self-heal round; Node 5/6 update it on entry; Node 8 clears it on completion. This replaces the implicit RUN_LOG-based recovery with explicit, data-backed state tracking.

## Usage

```text
/opsx:explore <topic>                                  # Explore requirements
/opsx:propose <name>                                   # Create a change (tasks + specs + design)

"Implement via the three-layer pipeline: openspec/changes/<name>/"   # Hand off to Pipeline

/opsx:sync <name> && git commit specs                  # Merge delta into main specs
/opsx:archive <name>                                   # Archive the change
```

## Environment constraints

The skill pack assumes a minimal baseline. Missing tools trigger either a guided install prompt or a documented degradation — no silent failures.

| Dependency | Required? | Role | Degradation if missing |
|:---|:---|:---|:---|
| **bash** (POSIX sh) | Required | Pipeline commands, `printf`-based append shortcut | None — bash is the execution environment |
| **git** | Required (Node 8) | Semantic commit | `[SKIP_COMMIT: git unavailable]` — code is written but not committed |
| **openspec CLI** | Optional | Phase A planning, Phase D sync/archive | `[NO_OPENSPEC]` mode — falls back to `ai_pipeline/PROJECT_SPEC.md` single-file planning; Phase D skipped |
| **Python 3.10+** | Template-dependent | `_contract_check.py` (AST parsing), mypy, ruff, pytest | Non-Python projects: contract check degrades to manual L2 checklist. Python projects without mypy/ruff/pytest: ADAPTIVE rules apply (install prompt if configured, degrade if unconfigured) |
| **mypy** | Python template | Node 4/5 type checking | `[SKIP_TYPE_CHECK: no config]` — degrades to IDE diagnostics + AI review (only if project has no mypy config; if configured but missing → install prompt and halt) |
| **ruff** | Python template | Node 5 lint | `[SKIP_LINT: no config]` — degrades to AI code review |
| **pytest** | Python template | Node 6 runtime verification | `[SKIP_COVERAGE: no framework]` — degrades to Ponytail self-check + manual acceptance |
| **TypeScript toolchain** (tsc/eslint/jest) | TS template | Node 4/5/6 equivalents | Same ADAPTIVE degradation rules as Python tools |

**Cross-platform**: All pipeline scripts use POSIX sh syntax (tested on Windows via Git Bash). `_contract_check.py` requires Python 3.10+ for AST `ast.unparse` and `match` statement support. Paths use forward slashes throughout.

## Quality assurance

- **Three-layer self-check (L0/L1/L2)**: syntax/import → behavioral self-check (assert/demo) → interface-contract comparison.
- **Hard gates**: type checking (Critical; failure interrupts and rolls back), lint (Standard; up to 3 self-heal rounds), runtime coverage (default ≥80% line, ≥70% branch).
- **Layer-level mypy checkpoint** (Node 4): after each topological layer of tasks completes, type-check all files written so far — catches cross-file type errors that per-file checks miss. Errors must be fixed before the next layer; they must never reach Node 5.
- **Escape-hatch detection** (Node 4→Node 5): if a self-heal "passes" by using `Any`, `# type: ignore`, or `cast()` as a last-resort workaround, it is recorded in ERROR_MEMORY with the `[ESCAPE_HATCH]` tag. Node 5's Critical gate scans for these markers and flags them for human review — not blocking, but tracked as quality debt.
- **Continuous sedimentation**: `RUN_LOG.md` is appended after every task (crash-safe), `ERROR_MEMORY.md` accumulates errors across runs, and `TECH_NOTES.md` records ADRs and known issues. A `printf`-based bash one-liner (in `pipeline/SKILL.md` §0) performs atomic prepend/append for append-only files, replacing the manual three-step protocol — no Python required.
- **Automated contract checking** (`pipeline/_contract_check.py`, Python template only): compares interface contracts from spec files against actual code signatures via AST. Two parsing modes: type-signature contracts from `PROJECT_SPEC.md`-style specs, and Gherkin endpoint extraction (`WHEN POST /path`) as a fallback for OpenSpec-format specs. Namespace-aware: methods under a class header are automatically prefixed (e.g. `TransactionService.authorize`), eliminating false positives from same-named methods in different classes. For non-Python projects, the manual L2 contract comparison checklist in `self_verify/SELF_VERIFY.md` remains the authoritative method.
- **Conflict rulings**: requirement existence defers to OpenSpec; code reuse defers to Ponytail; incomplete specs trigger a rollback plus a defect report.
- **Cross-session recovery** (`ai_pipeline/SESSION_STATE.json`): tracks in-progress pipeline state — current node, task, file, and self-heal round — across session boundaries. Five write points (Node 4 per-task + per-heal, Node 5 entry, Node 6 entry, Node 8 clear) ensure that if a session is interrupted, the next session knows exactly where to resume. Schema: `pipeline/_session_state_schema.json`.
- **Greenfield/brownfield routing**: Pipeline Entry detects whether the project has existing source code and adjusts Node 2/3 depth accordingly. Greenfield projects (no existing files) get summary TASK_PLAN and a one-line LOCATE_MAP — no time wasted locating code that doesn't exist. Brownfield projects (existing codebase) get full decomposition with exact line ranges, context code blocks, and conflict checks.
- **Tool awareness mechanism** (`[TOOL_CHECK]` matrix): Pipeline Entry outputs a matrix of every tool available for this run and its status. Each node references this matrix before starting, ensuring tools (`_contract_check.py`, bash append shortcut, layer-level mypy) are actively used rather than passively documented.
- **Risk flag redeclaration** (`[RISK_FLAGS_ACTIVE]`): risk flags declared in Phase A are re-declared at Pipeline Entry and printed before each flag-specific check (Node 4: FINANCE→Decimal enforced, Node 5: AUTH→type check mandatory). Prevents flags from being forgotten mid-pipeline.
- **Integration test transparency** (Node 6): coverage reports include a breakdown of unit-test files vs. integration-test files (identified by `test_api*.py` naming or `TestClient` imports). Thresholds are unchanged; the breakdown is informational.
- **OpenSpec CLI integration verified**: the full Phase A→B→C→D handoff contract has been validated via a mock OpenSpec environment at the project root. Four checkpoints confirmed: Entry detection of `openspec/config.yaml`, artifact consumption from `openspec/changes/<name>/`, Phase D delta→main spec sync, and archive. All sandboxes also support `[NO_OPENSPEC]` fallback mode.
- **Self-verification**: the skill pack itself is verified against a document-level L0/L1/L2 protocol covering front-matter, link integrity, cross-document consistency, and contract alignment.
- **Verification matrix**: 10 test suites, 148 tests, all green — split across 6 sandboxes (C0 calculator, C1b auth, C1b apikey, C2 ecommerce + discount codes, C2 finance clearing, C2 inventory) and 4 local suites (C0 utils, C1b validator, C1b payment retry with circuit breaker, C2 task execution engine). Covers all 6 risk flags, greenfield and brownfield, and incremental modification of existing code.

---
name: verify-static-quality-gate
description: Pipeline Node 5 - hard static quality gate. Two-level red-line checks: Critical (mypy type check → block and roll back) + Standard (ruff lint → AI self-heal up to 3 rounds). Use when static quality control is needed after code implementation is complete.
---

# Hard Quality Gate

> Default thresholds use pipeline/CONFIG.md as the single source of truth; this document keeps numeric copies.

## 1. Skill overview
- **Stage**: Pipeline Node 5/8
- **Upstream dependencies**: the set of modified source files output by Node 4 + `IMPLEMENTATION_REPORT.md`
- **Downstream output**: `VERIFY_REPORT.md` (passed to Node 6, the configurable verification stage)
- **Core goal**: before code enters runtime verification, use the "two-level red lines" to kill all type errors, lint violations, and debug leftovers at the gate, ensuring code leaving this stage has at least the baseline quality of "type-safe and spec-compliant". The toolchain switches automatically by template.

## 2. Input schema
The AI must receive all of the following inputs:
| Input type           | Format requirement                                         | Required             |
| :----------------- | :----------------------------------------------- | :------------------- |
| List of modified source files | The file path list from `IMPLEMENTATION_REPORT.md` | **Required**             |
| Original context reference     | `LOCATE_MAP.md` (to understand code intent when assisting fixes)    | Recommended             |
| Project type-check configuration   | `pyproject.toml` / `tsconfig.json` (auto-detected by the AI) | **Required** |

## 3. Execution workflow

### Step 1: Determine the verification scope
- **SESSION_STATE update**: write `ai_pipeline/SESSION_STATE.json` with `current_node: "Node 5"`, `current_task: ""`, `self_heal_round: 0`.
- **AI action**: extract the **absolute path list** of all modified source files from `IMPLEMENTATION_REPORT.md`.
- **Deduplicate**: if one file was modified by multiple tasks, keep only one record.
- **Contract check gate**: verify that `IMPLEMENTATION_REPORT.md` contains a filled `Contract check:` field. If it is empty or missing and the project is a Python template → **reject the handoff**, send back to Node 4 to run `_contract_check.py` and fill the field. If `[SKIP_CONTRACT_CHECK: <valid reason>]` is present → accept. Valid reasons: not Python template, no spec file.

### Step 2: Phase one — Critical red-line check (blocking)
- **AI action**:
  1. Run `mypy --strict <modified file list>` (Python) or `tsc --noEmit` (TypeScript) in the terminal.
  2. Parse the output, catch fatal errors of type `error:`, and check whether key imports are missing.
- **AI decision (hard interrupt)**:
  - **If type errors exist**:
    - **Immediately terminate the entire Node 5**.
    - Output `CRITICAL_FAILURE_REPORT.md` listing all type errors.
    - **The AI is forbidden** from attempting fixes. Node 4 already had 3 self-heal opportunities — a type error found at Node 5 is a structural defect; further fixes would only introduce new problems.
    - Roll back all modified files with `git checkout -- <files>` and request developer intervention.
  - **If no type errors**: release to Step 2b.

### Step 2b: Escape-hatch audit (non-blocking quality gate)
- **AI action**: scan `ai_pipeline/ERROR_MEMORY.md` and the modified source files for `[ESCAPE_HATCH]` markers and `Any`/`# type: ignore`/`cast()` workarounds introduced during Node 4 self-heals.
- **Checklist**:
  1. Read ERROR_MEMORY → extract all `[ESCAPE_HATCH]` entries from this run.
  2. For each entry, locate the affected line in the source code and verify the workaround is still present.
  3. Classify each: `LOW_RISK` (e.g. decorator wrapper returning Any — contained scope), `MEDIUM_RISK` (e.g. `dict[str, Any]` in a public API boundary), `HIGH_RISK` (e.g. `# type: ignore` on a FINANCE calculation).
- **Ruling**: escape hatches do NOT block release — they are quality debt. They MUST be listed in VERIFY_REPORT.md under a new section "Escape-hatch inventory" with risk classification. HIGH_RISK items additionally get a warning in PIPELINE_SUMMARY.
- **Prevention feedback**: if the same file/module accumulates escape hatches across multiple runs, ERROR_MEMORY patterns should trigger a pre-emptive review before Node 4 starts on that module next time.

### Step 3: Phase two — Standard red-line check (self-heal level)
- **AI action**:
  1. Run `ruff check <modified file list>` (Python) or `eslint <modified file list>` (TypeScript) in the terminal.
  2. Additional checks: leftover `print()` / `breakpoint()` (Python), leftover `console.log` / `debugger` (TypeScript), unused variables, naming conventions.
- **AI self-heal loop (core logic)**:
  - At most 3 rounds. Each round: the AI reads the violation list → fixes each one with SearchReplace → re-runs ruff/eslint.
  - If still not fully passing after 3 rounds → mark the remaining violations `[MANUAL_REQUIRED]` and write them into the report.
  **Examples of AI fix strategies**:
  - Violation: `Line 12: Found debug print` → the AI deletes that line with SearchReplace.
  - Violation: `Variable 'UserName' is not in snake_case` → the AI renames it consistently within the project.
  - Violation: `'unused_import' is imported but never used` → the AI removes that import.

### Step 4: Generate the final verification report
- **Advisory ponytail-review** (optional, non-blocking): after Standard checks pass, invoke `ponytail-review` on the diff to scan for over-engineering in the current change (reinvented stdlib features, unnecessary dependencies, speculative abstractions). Findings are informational — append them to VERIFY_REPORT.md under "Ponytail review" but do NOT block the gate. If the review is skipped or the skill returns nothing, the pipeline proceeds normally.
- Aggregate the Critical results, Standard results, and self-heal loop logs into `VERIFY_REPORT.md`.

## 4. Output schema (VERIFY_REPORT.md template)

```markdown
# Code Verification Report - [requirement name] - [date]

## Overall conclusion: ✅ all passed / ⚠️ human review needed (Standard leftovers) / 🛑 fatal halt (Critical failure)

---

### 1. Critical red-line check (blocking)
| Check item                          | Status       | Details                     |
| :------------------------------ | :--------- | :----------------------- |
| Type check (mypy --strict)       | ✅ PASS     | No type errors               |
| Key import completeness              | ✅ PASS     | All core library references exist          |
| Interface contract consistency                  | ✅ PASS     | Return types match the SPECIFICATION |
| **Critical conclusion**               | **✅ Pass** | **Release to Standard check** |

(If it fails, the specific type error stack will be shown here, annotated `[BLOCKED]`)

---

### 2. Standard red-line check (standard-level self-heal)

#### Initial check results (round 1)
| File                | Line | Violation type       | Violation content               |
| :------------------ | :--- | :------------- | :--------------------- |
| auth_service.py     | 45   | debug-print    | `print(f"debug: {user}")` |
| auth_service.py     | 78   | naming         | variable `UserName` should be snake_case |
| task_executor.py    | 12   | unused-import  | `import os` is unused    |

#### AI auto-fix records
| Fix round | Fix action                                            | Status   |
| :------- | :-------------------------------------------------- | :----- |
| Round 1  | Deleted `print()` on line 45 of `auth_service.py`           | ✅ Success |
| Round 1  | Renamed `UserName` to `user_name` (affects 3 references) | ✅ Success |
| Round 1  | Removed the unused `import os` in `task_executor.py`      | ✅ Success |

#### Final Standard check results (round 2)
| Check item            | Status               | Remaining violations       |
| :---------------- | :----------------- | :--------------- |
| Ruff lint rules    | ✅ PASS             | 0                |
| Naming conventions          | ✅ PASS             | 0                |
| Debug code leftovers      | ✅ PASS             | 0                |
| **Standard conclusion** | **✅ all self-healed** | **no human intervention needed** |

---

### 3. Final gate status
- Critical phase: ✅ passed
- Standard phase: ✅ all self-healed (3 violations fixed in total, took 2 rounds)
- **Final ruling**: ✅ **allowed to leave for Node 6 (configurable verification)**
```

## 5. Exception handling strategy

- **Critical type/compile errors (fatal)**: the AI **never modifies source files on its own**; it immediately halts and outputs the complete type-check log, because type errors may involve structural refactoring and blind AI fixes could introduce more serious logic defects.
- **Standard violation fix conflicts**: if fixing one violation (e.g. renaming a variable) causes a new violation (e.g. broken references), the AI must detect and fix it in the next loop round. If a "fix A → produces B → fix B → produces A" infinite loop occurs within 3 rounds, the AI must force an exit, downgrade all related violations to `[MANUAL_REQUIRED]`, and highlight a warning in the report.
- **Verification timeout**: if `mypy` or `ruff` runs for more than 30 seconds, the AI judges the project too large, skips the full check, and runs only an incremental check on the modified files.
- **Template tools unavailable** (routed by the ADAPTIVE degradation rules, consistent with the entry decision):
  - The project has a type-check configuration but the tool is not installed → the AI shows the install command (e.g. `pip install mypy ruff`) and halts, without degrading or skipping; re-run this node after installation.
  - The project has no type-check configuration → degrade to IDE diagnostics + AI line-by-line review, annotated `[SKIP_TYPE_CHECK: no config]`. This is a degradation allowed by ADAPTIVE; it is not a node failure and does not halt.
  - The same applies to lint tools (ruff/eslint): configured but not installed → prompt installation and halt; no lint configuration → Standard degrades to AI code review, annotated `[SKIP_LINT: no config]`.

## 6. Successful exit criteria (gate pass condition)

- **The Critical red-line check has been executed and passed entirely (critical_passed == True)**.
- **The Standard red-line check has been executed**, with 0 remaining violations (if `[MANUAL_REQUIRED]` markers exist, they must be explicitly annotated in the report; that state does not count as a "successful exit" — whether to release should be decided by team norms; **this skill defines: the release precondition is no Critical errors; Standard may leave items as "pending human confirmation", but must explicitly warn**).
- `VERIFY_REPORT.md` has been generated and explicitly contains item-by-item conclusions for both Critical and Standard.
- If the self-heal loop was triggered, the report must contain a complete "before/after fix" comparison log.

**After passing this gate, pass the absolute path of VERIFY_REPORT.md, the list of modified source file paths, IMPLEMENTATION_REPORT.md (from Node 4), and the OpenSpec specs/*.md (for Node 6 comparison verification) to Node 6 (configurable verification stage).**

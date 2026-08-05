---
name: code-self-verification
description: Pipeline Node 4 code self-check protocol — after each task, run the L0(import)/L1(assert)/L2(contract) three-layer self-check; only when all three pass is the task marked complete
---

# Three-layer code self-check

> Default thresholds use pipeline/CONFIG.md as the single source of truth; this document keeps numeric copies.

Inside Pipeline Node 4, after each atomic task's code injection, the three-layer self-check must be executed. A task must not be marked complete, and must not proceed to Node 5, until all three layers pass.

---

## 1. Self-check flow

```
SearchReplace code injection
        │
        ▼
  ┌─────────────────────┐
  │ Layer 0: syntax/import│──FAIL(≤3 self-heals)──→ [BLOCKED: L0]
  └────────┬────────────┘
           │ PASS
           ▼
  ┌─────────────────────┐
  │ Layer 1: Ponytail   │──FAIL(≤3 self-heals)──→ [BLOCKED: L1]
  │         self-check  │
  └────────┬────────────┘
           │ PASS
           ▼
  ┌─────────────────────┐
  │ Layer 2: interface   │──FAIL(Critical)──→ triggers R6
  │         contract    │
  │         comparison  │
  └────────┬────────────┘
           │ PASS
           ▼
     Task Complete ✓
```

---

## 2. Layer 0: syntax and imports

| Property | Value |
|:---|:---|
| **Command** | Python: `python -c "from <pkg> import <symbol>"`; TS: `node -e "require('./dist/<file>')"` |
| **Timeout** | ≤ 5 seconds |
| **Pass criteria** | Exit code = 0, no ImportError / SyntaxError / ModuleNotFoundError |
| **Failure self-heal** | AI checks for typos / missing imports / circular imports → fixes → re-runs, up to 3 times |
| **Limit exceeded** | Mark `[BLOCKED: L0]`, skip this task and continue the others, then aggregate and request human intervention after all are done |
| **Skip condition** | Pure config files (.yaml/.json/.toml), pure docs (.md), no code changes |
| **Report format** | `Layer 0 (import): ✅ PASS / ❌ FAIL (attempt N)` |

---

## 3. Layer 1: Ponytail self-check execution

| Property | Value |
|:---|:---|
| **Command** | Chosen by self-check form: ① `demo()` → `python -c "from mod import demo; demo()"`; ② `__main__` → `python <file>.py`; ③ DocTest → `python -m doctest <file>.py`; ④ pure assert → `python -c "<statements>"` |
| **Timeout** | ≤ 30 seconds |
| **Pass criteria** | All asserts pass, no uncaught exceptions, exit code = 0 |
| **Failure self-heal** | AI reads the error stack → locates the defect → fixes → re-runs, up to 3 times |
| **Limit exceeded** | Mark `[BLOCKED: L1]` and output the failure log (input/expected/actual/stack) |
| **Skip condition** | Trivial code (function body ≤3 lines with no branches / pure data classes / pure type definitions) → annotate `[TRIVIAL: no self-check]` |
| **Report format** | `Layer 1 (self-check): ✅ PASS / ❌ FAIL (attempt N), N asserts executed` |

### Self-check coverage baseline

| Code type | Minimum self-check |
|:---|:---|
| New function/method | ≥1 assert covering the happy path |
| Modified existing function logic | Update the original self-check / add ≥1 assert if none existed |
| New/modified state machine | ≥1 assert per legal transition + ≥1 assert that each illegal transition is rejected |
| New/modified data validation | ≥1 assert for valid input + ≥1 assert per invalid input type |
| Algorithm-intensive (merge/encode/encrypt/compress) | ≥3 asserts covering different input scenarios (e.g. CRDT: insert + delete + concurrent conflicts) |
| Financial calculations (amounts/billing/prices) | Decimal/Fixed-Point types enforced; ≥2 asserts (normal calculation + boundary precision) |
| Code deletion | Confirm the remaining code still passes its self-check |

---

## 4. Layer 2: interface contract comparison

| Property | Value |
|:---|:---|
| **Method** | AI compares item by item against the interface contracts in OpenSpec specs (`openspec/changes/<name>/specs/<capability>/spec.md`) |
| **Checklist** | ① function/class name matches; ② input parameters (name/type/required) match; ③ return value structure (field name+type) matches; ④ error codes match; ⑤ side effects (DB writes/API calls) match |
| **Pass criteria** | All five items match |
| **Critical mismatch** | Type mismatch (e.g. `str` vs `int`) → the code must be fixed |
| **Advisory mismatch** | Code has extra fields not defined in the contract → judge by type: ① a concise ponytail addition (e.g. an extra `created_at` timestamp) → mark `[EXTRA_FIELD]`, non-blocking; ② a deliberately kept compatibility field → mark `[COMPAT_FIELD]`, record the reason, suggest updating the spec later |
| **Contract itself wrong** | Code is correct but the spec is wrongly defined → trigger conflict rule R6, fall back to an OpenSpec update |
| **Compatibility field identification** | If the code has both old and new field names (e.g. `token` + `access_token`) and the old name implies a transitional nature → mark `[COMPAT_FIELD: <old field name>]`, note the compatibility end version/time in IMPLEMENTATION_REPORT |
| **Skip condition** | Pure refactoring (interface unchanged) → `[REFACTOR: contract unchanged]` |
| **Report format** | `Layer 2 (contract): ✅ 5/5 matched / ⚠️ 3/5 (field: X type mismatch)` |

**Automated structural pre-check**: before the manual 5-item comparison, run `python pipeline/_contract_check.py --spec <spec.md> --source <src_dir>` to catch structural mismatches automatically (missing functions, parameter count mismatches, missing return type annotations). This covers ~80% of L2 checks; the remaining semantic checks (④ error codes, ⑤ side effects) still require AI review. If the script exits non-zero, fix structural issues first, then proceed to manual comparison.

---

## 5. Failure log format

```markdown
### T00X: <task name> — ❌ BLOCKED (L1: self-check)

- **File**: `src/services/auth_service.py`
- **Injected lines**: L42-L68
- **Blocking layer**: Layer 1 (Ponytail self-check)

**Self-check execution**:
$ python -c "from src.services.auth_service import demo; demo()"
Traceback (most recent call last):
  File "src/services/auth_service.py", line 52, in demo
    assert result.token is not None
AssertionError

**Root cause**: the `login()` return field is named `access_token`, but the self-check references `token`

**Fix suggestions**:
  Option A: change the self-check to `assert result.access_token is not None`
  Option B: unify `login()` to use the `token` field name

**Current status**: waiting for the user to choose an option before continuing.
```

---

## 6. Relationship with downstream nodes

```
Node 4 self-check            Node 5 static verification        Node 6 runtime verification
─────────────────    ──────────────────    ──────────────────
L0: import/immediate  Critical: mypy/tsc    Mode A: pytest
L1: assert/demo()     Standard: ruff/eslint  Mode B: Eval
L2: contract match    (independent external check)         (independent extended verification)

The three layers do not overlap:
- Node 4 = developer view "the code I wrote runs" — immediate, lightweight, code-level
- Node 5 = project view "the code meets the standards" — config-level, gate-like
- Node 6 = user view "the functionality is correct" — system-level, coverage/behavior evaluation
```

---
name: simulator-verify-runtime
description: Pipeline Node 6 - configurable runtime verification. Supports three modes: Mode A (pytest coverage), Mode B (Eval baseline for agent behavior), Mode C (A+B combined), with three-level threshold rulings (pass / release with warning / block). Use when runtime functional verification is needed after static verification passes.
---

# Configurable Runtime Verification

> Default thresholds use pipeline/CONFIG.md as the single source of truth; this document keeps numeric copies; thresholds declared by CI configuration take precedence.

## 1. Skill overview
- **Stage**: Pipeline Node 6/8
- **Upstream dependencies**: source files that passed Node 5 verification + OpenSpec `specs/*.md` (the gold standard for requirements) + `IMPLEMENTATION_REPORT.md` (the modification list)
- **Downstream output**: `VERIFY_RUNTIME_REPORT.md` (passed to Node 8, the commit stage)
- **Core goal**: through configurable verification modes, verify the **functional correctness** and **behavior quality** of the code in a real runtime environment. Automatically choose the test coverage mode, Eval baseline mode, or combined mode based on the project type, ensuring code leaving this stage is "functionally correct and behaviorally accurate".

## 2. Input schema
The AI must receive all of the following inputs:
| Input type         | Format requirement                                                     | Required                     |
| :--------------- | :----------------------------------------------------------- | :--------------------------- |
| Modified source code   | Source files that passed Node 5 verification                                        | **Required**                     |
| Requirements specification   | OpenSpec `specs/*.md` (as the baseline for functional verification)                  | **Required**                     |
| Implementation report         | `IMPLEMENTATION_REPORT.md` (explicitly lists which modules/functions were modified)    | **Required**                     |
| Verification report (Node 5)| `VERIFY_REPORT.md` (confirms static checks passed)                     | Recommended (as evidence of the precondition)  |

## 3. Verification mode selection mechanism

### 3.1 Automatic selection logic
The AI decides Node 6's verification mode by the following priority:

| Priority | Condition | Default mode | Description |
|:---|:---|:---|:---|
| 1 | The user explicitly specifies a verification mode | Per the specification | The user tells us directly |
| 2 | The project matches the AI Agent feature list (see 3.2 Mode B) | Mode B (Eval baseline) | Evaluate dialogue quality, tool call accuracy |
| 3 | The change contains the ENV_OPS flag (service startup/keep-alive/process management) | Mode D (environment verification) | Verify process liveness and restart behavior |
| 4 | Project type is tool library / SDK / server-side | Mode A (test coverage) | Evaluate functional correctness |
| 5 | Cannot determine | Mode C (combined) | Run both A and B, safest; stack Mode D when ENV_OPS is present |

### 3.2 The three verification modes in detail

#### Mode A: test coverage mode
- **Use case**: tool libraries, SDKs, API services, data processing pipelines
- **Execution**: `pytest --cov=<src_dir> --cov-report=json --cov-report=term -v`
- **Check dimensions**:
  - Unit test pass rate (must be 100% PASS, no FAILED/ERROR)
  - Line coverage (default threshold >= 80%)
  - Branch coverage (default threshold ≥ 70%, configurable)
  - Modified-file coverage (this change's modified files must have coverage ≥ the project threshold, default 80%; the threshold follows pipeline/CONFIG.md)
- **Test composition transparency**: the coverage report must include a one-line breakdown of test composition — count of unit-test files (files NOT importing `TestClient`/`testclient` and NOT matching `test_api*.py`) vs integration-test files (files importing `TestClient` or matching `test_api*.py`). Format: `Tests: N unit + M integration = T total`. This does NOT change any threshold — 100% coverage with 90% integration tests is still 100%. The purpose is transparency: reviewers can see at a glance whether coverage comes from fine-grained unit tests or broad HTTP-level integration tests. Report this in VERIFY_RUNTIME_REPORT.md under the coverage table.
- **If no test files exist**: the AI automatically generates a minimal test skeleton from the changes in `IMPLEMENTATION_REPORT.md`, then runs it.

#### Mode B: Eval baseline mode
- **Use case**: AI Agents, LLM applications, dialogue systems, RAG pipelines
- **AI Agent feature list** (any hit → default Mode B): ① code contains LLM API calls (OpenAI/Anthropic SDK, langchain, etc.); ② an agent loop / ReAct loop / multi-step reasoning executor exists; ③ tool-calling schemas are defined (function calling / tool registration); ④ a RAG retrieval component exists (vector store/retriever/re-ranker)
- **Execution**: run the preset eval baselines
- **Check dimensions** (preset by Agent type):
  - **Dialogue agent**: intent recognition accuracy, response relevance, multi-turn dialogue coherence
  - **Tool-calling agent**: tool selection accuracy, parameter extraction correctness, call-chain completeness
  - **RAG pipeline**: retrieval recall, answer faithfulness, context utilization
- **Thresholds**: each metric defaults to >= 80%
- **If no eval configuration exists**: the AI auto-generates eval cases from the interface contracts and edge conditions in OpenSpec `specs/*.md`, then runs them; if cases cannot be generated from the contracts (no usable edge cases/contracts) → degrade to Mode A, annotated `[SKIP_MODE_B: no baseline]`.

#### Mode C: combined mode
- **Execution order**: run Mode A (test coverage) first; after it passes, run Mode B (Eval baseline)
- **Result merging**: each is evaluated independently; either failing triggers the corresponding level of ruling

#### Mode D: environment verification mode
- **Use case**: the change contains the ENV_OPS flag — service startup/keep-alive/process management (background execution, daemon, restart policies, pythonw/nohup-style startup), dependency readiness/startup sequencing
- **Execution**:
  0. **Dependency readiness/startup sequencing verification**: first probe whether external dependencies (DB/Redis/MQ ports or health checks) are ready; verify the "dependencies before service" startup order and waiting strategy (wait-for semantics, retry backoff); when dependencies are not ready, the service must retry and wait rather than crash (e.g. the "service starts first, MySQL starts later" scenario)
  1. **Startup liveness verification**: start the service with the modified startup method, probe the process/port/logs; the liveness assertion must pass 100%
  2. **Crash-restart drill**: kill the main process, confirm it is automatically restarted per the modified keep-alive strategy, ≥1 pass
  3. **Exit code/log probing**: exit codes and error logs for scenarios such as startup failure and missing dependencies match expectations
- **Edge-case templates (ENV_OPS)**: ① the service fails to connect to the database after restart — must verify retry/readiness waiting; ② background keep-alive (pythonw/nohup) auto-restart after a crash; ③ startup-order dependencies (DB before service)
- **Degradation**: real environment unavailable/no permission → ① startup script dry-run; ② unit tests for process-management logic; ③ AI Review of restart/error-handling paths, annotated `[SKIP_ENV: no environment]`; this is not treated as a node failure
- **Success criteria**: liveness assertions 100%, restart drill 1/1 pass, or degradation items recorded and alternative verification completed

## 4. Execution workflow

### Step 1: Environment preparation
- **SESSION_STATE update**: write `ai_pipeline/SESSION_STATE.json` with `current_node: "Node 6"`, `current_task: ""`, `self_heal_round: 0`.
- **AI action**:
  1. Check whether project dependencies are installed (`pip list` or `npm list`, chosen by template).
  2. If test dependencies are missing (e.g. `pytest-cov`), install them automatically.
  3. Confirm the test/eval configuration exists; if not, enter the auto-generation flow.
- **AI responsibility**: confirm the environment is ready; halt and report if preparation fails.

### Step 2: Determine the verification scope and cases
- **AI action**: extract from `IMPLEMENTATION_REPORT.md` and OpenSpec `specs/*.md`:
  - All modified functions/classes (core units to verify).
  - All newly added interface contracts (integration points to verify).
  - All edge conditions and exception scenarios (test cases to cover).
- **Output**: `TEST_MATRIX.md` (the list of test/eval cases to run).

### Step 3: Execute verification

**Mode A execution**:
- The AI runs `pytest --cov --cov-report=term -v` in the terminal, parses the output to get the test pass rate and coverage.

**Mode B execution**:
- The AI runs the project's preset eval suite, reads each dimension's score, and compares against the thresholds.

**Mode C execution**:
- A first, then B; merge the results.

### Step 4: Threshold ruling (core AI reasoning)
- **Data reading**: the AI reads the verification result JSON.
- **Hard ruling rules**:

| Condition | Ruling | Action |
| :--- | :--- | :--- |
| All metrics meet the thresholds and no FAILED tests | ✅ **Pass** | Write the conclusion "runtime verification passed" |
| Metrics are between 90% and 100% of the threshold (just short) with a reasonable cause | ⚠️ **Release with warning** | Write "minor deviation, re-check recommended", **still release** to Node 8 |
| FAILED tests exist or metrics are below 90% of the threshold | 🛑 **Block** | Halt the pipeline, output an error report, request human intervention |

- **Note**: when blocked, the AI **must** embed detailed information about the failed cases (input, expected output, actual output) in the report for developers to locate precisely.

### Step 5: Generate the final verification report
Aggregate all test results, Eval scores, and coverage data into `VERIFY_RUNTIME_REPORT.md`.

## 5. Output schema (VERIFY_RUNTIME_REPORT.md template)

```markdown
# Runtime Verification Report - [requirement name] - [date]

## Overall conclusion: ✅ passed / ⚠️ minor deviation (released) / 🛑 blocked (needs human fix)

## Verification mode: Mode C (combined: test coverage + Eval baseline)

---

### 1. Environment info
- Python version: 3.11.4
- Test framework: pytest 8.x + pytest-cov
- Eval baseline: agent-eval-suite v1.2
- Dependency status: ✅ all ready

---

### 2. Mode A: test coverage results

#### Test execution summary
| Metric | Result | Threshold | Status |
| :--- | :--- | :--- | :--- |
| Unit test pass rate | 100% (12/12 PASS) | 100% | ✅ |
| Line coverage | 87.3% | ≥ 80% | ✅ |
| Branch coverage | 75.0% | ≥ 70% | ✅ |
| Modified-file coverage | 92.1% | ≥ 85% | ✅ |

#### Failed case details (none)
(If failures exist, list each FAILED case's input/expected/actual/stack here)

---

### 3. Mode B: Eval baseline results

#### Eval dimension scores
| Dimension | Score | Threshold | Status |
| :--- | :--- | :--- | :--- |
| Tool selection accuracy | 94.2% | ≥ 80% | ✅ |
| Parameter extraction correctness | 91.7% | ≥ 80% | ✅ |
| Call-chain completeness | 88.5% | ≥ 80% | ✅ |
| Edge condition handling | 76.0% | ≥ 80% | ⚠️ minor deviation |

#### Eval failure case details
| Case ID | Scenario | Expected behavior | Actual behavior | Deviation notes |
| :--- | :--- | :--- | :--- | :--- |
| BOUND-03 | Network timeout | Return a degraded response | Throws an uncaught exception | Timeout exception handling needed |
| BOUND-07 | Empty input | Return an empty list | Returns None | Return value type mismatch |

---

### 4. Final ruling
- **Test coverage**: ✅ all thresholds met
- **Eval baseline**: ⚠️ edge condition handling 76% (slightly below the 80% threshold), 2 unhandled edge scenarios
- **Overall conclusion**: ⚠️ **release with warning**. The edge-case deviation does not block core functionality; recommend fixing BOUND-03/BOUND-07 in a later iteration.

**Follow-up items after release**:
- [ ] BOUND-03: add `asyncio.wait_for` timeout handling for network calls
- [ ] BOUND-07: unify the empty-value return type to `[]`
```

## 6. Exception handling strategy

- **Missing test dependencies**: if `pytest`/`pytest-cov` is not installed, the AI runs `pip install pytest pytest-cov` automatically. If installation fails, skip Mode A, run only Mode B (if configured), and annotate `[SKIP_MODE_A]` in the report.
- **Missing eval configuration**: if the project has no `eval_suite` configured, the AI auto-generates a minimal eval case set from the interface contracts and edge conditions in OpenSpec `specs/*.md`, annotated `[AI_GENERATED_EVAL]`.
- **Run timeout**: a single test/eval case timing out after 60 seconds is automatically judged FAILED, to avoid stalling the pipeline.
- **External dependencies unavailable** (e.g. database, API): if the external services the tests depend on are unavailable, the AI skips integration tests, runs only unit tests and mock-level verification, and annotates `[SKIP_INTEGRATION]`.
- **Environment unavailable** (Mode D): no real runtime environment or no process-management permission → execute alternative verification per the Mode D degradation rules, annotated `[SKIP_ENV: no environment]`.

## 7. Successful exit criteria (gate pass condition)

- The verification mode has been auto-selected and executed based on the project type/configuration.
- **Mode A**: all unit tests PASS (0 failures), line coverage ≥ the configured threshold (default 80%), modified-file coverage ≥ the configured threshold.
- **Mode B**: all Eval dimension scores ≥ the configured threshold (default 80%), no severe behavioral deviations.
- **Mode C**: both A and B satisfy the above conditions.
- If "release with warning" is used (metrics between 90% and 100% of the threshold), the report must explicitly list the follow-up items.
- `VERIFY_RUNTIME_REPORT.md` has been generated and contains complete test/eval results and failed-case details.

------

**After passing this gate, pass the absolute path of VERIFY_RUNTIME_REPORT.md, all modified source file paths, the OpenSpec specs/*.md, and IMPLEMENTATION_REPORT.md to Node 8 (commit stage).**

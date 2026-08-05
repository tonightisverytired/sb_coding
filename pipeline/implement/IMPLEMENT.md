---
name: implement-code-generation
description: Pipeline Node 4 - precision code implementation. Execute atomic tasks in topological order, generate complete business logic code with the AI, inject it into source files directly with code editing tools, and run immediate mypy checks (up to 3 self-heal rounds). Use when code needs to be generated and injected after location is complete.
---

# Precision Code Implementation

## 1. Skill overview
- **Stage**: Pipeline Node 4/8
- **Upstream dependencies**: `LOCATE_MAP.md` output from Node 3 + OpenSpec specs (as the L2 contract baseline) + `TASK_PLAN.md`
- **Downstream output**: physically modified source files + `IMPLEMENTATION_REPORT.md` (passed to Node 5, the verification stage)
- **Core goal**: under the "understand first, modify second" principle, the AI generates complete business logic based on the project's existing code style, injects it into source files directly with code editing tools (such as apply_patch / SearchReplace / Edit), and ensures the output code passes immediate type checks.

## 2. Input schema
The AI must receive all of the following inputs:
| Input type       | Format requirement                                                     | Required |
| :------------- | :----------------------------------------------------------- | :------- |
| Physical location list   | `LOCATE_MAP.md` (from Node 3, with file paths, line numbers, context)       | **Required** |
| Task execution list   | `TASK_PLAN.md` (from Node 3, with topological order and openspec_ref)       | **Required** |
| Interface contract baseline | OpenSpec specs (`openspec/changes/<name>/specs/<capability>/spec.md`) | **Required** (as the L2 self-check comparison baseline) |

## 3. Execution workflow

### Step 1: Load tasks in order (follow the topological order)
- **AI action**: read the dependency order annotated in `TASK_PLAN.md`, and execute **strictly in topological order** (e.g. T002 (data model layer) must come before T001 (business service layer) if T001 depends on T002).
- **No parallel execution**: although each task is relatively independent, to avoid code version conflicts they must run serially; update the in-memory file state immediately after each task.
- **REUSED tasks**: tasks whose change type is marked `REUSED` (conflict rule R2 reuse ruling) skip code implementation; record the reuse source and move to the next task; the task stays in TASK_PLAN and is not deleted.
- **SESSION_STATE update**: before starting each task, write `ai_pipeline/SESSION_STATE.json` (overwrite) with `current_node: "Node 4"`, `current_task`, `current_file`, `self_heal_round: 0`, `resume_hint: ""`. After each self-heal round, update `self_heal_round` and set `resume_hint` to the error + fix direction (e.g. "mypy: no-untyped-def on routes.py:93. Add -> ReturnType annotation."). This ensures that if the session is interrupted mid-task, the next session knows exactly which task, which file, which heal round to resume from. Schema: `pipeline/_session_state_schema.json`.

### Step 2: Context anchoring and code generation (core AI reasoning)
For the current task (e.g. T001):
- **AI action**:
  1. Read the context code block and line number info for the target file from `LOCATE_MAP.md`.
  2. Understand whether the task is an **addition** or **modification**, and generate complete code based on the project's existing code style and the interface contracts in OpenSpec specs/*.md.
  3. For values requiring precise computation or complex regexes, the AI may use Bash to run single-line Python commands to get deterministic results, rather than writing them by hand.
- **Strict requirements**: the generated code must have consistent style, complete type annotations, and necessary imports.

### Step 3: In-place injection (AI operates directly)
- **AI action**: use code editing tools (such as apply_patch / SearchReplace / Edit) to inject the generated code block at the exact line position in the target file.
- **Safety mechanism**: before injection, confirm the modification scope with `git diff` to avoid accidentally modifying unrelated code.

### Step 4: Immediate type check (hard loop red line — ahead of Node 5)
- **AI action** (auto-selected by current tech stack):
  - Python: run `mypy --strict <modified file path>` or `pyright <file>` in the terminal
  - TypeScript: run `tsc --noEmit` in the terminal
- **AI decision tree**:
  - **Exit code 0 (pass)** → move to the next task.
  - **Exit code non-zero (error)** → the AI reads the error log and **attempts to fix it up to 3 times** (re-running the type check after each fix).
    - If the 3rd attempt still fails → terminate the entire Node 4 flow, output `CHECK_ERROR_REPORT.md`, roll back with `git checkout -- <file>`, and request human intervention.
    - **Escape-hatch detection**: if a self-heal "passes" by using `Any`, `# type: ignore`, `cast()`, or `Callable[..., Any]` as a last-resort workaround, the fix is NOT a true pass. Record it immediately in ERROR_MEMORY with the tag `[ESCAPE_HATCH]` (format: `[ESCAPE_HATCH] T00X L0: <original error>, workaround: <Any/type:ignore/etc.>, risk: <what type safety was lost>`). Node 5 Critical gate must scan for `[ESCAPE_HATCH]` entries and flag them for human review — they are not blocking (the code works), but they are a quality debt that compounds.
- **Layer-level checkpoint**: after completing each topological layer from TASK_PLAN (e.g. all foundation tasks, all service tasks, all API tasks), run the type checker on **all files written so far** — not just the single modified file. Single-file mypy on a new file may miss cross-file type errors (e.g. an import chain that type-checks only when all files are present). This is the primary gate; per-task mypy above is a fast-fail supplement. If the layer checkpoint fails, fix before moving to the next layer — do not defer to Node 5.
- **Hard constraint**: **code with type errors must never leave Node 4**.

### Step 5: Immediate sedimentation + generate the implementation report
After each task completes:
1. Run the L0/L1/L2 three-layer self-check (L2 compares against the interface contracts in the OpenSpec specs)
2. Update `IMPLEMENTATION_REPORT.md` (task summary + self-check results + line numbers)
3. **Immediately append** to `ai_pipeline/RUN_LOG.md` in the following format:

**Task completed normally**:
```
## [timestamp] T00X complete
- File: <file path>
- L0(import): ✅ | L1(self-check): ✅ N asserts | L2(contract): ✅ N/N
- Decision: <key decision description, e.g. "use bcrypt synchronous method, ponytail: consider async version under high concurrency">
```

**Task completed after self-healing**:
```
## [timestamp] T00X self-healed N times
- L<N> failed: <specific error>
- Fix: <fix method>
- Prevention: <how to avoid next time>
```

4. If self-healing/errors occurred → **immediately append** to `ai_pipeline/ERROR_MEMORY.md` in the following format:

```
- [timestamp] T00X L<N>: <error description>, fix: <fix method>, prevention: <how to avoid next time>
```

ERROR_MEMORY entries are grouped by run date (`## YYYY-MM-DD Run #N — <change-name>`), accumulating across runs without overwriting.
5. **Sync the tasks.md checkboxes**: if `openspec/changes/<name>/tasks.md` exists, change the corresponding entries from `- [ ]` to `- [x]` per the openspec_ref in TASK_PLAN; REUSED tasks are also checked `[x]` with the annotation `<!-- reused: <reuse source> -->` appended (the work is factually complete, just no new code written); in `[NO_OPENSPEC]` / `[LIGHT_PLAN]` modes there is no tasks.md, so this is skipped.

## 4. Output schema (IMPLEMENTATION_REPORT.md template)

```markdown
# Code Implementation Report - [requirement name] - [date]

## Overall status: ✅ complete (N/N tasks) / ❌ halted (reason)
## Contract check: <N> passed / <M> failed from `_contract_check.py` | [SKIP_CONTRACT_CHECK: <reason>]

> ⚠️  Required field. If the project is Python and this field is empty, Node 5 MUST reject the handoff and send back to Node 4. Legal skip reasons: `[SKIP_CONTRACT_CHECK: not Python template]`, `[SKIP_CONTRACT_CHECK: no spec file]`.

---

### T001: Add user authentication service
- **File path**: `/project/src/services/auth_service.py`
- **Operation mode**: INSERT (new class)
- **Injection lines**: end of file (after line 95)
- **Script call log**:
  - `calc_helpers.py --op timeout --value 30`: returned `30` (seconds) ✅
  - `regex_helper email_pattern`: returned the regex ✅
  - `format_code`: returned 0, formatted (ruff format). ✅
- **Immediate type check**: ✅ passed (`mypy --strict`, no errors)
- **Final code block preview (key part)**:
  ```python
  from src.models.user import User
  from src.utils.jwt import generate_token

  class AuthService:
      """User authentication service"""

      def login(self, username: str, password: str) -> dict[str, str]:
          """User login, returns a JWT token"""
          user = User.find_by_username(username)
          if not user or not user.verify_password(password):
              raise AuthenticationError("Incorrect username or password")

          token = generate_token(user.id)
          return {"token": token, "expires_in": 3600}
  ```

### T002: Add query method to the user model
- **File path**: `/project/src/models/user.py`
- **Operation mode**: MODIFY (add a method to the User class)
- **Modified line range**: original User class lines 15-85; added `find_by_username` at lines 86-95
- **Script call log**:
  - `format_code`: returned 0, formatted. ✅
- **Immediate type check**: ✅ passed (`mypy --strict`, no errors)
- **Final code block preview (key part)**:
  ```python
  @staticmethod
  def find_by_username(username: str) -> "User | None":
      """Look up a user by username"""
      return User.query.filter_by(username=username).first()
  ```

### T003: Add state machine to the task executor
- **File path**: `/project/src/tools/task_executor.py`
- **Operation mode**: MODIFY (modify the `execute` method, add state transition logic)
- **Modified line range**: original lines 45-78; added state machine logic, extended to lines 45-105
- **Script call log**:
  - `format_code`: returned 0, formatted. ✅
- **Immediate type check**: ⚠️ failed on the 1st attempt (`State` enum undefined); after AI auto-fix, passed on the 2nd attempt ✅
- **Final code block preview (key part)**:
  ```python
  from enum import Enum, auto

  class TaskState(Enum):
      IDLE = auto()
      PENDING = auto()
      RUNNING = auto()
      SUCCESS = auto()
      FAILED = auto()
      CANCELLED = auto()

  class TaskExecutor:
      VALID_TRANSITIONS = {
          TaskState.IDLE: [TaskState.PENDING],
          TaskState.PENDING: [TaskState.RUNNING],
          TaskState.RUNNING: [TaskState.SUCCESS, TaskState.FAILED, TaskState.CANCELLED],
          TaskState.FAILED: [TaskState.PENDING],  # manual retry
      }

      def transition(self, new_state: TaskState) -> None:
          if new_state not in self.VALID_TRANSITIONS.get(self.state, []):
              raise IllegalStateTransitionError(
                  f"Cannot transition from {self.state} to {new_state}"
              )
          self.state = new_state
  ```

## Rollback info
- To roll back, run: `git checkout -- <file path>`
```

## 5. Exception handling strategy
- **Line number drift**: after injecting code, the line numbers in `LOCATE_MAP.md` may become invalid for later tasks. **The AI must re-confirm the current line numbers of the target symbols via LSP or `rg` before each task**, to ensure accurate injection positions.
- **Self-heal loop limit exceeded**: if the same task triggers type-check errors more than 3 times, the AI judges it as "logic that is hard to auto-fix", immediately terminates, and requests human intervention to avoid an infinite loop consuming tokens.
- **Uncertain values**: if a value needs precise computation but the AI is unsure of it (e.g. cryptographic hashes, complex algorithm parameters), use Bash to run single-line Python commands to get the result, rather than hardcoding it directly.

## 6. Successful exit criteria (gate pass condition)
- All atomic tasks (the N tasks in `TASK_PLAN.md`) have been executed, with no task missed.
- Every modified source file has passed the **immediate type check** (Python: `mypy --strict`; TypeScript: `tsc --noEmit`) with no syntax/type errors.
- `IMPLEMENTATION_REPORT.md` has been generated and includes a **modification summary** and **final modified line numbers** for each task.
- The code contains no `TODO`, placeholders, or incomplete markers.

---

**After passing this gate, pass the absolute path of `IMPLEMENTATION_REPORT.md` and the list of all modified source file paths to Node 5 (verification stage).**

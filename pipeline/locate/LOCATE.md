---
name: locate-code-positioning
description: Pipeline Node 3 - physical code location. Use Python ast/ripgrep/LSP to map atomic tasks precisely to line ranges in source files, producing LOCATE_MAP.md. Use when a development task needs to be located to a specific code position.
---

# Physical Code Location

## 1. Skill overview
- **Stage**: Pipeline Node 3
- **Upstream dependencies**: `TASK_PLAN.md` output from Node 2 + OpenSpec `specs/*.md` (for understanding module semantics)
- **Downstream output**: `LOCATE_MAP.md` (passed to Node 4, the implementation stage)
- **Core goal**: map every atomic task in TASK_PLAN to a **physical position** in the source code (absolute path, function/class name, line range, context code block), so that Node 4 can "open the file and modify directly" without further searching.
- **Greenfield mode** (`[CODEBASE] greenfield`): output a one-line summary — `# Location Map — greenfield project. All N tasks are [NEW_FILE]. No existing code to locate.` No per-task context blocks, no line ranges, no confidence scores. Node 4 in greenfield mode creates files from scratch; location information adds zero value.
- **Brownfield mode** (`[CODEBASE] brownfield`): full LOCATE_MAP per the format below — every MODIFY/DELETE task must have exact line ranges and context code blocks. ADD tasks in brownfield projects still need insertion points (end of file, after specific class).

## 2. Input schema
The AI must receive all of the following inputs:
| Input type       | Format requirement                                                     | Required                                    |
| :------------- | :----------------------------------------------------------- | :--------------------------------------- |
| Task execution plan   | `TASK_PLAN.md` (from Node 2, with file paths, target symbols, dependencies, openspec_ref) | **Required**                                 |
| Interface specs       | OpenSpec `specs/*.md` (for understanding module semantics and interface contracts)           | **Required**                                 |
| Project source code       | The full project source tree                                         | **Required**                                 |
| LSP service ready    | IDE LSP service initialized, supporting goToDefinition / findReferences   | **Strongly recommended**; degrades to plain-text search if missing     |

## 3. Execution workflow

### Five-step location method (core methodology)

For each atomic task in TASK_PLAN, locate it step by step:

```
Step 1: Module path inference → Step 2: Symbol search → Step 3: Context extraction
  → Step 4: Uniqueness check → Step 5: Token budget control
```

---

### Step 1: Module path inference (AI reasoning)

- **AI action**: read the "target file" and "target symbol" fields in TASK_PLAN, combine them with the project directory structure, and infer candidate file paths using:
  - Fuzzy matching on directory names (e.g. `auth` → `src/services/auth_service.py`)
  - Pattern matching on file names (e.g. `user model` → `src/models/user.py`)
  - `rg` searches for class/function names to locate candidate files
- **AI responsibility**: pick the final file from the candidate list; the candidate path selection line is ≥ 0.80; if the highest confidence is < 0.80, mark `[AMBIGUOUS]` and ask the user.

### Step 2: Symbol-level precise location (multi-tool combination)

Choose the location toolchain based on the current template type:

#### Python template location methods

| Method | Tool/command | Use case | Precision |
|:---|:---|:---|:---|
| AST parsing | `ast` module to parse Python source | Locate function/class/method definitions | Exact line numbers |
| Text search | `rg -n "def login\|class AuthService" src/` | Fuzzy match multiple symbols | Line ranges |
| LSP symbol lookup | IDE LSP `workspaceSymbol` / `goToDefinition` | Jump precisely to the definition | Exact line/column |
| Import tracking | `rg "from.*import.*TaskExecutor"` | Locate dependency reference positions | Reference line numbers |

#### TypeScript template location methods

| Method | Tool/command | Use case | Precision |
|:---|:---|:---|:---|
| AST parsing | `ts-morph` / `tsc --showConfig` | Locate function/class/interface definitions | Exact line numbers |
| Text search | `rg -n "function login\|class AuthService" src/` | Fuzzy match multiple symbols | Line ranges |
| LSP symbol lookup | IDE LSP `workspaceSymbol` / `goToDefinition` | Jump precisely to the definition | Exact line/column |
| Import tracking | `rg "from\|import.*TaskExecutor"` | Locate dependency reference positions | Reference line numbers |

#### default template
The AI asks the user to specify search tools item by item (defaults to `rg` + LSP).

---

**AI execution actions**:
1. If the task is "add" (ADD): locate the **insertion point** in the target file (end of file, end of class, or after the most relevant function).
2. If the task is "modify" (MODIFY): precisely locate the **definition start line** and **scope end line** of the target function/class/method/variable.
3. If the task is "delete" (DELETE): locate the **exact start and end line numbers** of the code block to remove.

**Intermediate output**: a `symbol location card` for each task:

```markdown
### T001 location result
- **Target file**: `src/services/auth_service.py`
- **Target symbol**: `AuthService.login` (function)
- **Location method**: rg search + LSP jump
- **Line range**: L42-L68 (function definition + docstring + implementation body)
- **Operation type**: ADD (insert new logic after L68)
```

### Step 3: Context code block extraction (AI reads directly)

- **AI action**: directly read the target line range in the target file and extract the context code block:
  - Default context: **15 lines** before and after the target symbol (about 30 lines total), for the AI to understand the surrounding environment.
  - Generate a normalized context code block (with line number annotations).
- **AI responsibility**: verify that the extracted code block actually contains the target symbol, and that the context is sufficient to understand the modification point.

**Example output**:
```python
# [LOCATE_MAP] context code block - src/services/auth_service.py L35-L80

35: class AuthService:
36:     """User authentication service"""
37:
38:     def __init__(self, db_session: Session):
39:         self.db = db_session
40:
41:     # [T001] Target symbol: login - lines 42-68
42:     def login(self, username: str, password: str) -> dict:
43:         """User login interface
44:
45:         Args:
46:             username: username (3-32 chars)
47:             password: plaintext password
48:
49:         Returns:
50:             dict: {token, expires_in, refresh_token}
51:         """
52:         # Parameter validation
53:         if not username or len(username) < 3:
54:             raise ValueError("Username cannot be empty and must be at least 3 chars")
55:
56:         # Look up the user
57:         user = User.find_by_username(self.db, username)
58:         if not user:
59:             raise AuthError(AUTH_001, "Incorrect username or password")
60:
61:         # Password verification
62:         if not bcrypt.verify(password, user.password_hash):
63:             self._record_failed_attempt(user)
64:             raise AuthError(AUTH_001, "Incorrect username or password")
65:
66:         # Generate token
67:         token = jwt.encode({"user_id": user.id, "exp": ...}, SECRET_KEY)
68:         return {"token": token, "expires_in": 3600}
69:
70:     # Subsequent code...
```

### Step 4: Uniqueness check (hard gate)

- **Critical red lines (blocking)**:
  - The same task locates the **same symbol name** in multiple files and the AI cannot determine which one it belongs to → mark `[CONFLICT]` and halt.
  - The target symbol in the location result **does not exist** in the source code → mark `[NOT_FOUND]` and halt.
  - Either trigger terminates the run; the AI must request human intervention to clarify the target file.

- **Standard red lines (warning level)**:
  - The located symbol name does not **exactly match** the symbol name in the task description (e.g. the task asks for `login` but `do_login` was located). The AI automatically annotates `[APPROXIMATE_MATCH]` and records it in the warning area.
  - Location confidence in the 0.60–0.80 range → automatically annotate `[APPROXIMATE_MATCH]`; Node 4 must re-verify before implementing.

### Step 5: Token budget control (global constraint)

- **Suggested cap**: the total tokens of all context code blocks in `LOCATE_MAP.md` should be ≤ 30K. When exceeded, keep the complete code blocks of direct modification targets first, and keep only key lines for dependency references. Under the current 200K context, this limit is a soft suggestion.
- **Control strategy**:
  1. Prioritize keeping the code blocks of **direct modification targets** (keep the function/class containing the modification point complete).
  2. Keep only **key lines** (≤ 5 lines) for dependency reference code blocks (e.g. import statements, parent class definitions).
  3. If the task count is > 15, keep only **file path + line numbers + one-line summary** for low-priority tasks, without full context.
- **AI responsibility**: after locating all tasks, estimate the total tokens (about 1 Token ≈ 4 English characters or 1 Chinese character); if over the limit, trim per the strategy above until it passes.

## 4. Output schema (LOCATE_MAP.md template)

```markdown
# Physical Code Location Map - [requirement name] - [date]

## Location overview
- **Total tasks**: N
- **Located successfully**: K
- **Needs human intervention**: M (including [CONFLICT] / [NOT_FOUND] / [AMBIGUOUS])
- **Estimated total tokens**: about XX K

## Location mapping table

| Task ID | Task summary           | Target file                             | Target symbol          | Line range  | Operation type | Confidence |
|:-------|:-------------------|:-------------------------------------|:------------------|:----------|:---------|:-------|
| T001   | Add login interface       | src/services/auth_service.py         | AuthService.login | L42-L68   | ADD      | 0.95   |
| T002   | Add user query method   | src/models/user.py                   | User.find_by_username | L25-L35 | ADD      | 0.92   |
| T003   | Add task state machine     | src/tools/task_executor.py           | TaskExecutor.run  | L60-L95   | MODIFY   | 0.88   |

## Per-task context code blocks

### T001 - AuthService.login (confidence: 0.95)
- **Physical path**: `[project root]/src/services/auth_service.py`
- **Line range**: L42-L68 (context L35-L80)
- **Location method**: rg search + LSP jump

```python
# [L35-L80] context code block (insertion point: after L68)
[code content...]
```

### T002 - User.find_by_username (confidence: 0.92)
- **Physical path**: `[project root]/src/models/user.py`
- **Line range**: L25-L35 (context L18-L48)
- **Location method**: rg search

```python
# [L18-L48] context code block (insertion point: after L35)
[code content...]
```

## Warnings and items to confirm
- [APPROXIMATE_MATCH] T003: the task description says "state machine" but the `run()` method was located; confirm whether it is the correct modification entry point.
- [AMBIGUOUS] T004: two candidate paths exist — `src/api_v1/auth.py` and `src/api_v2/auth.py`; waiting for the user to choose.
```

## 5. Exception handling strategy

- **Project source unavailable**: if the project directory has no source files (e.g. a brand-new project), annotate every task in `LOCATE_MAP.md` as `[NEW_FILE]`, infer the target file path from the module name (e.g. `auth → src/services/auth_service.py`), and mark `[AI_GUESSED]`.
- **LSP service unavailable**: degrade to plain-text search mode (`rg` + `grep`), annotate `[LSP_UNAVAILABLE]` at the top of the report, and automatically lower location confidence by 0.15.
- **Giant files**: if the target file is > 2000 lines, extract symbol-level location info only through LSP documentSymbol, without extracting full context, to reduce token consumption.

## 6. Successful exit criteria (gate pass condition)

- `LOCATE_MAP.md` has been generated, containing the location mapping table + context code blocks for all tasks.
- Confidence for all tasks ≥ 0.60 (release line); the 0.60–0.80 range is automatically annotated `[APPROXIMATE_MATCH]` and re-verified by Node 4; < 0.60 counts as a location failure and requires human intervention.
- No `[CONFLICT]` or `[NOT_FOUND]`-level blocking issues.
- Total tokens of context code blocks ≤ 30K (soft suggestion, not a hard block).
- Every task has an explicit target file path and line range (INSERT_POINT is allowed as the insertion point for add tasks).

------

**After passing this gate, write the absolute paths of LOCATE_MAP.md and TASK_PLAN.md (from Node 2, passed through without modification) into the context, and pass them together with the OpenSpec specs/*.md to Node 4 (implementation stage).**

**Immediate sedimentation**: after location completes, append to RUN_LOG:
```
## [time] Node 3 complete
- Located N/N tasks, confidence 0.XX-0.XX, no CONFLICT/NOT_FOUND
```

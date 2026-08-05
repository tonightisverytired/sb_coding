---
name: commit-semantic-delivery
description: Final pipeline node - semantic commit and final delivery. Aggregate changes into a Conventional Commits message, scan for debug leftovers, execute git commit, generate TECH_NOTES from RUN_LOG, and update ERROR_MEMORY and PIPELINE_STATUS.
---

# Semantic commit and final delivery

## 1. Skill overview
- **Stage**: final Pipeline node
- **Upstream dependencies**: final modified source files + `ai_pipeline/RUN_LOG.md` + `IMPLEMENTATION_REPORT.md` + `VERIFY_RUNTIME_REPORT.md`
- **Downstream output**: `COMMIT_MESSAGE.md` + Git Commit + `TECH_NOTES.md` + updated `PIPELINE_STATUS.md`

## 2. Input specification
| Input type | Format requirement | Required |
|:---|:---|:---|
| Final modified source files | Physical files (for `git status` and `git diff`) | **Required** |
| RUN_LOG | `ai_pipeline/RUN_LOG.md` (continuous sedimentation record) | **Required** |
| Implementation report | `IMPLEMENTATION_REPORT.md` | Recommended |
| Verification report | `VERIFY_RUNTIME_REPORT.md` | Recommended |

## 3. Internal processing flow

### Step 1: Change aggregation and automatic classification
- Run `git status --porcelain` to get the status of changed files
- Roughly classify by path rules: services/api → feat; models/schemas → feat; tools/agents → feat; .md/docs → docs; test/ → test
- No more than 3 groups

### Step 2: Semantic aggregation and summary extraction
- For each group of changes, combine `RUN_LOG.md` and `IMPLEMENTATION_REPORT.md` to generate a user-perspective, verb-led summary of ≤50 characters
- If two groups of changes are completely unrelated in business terms → trigger a split suggestion

### Step 3: Conventional Commits generation
- Format: `<type>(<scope>): <subject>` + Body + Footer
- Body references the decision entries in RUN_LOG (`Ref: RUN_LOG T00X decision`)
- Footer contains the ⚠️ items and known issues from RUN_LOG

### Step 4: Pre-commit red-line checks
- **Critical**: scan for debug leftovers (print/breakpoint/console.log/debugger), oversized files (single file >1000 new lines)
- **Standard**: untracked source files → git add; body lines too long → auto wrap

### Step 5: Delivery execution
- `git commit -F COMMIT_MESSAGE.md`
- main/master branch → WARN + pause for confirmation
- Generate `PIPELINE_SUMMARY.md`

- **Append the Phase D advancement prompt at the end of PIPELINE_SUMMARY**: Phase C complete. Code committed. Continue to Phase D? Reply sync / archive / all / later
- **Persist the Phase D prompt**: write the same prompt to `ai_pipeline/PHASE_D_PENDING.md` (overwrite). The Pipeline Entry step (see pipeline/SKILL.md §Entry step 6) checks for this file on next invocation. After Phase D completes (sync+archive), delete this file.
- **Extract Ponytail debt**: run `grep -rn "ponytail:" src/` and append findings to `ai_pipeline/PONYTAIL_DEBT.md` (append mode — use Append Protocol §0). Format each entry as: `<file>:<line> | <limit> | <upgrade path>`. This ensures deliberate shortcuts are tracked across runs and visible to the `/ponytail-debt` sub-skill.
### Step 6: Wrap-up sedimentation
- Generate `ai_pipeline/TECH_NOTES.md` from `RUN_LOG.md` (see the settle SKILL)
- Completeness check: do the error/self-heal/⚠️ entries in RUN_LOG have corresponding records in ERROR_MEMORY?
- **tasks.md completion check**: against the openspec_ref in IMPLEMENTATION_REPORT, fill in `[x]` for completed tasks (including REUSED); if unchecked items still remain after filling → list them in PIPELINE_SUMMARY and the Phase D prompt for archive-time handling per R8

### Step 7: Update tracking files
- **Clear SESSION_STATE**: write `{}` to `ai_pipeline/SESSION_STATE.json` (empty object). This signals to the next Pipeline Entry that no pipeline is in progress.
- Update `PIPELINE_STATUS.md`:
  - Stages: √ Node 3 → √ Node 4 → √ Node 5 → √ Node 6 → √ Node 8
  - Artifact paths: LOCATE_MAP, IMPLEMENTATION_REPORT, VERIFY_REPORT, VERIFY_RUNTIME_REPORT, TECH_NOTES, RUN_LOG, ERROR_MEMORY, COMMIT_MESSAGE
  - Known issues: extracted from RUN_LOG

## 4. Successful exit criteria
- `git status` shows the changes are staged
- `COMMIT_MESSAGE.md` follows the Conventional Commits format
- Pre-commit red lines pass 100%
- The commit command has been executed
- `TECH_NOTES.md` has been generated from RUN_LOG
- `PIPELINE_STATUS.md` has been updated
- If an openspec tasks.md exists, all completed tasks (including REUSED) have their checkboxes filled in

---

**🎉 Pipeline execution complete. Code committed, RUN_LOG and ERROR_MEMORY sedimented, TECH_NOTES generated.**

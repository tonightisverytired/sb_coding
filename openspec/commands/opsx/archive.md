---
name: "OPSX: Archive"
description: "Archive a completed change in an experimental workflow"
allowed-tools: Bash(openspec:*)
category: "Workflow"
tags: ["workflow", "archive", "experimental"]
---

Archive a completed change in an experimental workflow.

**Store selection:** If the user specified a store (a store is a separate OpenSpec repository registered on this machine), or the work belongs to a store, run `openspec store list --json` to discover the registered store id, then pass `--store <id>` on commands that read and write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `view`). Other commands do not accept this flag. The prompts printed by commands already include this flag; keep it in subsequent operations. If there is no store, commands operate on the nearest local `openspec/` root.

**Input:** Optionally specify a change name after `/opsx:archive` (e.g. `/opsx:archive add-auth`). If omitted, check whether it can be inferred from the conversation context. If unclear or ambiguous, you must prompt the user to choose from the available changes.

**Steps**

1. **Select the change**

   If a name was provided, use it directly. Otherwise:
   - Infer it from the conversation context (if the user mentioned a change)
   - If only one active change exists, select it automatically
   - If ambiguous, run `openspec list --json` to get the list of available changes and ask the user to choose

   When prompting, only show active changes (not yet archived).
   If available, include the schema used by each change.

   Always state: "Using change: <name>" and how to override (e.g. `/opsx:archive <other>`).

   **Load the current archive input before the existing archive checks:**

   After determining the selected change and planning root, run:
   ```bash
   openspec instructions archive --change "<name>" --json
   ```
   Keep the same selected root flag on this command. This lookup is advisory and optional: it only provides additional prompt input, so it must never block archiving.
   If it exits non-zero or returns invalid JSON — for example on an older CLI that does not support this command yet — continue the archive workflow without any context or operation guidance. Do not report an error, do not stop.

   A successful response may omit the two optional fields. Treat `context` as required prompt-level input: read and consider it, applying relevant project facts, conventions, and constraints. Treat `operationGuidance` as optional additional advice: read and consider each item, following those that apply and are compatible with the built-in archive workflow.

   Keep these two fields separate from the built-in steps, explicit user choices, resolved paths, CLI checks, and command conventions. If context conflicts with one of these control inputs, report the conflict and keep the control values. If guidance does not apply or conflicts with control inputs, do not follow it and explain why. Do not infer alternative paths, skipped prompts, or flags from either field, and do not copy their text verbatim into specs, change artifacts, or archive summaries unless the user separately asks for it. These are prompt-level behavioral conventions, not enforceable checks.

2. **Check artifact completion status**

   Run `openspec status --change "<name>" --json` to check artifact completion.

   Parse the JSON to understand:
   - `schemaName`: the workflow in use
   - `planningHome`, `changeRoot`, `artifactPaths`, and `actionContext`: path and scope context
   - `artifacts`: the artifact list and their statuses (`done`, `skipped`, or other)

   **If any artifact is neither `done` nor `skipped`** (a skipped artifact satisfies the requirement — the change declares skip_specs):
   - Show a warning listing the incomplete artifacts
   - Prompt the user to confirm whether to continue
   - Continue if the user confirms

3. **Check task completion status**

   Read the tasks file (usually `tasks.md`) to check for incomplete tasks.

   Count the tasks marked `- [ ]` (incomplete) versus `- [x]` (complete).

   **If there are incomplete tasks:**
   - Show a warning with the count of incomplete tasks
   - Prompt the user to confirm whether to continue
   - Continue if the user confirms

   **If there is no tasks file:** continue directly without task-related warnings.

4. **Assess delta spec sync status**

   Use only `artifactPaths.specs.existingOutputPaths` from the status JSON as the delta-spec source. If the `specs` entry is missing or `existingOutputPaths` is empty, continue directly without a sync prompt; do not infer delta specs from other artifacts.

   **If there are delta specs:**
   - Compare each delta spec with its corresponding main spec (at `<planningHome.root>/openspec/specs/<capability>/spec.md`) (use the store-aware `planningHome.root` from step 2, not a hardcoded repository path)
   - Determine which changes will be applied (added, modified, removed, renamed)
   - Show a consolidated summary before prompting

   **Prompt options:**
   - If changes are needed: "Sync now (recommended)", "Archive without syncing"
   - If already synced: "Archive now", "Sync anyway", "Cancel"

   Route based on the answer:
   - "Cancel" — stop, do not archive
   - "Archive without syncing" or "Archive now" — proceed to archiving
   - "Sync now" or "Sync anyway" — sync, then verify (see below)
   - Anything else — ask again instead of archiving

   Before the selected sync writes to any main spec, run `openspec instructions specs --change "<name>" --json` once, using the same selected root flag. Require a zero exit status and valid artifact-instruction JSON. If the lookup fails or returns invalid JSON, report the error and stop before writing to any main spec or moving the change. A valid response that omits `rules` counts as a no-rules case. Apply the returned `rules` only to the content and form of the main specs produced by this merge; do not use them as archive guidance, do not change CLI behavior, and do not copy the rule text into any output file.

   Then run the `/opsx:sync` workflow inline (agent-driven smart merge) for change '<name>', passing the delta-spec analysis above and the fetched specs-rule snapshot, and wait for it to complete. The inline sync must reuse that snapshot without fetching the `specs` instruction again. Do not delegate it to a background task — step 5 would move `changeRoot` while the sync is still reading it, archiving the change while the main spec is never updated. If your agent can only run it by delegating, delegate the sync and wait for the result.

   Then, for every capability with a delta spec in `artifactPaths.specs.existingOutputPaths`, re-run the comparison from the start of this step — not just the ones the sync reported touching. A successful sync should have completed everything that needed applying, so each capability must now read as synced:
   - ADDED requirements exist
   - MODIFIED requirements contain the scenario and description changes named in the delta, with other scenarios intact
   - REMOVED requirements are gone
   - RENAMED requirements exist under the new name and not under the old name

   If the sync fails, or any capability does not match, report the differences and stop — do not archive. Nothing has been moved and `changeRoot` is intact, so the user can fix the mismatch or re-run the sync and start archiving again.

5. **Perform the archive**

   If no `archive` directory exists under `planningHome.changesDir`, create it:
   ```bash
   mkdir -p "<planningHome.changesDir>/archive"
   ```

   Generate the target name: if the change name already starts with a `YYYY-MM-DD-` prefix, use it as-is; otherwise prepend the current date: `YYYY-MM-DD-<change-name>`. Never stack a second date (same rule as `openspec archive`).

   **Check whether the target already exists:**
   - If it does: fail with an error and suggest renaming the existing archive or using a different date
   - If it does not: move `changeRoot` to the archive directory

   ```bash
   mv "<changeRoot>" "<planningHome.changesDir>/archive/<target-name>"
   ```

6. **Show the summary**

   Display the archive completion summary, including:
   - Change name
   - Schema used
   - Archive location
   - Spec sync status (synced / sync skipped / no delta specs)
   - Notes about any warnings (incomplete artifacts/tasks)

**Output on success**

```markdown
## Archive complete

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** archive path derived from `planningHome.changesDir`/<target-name>/
**Specs:** ✓ synced to main specs

All artifacts are complete. All tasks are complete.
```

**Output on success (no delta specs)**

```markdown
## Archive complete

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** archive path derived from `planningHome.changesDir`/<target-name>/
**Specs:** no delta specs

All artifacts are complete. All tasks are complete.
```

**Output on success (with warnings)**

```markdown
## Archive complete (with warnings)

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** archive path derived from `planningHome.changesDir`/<target-name>/
**Specs:** sync skipped (user chose to skip)

**Warnings:**
- Archived with 2 incomplete artifacts
- Archived with 3 incomplete tasks
- Delta spec sync skipped (user chose to skip)

If this was not intentional, please check the archive.
```

**Output on error (archive already exists)**

```markdown
## Archive failed

**Change:** <change-name>
**Target:** archive path derived from `planningHome.changesDir`/<target-name>/

The target archive directory already exists.

**Options:**
1. Rename the existing archive
2. Delete the existing archive (if it is a duplicate)
3. Wait until a different date to archive
```

**Guardrails**
- State the selected change; prompt for selection when ambiguous
- Use the artifact graph (openspec status --json) for completion checks
- Do not block archiving on warnings — only notify and confirm
- Preserve .openspec.yaml when moving to the archive (it moves with the directory)
- Show a clear summary of what happened
- If sync is requested, run the `/opsx:sync` workflow inline (agent-driven)
- Never archive while spec sync is still in progress — run the sync inline and verify the main specs before moving `changeRoot`
- If delta specs exist, always run the sync assessment and show a consolidated summary before prompting
- Apply relevant runtime context and report conflicts; operation guidance stays advisory
- Consider each guidance item and explain any advice that does not apply or conflicts
- Existing CLI checks, resolved paths, prompts, and command conventions remain unchanged
- Artifact rules only constrain the specs being written, never operation guidance
- Never copy runtime context, operation guidance, or artifact-rule text verbatim into output files

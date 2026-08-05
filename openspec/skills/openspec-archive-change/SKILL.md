---
name: openspec-archive-change
description: Archive a completed change in an experimental workflow. Use when the user needs to finalize and archive a change after implementation is complete.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires the openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.7.0"
---

Archive a completed change in an experimental workflow.

**Store selection**: If the user specified a store (a store is a separate OpenSpec repository registered on this machine) or the current work is in a store, run `openspec store list --json` to find the registered store ID, then pass `--store <id>` on commands that read and write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `view`). Other commands do not accept this flag. The prompts printed by commands already include this flag; keep using it in subsequent commands. If no store is specified, commands operate on the nearest local `openspec/` root.

**Input**: Optionally specify a change name. If omitted, check whether it can be inferred from the conversation context. If unclear or ambiguous, you must prompt the user to select from the available changes.

**Steps**

1. **Select the change**

   If a name was provided, use it directly. Otherwise:
   - Infer from the conversation context whether the user mentioned a change
   - If only one active change exists, select it automatically
   - If ambiguous, run `openspec list --json` to get the list of available changes and let the user choose

   When prompting, only show active changes (not archived).
   If available, include the schema used by each change.

   Always state: "Using change: <name>" and how to override (e.g. `/opsx:archive <other>`).

   **Load the archive input before the existing archive checks:**

   After resolving the selected change and planning root, run:
   ```bash
   openspec instructions archive --change "<name>" --json
   ```
   Keep the same selected root flag on this command. This lookup is advisory and optional:
   it only provides additional prompt input, so it must never block archiving.
   If it exits non-zero or returns invalid JSON — for example on an older CLI that does not
   support this command yet — continue the archive workflow without context and operation guidance.
   Do not report an error, do not stop.

   A successful response may omit the two optional fields. Treat `context` as required prompt-level input:
   read and consider it, applying relevant project facts, conventions, and constraints.
   Treat `operationGuidance` as optional advisory advice: read and consider each item,
   following the ones that apply and are compatible with the built-in archive workflow.

   Keep these two fields separate from the built-in steps, explicit user choices, resolved paths,
   CLI checks, and command contracts. If context conflicts with a control input,
   report the conflict and keep the control value. If guidance does not apply or conflicts with control inputs,
   do not follow it and explain why. Do not infer alternative paths, skipped prompts, or flags from either field,
   and do not copy their text verbatim into specs, change artifacts, or archive summaries,
   unless the user separately asks. These are prompt-level behavioral contracts, not enforceable checks.

2. **Check artifact completion status**

   Run `openspec status --change "<name>" --json` to check artifact completion status.

   Parse the JSON to understand:
   - `schemaName`: the workflow in use
   - `planningHome`, `changeRoot`, `artifactPaths`, and `actionContext`: path and scope context
   - `artifacts`: the artifact list and their statuses (`done`, `skipped`, or other)

   **If any artifact is neither `done` nor `skipped`** (a skipped artifact satisfies the requirement — the change declares skip_specs):
   - Show a warning listing the incomplete artifacts
   - Ask the user to confirm whether to continue
   - Continue once the user confirms

3. **Check task completion status**

   Read the tasks file (usually `tasks.md`) to check for incomplete tasks.

   Count the tasks marked `- [ ]` (incomplete) and `- [x]` (complete).

   **If incomplete tasks are found:**
   - Show a warning with the count of incomplete tasks
   - Ask the user to confirm whether to continue
   - Continue once the user confirms

   **If no tasks file exists:** continue without showing task-related warnings.

4. **Assess delta spec sync status**

   Use only `artifactPaths.specs.existingOutputPaths` from the status JSON
   as the delta-spec source. If the `specs` entry is missing or
   `existingOutputPaths` is empty, continue without a sync prompt,
   and do not infer delta specs from other artifacts.

   **If delta specs exist:**
   - Compare each delta spec with the corresponding main spec at `<planningHome.root>/openspec/specs/<capability>/spec.md` (use the store-aware `planningHome.root` from step 2, not a hardcoded repo path)
   - Determine the changes to apply (added, modified, removed, renamed)
   - Show a merge summary before prompting

   **Prompt options:**
   - If changes are needed: "Sync now (recommended)", "Archive without syncing"
   - If already synced: "Archive now", "Sync anyway", "Cancel"

   Route based on the answer:
   - "Cancel" — stop, do not archive
   - "Archive without syncing" or "Archive now" — proceed to archiving
   - "Sync now" or "Sync anyway" — sync, then verify (see below)
   - Anything else — ask again rather than archiving

   Before the selected sync writes to any main spec, run
   `openspec instructions specs --change "<name>" --json` once,
   using the same selected root flag. Require a zero exit status and valid artifact-instruction
   JSON. If the lookup fails or returns invalid JSON, report the error and stop before writing to any main spec
   or moving the change. A valid response that omits `rules` is a no-rules case.
   Apply the returned `rules` only to the content and form of the main specs produced by this merge;
   do not use them as archive guidance, do not change CLI behavior, and do not copy the rule text into any output file.

   Then run the `openspec-sync-specs` workflow inline (agent-driven smart merge) for change '<name>',
   passing the delta-spec analysis above and the fetched specs-rule snapshot, and wait for it to complete.
   The inline sync must reuse that snapshot without fetching the `specs` instruction again. Do not delegate it to a
   background task — step 5 would move `changeRoot` while the sync is still reading it,
   archiving the change while the main specs are never updated. If your agent can only run it via delegation,
   delegate the sync and wait for the result.

   Then re-run the comparison at the top of this step for every capability with a delta spec in
   `artifactPaths.specs.existingOutputPaths` — not just the ones the sync reported touching.
   A successful sync should leave no changes pending, so each capability
   must now read as synced:
   - ADDED requirements exist
   - MODIFIED requirements contain the scenario and description changes named in the delta, with other scenarios intact
   - REMOVED requirements are gone
   - RENAMED requirements exist under the new name and not under the old name

   If the sync fails, or any capability does not match, report the differences and stop — do not archive.
   Nothing has been moved and `changeRoot` is intact, so the user can fix the mismatch or
   re-run the sync and start archiving again.

4.5 **Commit the post-sync specs**

   If `openspec sync` modified main spec files (`openspec/specs/**/*.md`), show the sync summary and prompt to commit:

   ```markdown
   ## Sync Result Summary

   | Capability | Delta operation | Main specs change |
   |:---|:---|:---|
   | <cap> | ADDED: "<name>" | Added §X.Y |
   | <cap> | MODIFIED: "<name>" | §X.Y updated |
   | <cap> | REMOVED: "<name>" | §X.Y removed |

   Suggested command: git add openspec/specs/ && git commit -m "docs(spec): sync <change-name>"
   ```

   **Important**: the user must commit the synced main specs before archiving. The archive operation moves the change directory but does not automatically commit the updated specs. If the user skips this step, the updated main specs will remain as uncommitted changes.

5. **Perform the archive**

   If it does not exist, create the `archive` directory under `planningHome.changesDir`:
   ```bash
   mkdir -p "<planningHome.changesDir>/archive"
   ```

   Generate the target name: if the change name already starts with a `YYYY-MM-DD-` prefix, use it as-is;
   otherwise prepend the current date: `YYYY-MM-DD-<change-name>`. Never stack a second date (same rule as `openspec archive`).

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
   - Whether specs were synced (if applicable)
   - Notes about any warnings (incomplete artifacts/tasks)

**Output on success**

```markdown
## Archive complete

**Change:** <change-name>
**Schema:** <schema-name>
**Archived to:** archive path derived from `planningHome.changesDir`/<target-name>/
**Specs:** <show "✓ synced to main specs" only if step 4 verified it; otherwise "no delta specs" or "sync skipped">

<"All artifacts are complete. All tasks are complete." — or, if archiving with warnings, list them instead (e.g. "archived with 2 incomplete tasks")>
```

**Guardrails**
- State the selected change; prompt for selection when ambiguous
- Use the artifact graph (openspec status --json) for completion checks
- Do not block archiving on warnings — only notify and confirm
- Preserve .openspec.yaml when moving to the archive (it moves with the directory)
- Show a clear summary
- If sync is requested, run the `openspec-sync-specs` workflow inline (agent-driven)
- Never archive while spec sync is still in progress — run the sync inline and verify the main specs before moving `changeRoot`
- If delta specs exist, always run the sync assessment and show the merge summary before prompting
- Apply relevant runtime context and report conflicts; operation guidance stays advisory
- Consider each guidance item and explain advice that does not apply or conflicts
- Existing CLI checks, resolved paths, prompts, and command contracts remain unchanged
- Artifact rules only constrain the specs being written, never act as operation guidance
- Never copy runtime context, operation guidance, or artifact-rule text verbatim into output files

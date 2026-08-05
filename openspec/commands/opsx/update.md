---
name: "OPSX: Update"
description: "Update a change - revise existing planning artifacts and keep them consistent (experimental)"
allowed-tools: Bash(openspec:*)
category: "Workflow"
tags: ["workflow", "artifacts", "experimental"]
---

Revise the existing planning artifacts of a change and keep them consistent. Never edit code.

**Store selection:** If the user specified a store (a store is a separate OpenSpec repository registered on this machine), or the current work is in a store, run `openspec store list --json` to discover the registered store id, then pass `--store <id>` on commands that read and write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `view`). Other commands do not accept this flag. The prompts printed by commands already include this flag; keep it in subsequent operations. If there is no store, commands operate on the nearest local `openspec/` root.

**Input:** Optionally specify a change name after `/opsx:update` (e.g. `/opsx:update add-auth`). If omitted, check whether it can be inferred from the conversation context. If unclear or ambiguous, you must prompt for the available changes.

**Steps**

1. **Select the change**

   If a name was provided, use it. Otherwise:
   - If the user mentioned a change in the conversation, infer it from context
   - If only one active change exists, select it automatically
   - If unclear, run `openspec list --json` to get the available changes (sorted by most recently modified) and let the user choose

   When prompting, show the 3-4 most recently modified changes as options, displaying:
   - Change name
   - Schema (from the `schema` field, if present; otherwise "spec-driven")
   - Status (e.g. "0/5 tasks", "complete", "no tasks")
   - Most recent modification time (from the `lastModified` field)

   Mark the most recently modified change as "(recommended)", since it is the most likely one the user wants to update.

   Always state: "Using change: <name>" and how to override (e.g. `/opsx:update <other>`).

2. **Get the change's artifacts**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to understand the current state. The response includes:
   - `schemaName`: the workflow schema in use (e.g. "spec-driven")
   - `artifacts`: the artifact array with their statuses ("done", "skipped", "ready", "blocked")
   - `isComplete`: a boolean indicating whether all artifacts are complete
   - `planningHome`, `changeRoot`, `artifactPaths`, and `actionContext`: path and scope context. Use these instead of assuming repository-local paths.

   Artifact ids and paths come from the active schema — do not assume them and do not branch on hardcoded artifact names. Custom schemas must work unchanged.

   The files to edit are `artifactPaths.<id>.existingOutputPaths` — the concrete files that exist on disk, already glob-expanded for glob artifacts (e.g. `specs/**/*.md`). Do not write to `resolvedOutputPath`: for glob artifacts it is still a glob pattern, not a real file.

3. **Understand the request**
   - If the user requested a specific revision ("the design now uses X"), that is the starting edit.
   - If the user just says "update" / "make this coherent", treat it as a consistency review: read the existing artifacts and cross-check them against each other for contradictions, gaps, and duplication.

4. **Read and reconcile**
   - Read the artifacts involved in the request plus the change's other existing artifacts.
   - Apply the requested edit. Then check it against every other existing artifact — in *either* direction: an edit to a later artifact may require revising an earlier one, and not just the reverse. The build order is a useful reading order, not a constraint on which artifacts can be revised.
   - Note everything that is now inconsistent, missing, or contradictory.
   - Only revise files that already exist (`existingOutputPaths`). Do not create artifacts that do not exist yet, and do not invent new files under glob artifacts — note them and point the user to `/opsx:continue` to create them.
   - If the change is already consistent, say so and make no edits.

5. **Confirm and apply, one artifact at a time**
   - Show each proposed revision with its rationale. Only write after the user confirms.
   - If the user rejects a revision, do not write it — leave that artifact unchanged.
   - When a major rewrite is needed, first fetch the artifact's rules and template:
     ```bash
     openspec instructions <artifact-id> --change "<name>" --json
     ```

6. **Point to the next step (guidance only — never execute)**
   - Artifacts still missing -> suggest `/opsx:continue` to create them.
   - Change already implemented (tasks checked / applied) -> the code may no longer match the revised plan; suggest `/opsx:apply` to bring the delta into the code.
   - Everything complete and implemented -> suggest `/opsx:archive`.

**Output**

After each invocation, show:
- Which artifacts were revised (and which proposed revisions were rejected)
- Anything deferred to `/opsx:continue` (artifacts or files not yet created)
- The change's current status and the recommended next command

**Guardrails**
- Planning artifacts only — never edit implementation code. If the revised plan implies code changes, stop and point to `/opsx:apply`.
- Use the artifact ids and paths reported by `openspec status`; never branch on hardcoded artifact names.
- Only edit the concrete files in `existingOutputPaths`; never write to a glob `resolvedOutputPath`.
- Do not advance the build frontier: no new artifacts, no new files under glob artifacts — that is `/opsx:continue`'s job.
- Confirm each edit with the user before writing.
- If the request changes the *intent* of the change rather than refining it, suggest starting over with `/opsx:new` (the "update vs. start over" heuristic).
- `/opsx:continue` and `/opsx:new` may not be installed (core profile). When suggesting an unavailable command, point to the CLI instead: `openspec status --change "<name>" --json` shows the next artifact, and `openspec instructions <artifact-id> --change "<name>" --json` explains how to create it.

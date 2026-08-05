---
name: "OPSX: Apply"
description: "Implement tasks in an OpenSpec change (experimental)"
allowed-tools: Bash(openspec:*)
category: "Workflow"
tags: ["workflow", "artifacts", "experimental"]
---

Implement the tasks in an OpenSpec change.

**Store selection:** If the user specified a store (a store is a separate OpenSpec repository registered on this machine), or the work belongs to a store, run `openspec store list --json` to discover the registered store id, then pass `--store <id>` on commands that read and write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `view`). Other commands do not accept this flag. The prompts printed by commands already include this flag; keep it in subsequent operations. If there is no store, commands operate on the nearest local `openspec/` root.

**Input:** Optionally specify a change name after `/opsx:apply` (e.g. `/opsx:apply add-auth`). If omitted, check whether it can be inferred from the conversation context. If unclear or ambiguous, you must prompt the user to choose from the available changes.

**Steps**

1. **Select the change**

   If a name was provided, use it directly. Otherwise:
   - Infer it from the conversation context (if the user mentioned a change)
   - If only one active change exists, select it automatically
   - If ambiguous, run `openspec list --json` to get the list of available changes and ask the user to choose

   Always state: "Using change: <name>" and how to override (e.g. `/opsx:apply <other>`).

2. **Check status to understand the schema**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to understand:
   - `schemaName`: the workflow in use (e.g. "spec-driven")
   - `planningHome`, `changeRoot`, and `actionContext`: planning scope and edit constraints
   - Which artifact contains the tasks (spec-driven is usually "tasks"; for other schemas, look at the status output)

3. **Get the apply instructions**

   ```bash
   openspec instructions apply --change "<name>" --json
   ```

   This command returns:
   - `contextFiles`: artifact ID -> array of concrete file paths (schema-dependent)
   - Progress (total, complete, remaining)
   - The task list with statuses
   - Dynamic instructions based on the current state
   - Optional `context`: current required project instruction input from the selected root
   - Optional `operationGuidance`: current advisory guidance for apply

   **Handle the various states:**
   - If `state: "blocked"` (missing artifacts): show the message, suggest using `/opsx:continue` (if not installed, run `openspec status --change "<name>" --json` to see the next artifact, and `openspec instructions <artifact-id> --change "<name>" --json` to learn how to create it)
   - If `state: "all_done"`: congratulate and suggest archiving
   - Otherwise: continue with implementation

   Treat `context` as required prompt-level input. Read and consider it, and apply relevant project facts, conventions, and constraints while implementing.
   Treat `operationGuidance` as optional additional advice. Read and consider each item, and follow those that apply and are compatible with the built-in workflow.

   Keep these two fields separate from the status, missing artifacts, tasks, progress, `contextFiles`, and built-in `instruction` returned by the CLI. They are not evidence of task completion, do not replace the built-in instruction, and do not allow bypassing the blocked state. If context conflicts with the built-in instruction, an explicit user choice, or CLI-controlled values, report the conflict and keep the control values. If guidance does not apply or conflicts with these control inputs, do not follow it and explain why. These are prompt-level behavioral conventions, not enforceable checks.

4. **Read the context files**

   Read each file path listed under `contextFiles` from the apply instruction output.
   The specific files depend on the schema in use:
   - **spec-driven**: proposal, specs, design, tasks
   - Other schemas: follow the contextFiles from the CLI output

   Do not copy `context` or `operationGuidance` verbatim into implementation files or planning artifacts unless the user separately asks for it.

5. **Show the current progress**

   Display:
   - The schema in use
   - Progress: "N/M tasks complete"
   - An overview of the remaining tasks
   - The CLI's dynamic instruction

6. **Implement tasks (loop until complete or blocked)**

   For each pending task:
   - Show which task is being processed
   - Make the required code changes
   - Keep changes minimal and focused
   - Mark the task complete in the tasks file: `- [ ]` → `- [x]`
   - Continue to the next task

   **Pause when:**
   - The task is unclear → request clarification
   - Implementation reveals a design issue → suggest updating the artifact
   - An error or blocker is encountered → report and wait for guidance
   - The user interrupts

7. **When finished or paused, show the status**

   Display:
   - Tasks completed in this session
   - Overall progress: "N/M tasks complete"
   - If all done: suggest archiving
   - If paused: explain why and wait for guidance

**Output while implementing**

```
## Implementing: <change-name> (schema: <schema-name>)

Working on task 3/7: <task description>
[...implementation in progress...]
✓ Task complete

Working on task 4/7: <task description>
[...implementation in progress...]
✓ Task complete
```

**Output on completion**

```
## Implementation complete

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 7/7 tasks complete ✓

### Completed this session
- [x] Task 1
- [x] Task 2
...

All tasks complete! You can archive this change with `/opsx:archive`.
```

**Output when paused (issue encountered)**

```
## Implementation paused

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 4/7 tasks complete

### Issue encountered
<issue description>

**Options:**
1. <option 1>
2. <option 2>
3. Another approach

How would you like to proceed?
```

**Guardrails**
- Keep driving tasks forward until complete or blocked
- Always read the context files (from the apply instruction output) before starting
- If a task is unclear, pause and ask before implementing
- If implementation reveals a problem, pause and suggest an artifact update
- Keep code changes minimal and scoped to each task
- Update the task checkbox immediately after completing each task
- Pause on errors, blockers, or unclear requirements — never guess
- Use the contextFiles from the CLI output; do not assume specific file names
- Do not treat context or operation guidance as evidence of task completion
- Apply relevant project context; report conflicts with control workflow inputs
- Consider each guidance item; explain any advice that does not apply or conflicts
- Do not copy runtime context or operation guidance into implementation files or planning artifacts
- Preserve CLI-controlled blocked/ready/all-done behavior and completion criteria

**Fluid workflow integration**

This skill supports the "operate on a change" model:

- **Callable at any time**: before all artifacts are complete (if tasks already exist), after partial implementation, interleaved with other operations
- **Artifact updates allowed**: if implementation reveals a design issue, suggest updating artifacts — no phase locking, work fluidly

---
name: openspec-apply-change
description: Implement the tasks in an OpenSpec change. Use when the user needs to start, continue, or complete the implementation of a change.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires the openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.7.0"
---

Implement the tasks in an OpenSpec change.

**Delegation mode**: If the project has a `pipeline/` skill directory (detection method: check that `pipeline/SKILL.md` exists), apply does not implement code itself. Instead, prompt the user:

  「OpenSpec apply detected that Pipeline is available. Pipeline provides quality-gate guarantees (type checking/lint/test coverage/semantic commits).
   Reply **pipeline** to run through the Pipeline, or **native** to use OpenSpec's native apply.」

If the user chooses `pipeline` → output the handoff instruction and exit: "Implement via the three-layer pipeline: openspec/changes/<name>/"
If the user chooses `native` → continue with the original flow below.

**Store selection**: If the user specified a store (a store is a separate OpenSpec repository registered on this machine) or the current work is in a store, run `openspec store list --json` to find the registered store ID, then pass `--store <id>` on commands that read and write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `view`). Other commands do not accept this flag. The prompts printed by commands already include this flag; keep using it in subsequent commands. If no store is specified, commands operate on the nearest local `openspec/` root.

**Input**: Optionally specify a change name. If omitted, check whether it can be inferred from the conversation context. If unclear or ambiguous, you must prompt the user to select from the available changes.

**Steps**

1. **Select the change**

   If a name was provided, use it directly. Otherwise:
   - Infer from the conversation context whether the user mentioned a change
   - If only one active change exists, select it automatically
   - If ambiguous, run `openspec list --json` to get the list of available changes and let the user choose

   Always state: "Using change: <name>" and how to override (e.g. `/opsx:apply <other>`).

2. **Check status to understand the schema**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to understand:
   - `schemaName`: the workflow in use (e.g. "spec-driven")
   - `planningHome`, `changeRoot`, and `actionContext`: planning scope and edit constraints
   - Which artifact contains the tasks (spec-driven is usually "tasks"; for other schemas, determine it from the status)

3. **Get the apply instructions**

   ```bash
   openspec instructions apply --change "<name>" --json
   ```

   Returns:
   - `contextFiles`: artifact ID → array of concrete file paths (schema-dependent — may be proposal/specs/design/tasks or spec/tests/implementation/docs)
   - Progress (total, complete, remaining)
   - The task list with statuses
   - Dynamic instructions based on the current state
   - Optional `context`: required project instruction input currently fetched from the selected root
   - Optional `operationGuidance`: advisory guidance for the current apply

   **Handle states:**
   - If `state: "blocked"` (missing artifacts): show the message and suggest openspec-continue-change (if not installed, run `openspec status --change "<name>" --json` to see the next artifact, and `openspec instructions <artifact-id> --change "<name>" --json` to learn how to create it)
   - If `state: "all_done"`: congratulate and suggest archiving
   - Otherwise: enter the implementation phase

   Treat `context` as required prompt-level input. Read and consider it,
   and apply relevant project facts, conventions, and constraints while implementing.
   Treat `operationGuidance` as optional advisory advice. Read and consider each item,
   and follow the ones that apply and are compatible with the built-in workflow.

   Keep these two fields separate from the status, missing artifacts, tasks,
   progress, `contextFiles`, and built-in `instruction` returned by the CLI. They are not
   evidence of task completion, do not replace the built-in instruction, and do not allow
   bypassing the blocked state. If context conflicts with the built-in instruction, an
   explicit user choice, or a CLI-controlled value, report the conflict and keep the control value.
   If guidance does not apply or conflicts with control inputs, do not follow it and explain why.
   These are prompt-level behavioral contracts, not enforceable checks.

4. **Read the context files**

   Read every file path listed under `contextFiles` in the apply instruction output.
   The files depend on the schema in use:
   - **spec-driven**: proposal, specs, design, tasks
   - Other schemas: follow the contextFiles from the CLI output

   Unless the user separately asks for it, do not copy `context` or `operationGuidance`
   verbatim into implementation files or planning artifacts.

5. **Show the current progress**

   Display:
   - The schema in use
   - Progress: "N/M tasks complete"
   - An overview of the remaining tasks
   - The CLI's dynamic instruction

6. **Implement tasks (loop until complete or blocked)**

   For each pending task:
   - Show the task being processed
   - Make the required code changes
   - Keep changes minimal and focused
   - Mark it complete in the tasks file: `- [ ]` → `- [x]`
   - Continue to the next task

   **Pause conditions:**
   - The task is unclear → request clarification
   - Implementation exposes a design issue → suggest updating the artifacts
   - An error or blocker is encountered → report and wait for guidance
   - The user interrupts

7. **Show status when finished or paused**

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

All tasks complete! You can archive this change.
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
- Keep executing tasks until complete or blocked
- Always read the context files (from the apply instruction output) before starting
- If a task is unclear, pause and ask before implementing
- If implementation exposes a problem, pause and suggest updating the artifacts
- Keep code changes minimal and focused on each task
- Update the task checkbox immediately after completing a task
- Pause on errors, blockers, or unclear requirements — never guess
- Use the contextFiles from the CLI output; do not assume specific file names
- Do not treat context or operation guidance as evidence of task completion
- Apply relevant project context; report conflicts with control workflow inputs
- Consider each guidance item; explain advice that does not apply or conflicts
- Do not copy runtime context or operation guidance into implementation files or planning artifacts
- Preserve CLI-controlled blocked/ready/all-done behavior and completion criteria

**Fluid workflow integration**

This skill supports the "operate on a change" model:

- **Callable at any time**: before all artifacts are complete (if tasks already exist), after partial implementation, interleaved with other operations
- **Artifact updates allowed**: if implementation exposes a design issue, suggest updating artifacts — no phase locking, work fluidly

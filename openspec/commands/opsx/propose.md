---
name: "OPSX: Propose"
description: "Propose a new change - create the change and generate all artifacts in one step"
allowed-tools: Bash(openspec:*)
category: "Workflow"
tags: ["workflow", "artifacts", "experimental"]
---

Propose a new change - create the change and generate all artifacts in one step.

I will create a change using the artifacts defined by your schema. For the default spec-driven schema, that is:
- proposal.md (what & why)
- `specs/<capability>/spec.md` (what the system must do - a delta, not the main spec)
- design.md (how)
- tasks.md (implementation steps)

When ready to implement, run /opsx:apply

---

**Store selection:** If the user specified a store (a store is a separate OpenSpec repository registered on this machine), or the current work is in a store, run `openspec store list --json` to discover the registered store id, then pass `--store <id>` on commands that read and write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `view`). Other commands do not accept this flag. The prompts printed by commands already include this flag; keep it in subsequent operations. If there is no store, commands operate on the nearest local `openspec/` root.

**Input:** The arguments after `/opsx:propose` are the change name (kebab-case) or a description of what the user wants to build.

**Steps**

1. **If no input was provided, ask the user what they want to build**

   Ask the user (open-ended, no preset options):
   > "What change do you want to make? Describe what you want to build or fix."

   From their description, derive a kebab-case name (e.g., "add user authentication" → `add-user-auth`).

   **Important**: do not continue before understanding what the user wants to build.

2. **Create the change directory**
   ```bash
   openspec new change "<name>"
   ```
   This creates a scaffolded change in the planning home resolved by the CLI through `.openspec.yaml`.

3. **Get the artifact build order**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to get:
   - `applyRequires`: the array of artifact IDs required before implementation (e.g. `["tasks"]`)
   - `artifacts`: the list of all artifacts, each with its `status` and `requires` edges (the artifact IDs it directly depends on)
   - `planningHome`, `changeRoot`, `artifactPaths`, and `actionContext`: path and scope context. Use these instead of assuming repository-local paths.

4. **Create every artifact in the required set**

   Use a todo list to track artifact progress.

   Loop over artifacts in dependency order (artifacts with no pending dependencies first):

   a. **For each artifact in the `ready` state (dependencies satisfied)**:
      - Fetch the instructions:
        ```bash
        openspec instructions <artifact-id> --change "<name>" --json
        ```
      - The instruction JSON includes:
        - `context`: project background (constraints for you — do not include in the output)
        - `rules`: artifact-specific rules (constraints for you — do not include in the output)
        - `template`: the structure for the output file
        - `instruction`: schema-specific guidance for this artifact type
        - `skipped`/`warning`: present when the change declares skip_specs and this artifact must not be created — stop and choose another artifact
        - `resolvedOutputPath`: the resolved path or pattern to write the artifact to
        - `dependencies`: completed artifacts that need to be read for context
      - Read any completed dependency files for context — always re-read them from disk, even if you saw them earlier in the conversation (the user may have edited them)
      - If the `instruction` field delegates creation to a specific skill or command, invoke it to generate the artifact instead of writing the file yourself, then verify the artifact file exists at `resolvedOutputPath`
      - Otherwise, create the artifact file using `template` as the structure and write it to `resolvedOutputPath`. If `resolvedOutputPath` is a glob pattern, follow `instruction` to choose the concrete file path
      - Apply `context` and `rules` as constraints — but do not copy them into the file
      - Show brief progress: "Created <artifact-id>"

   b. **Keep creating until every artifact in the required set exists (not just `apply.requires`)**
      - After creating each artifact, re-run `openspec status --change "<name>" --json`
      - The required set is `applyRequires` plus every artifact reachable from them by following the `requires` edges in `status --json` — traverse them transitively (spec-driven closes over proposal, specs, design, tasks). Exclude artifacts not in that set
      - `status` is based only on file existence, so an artifact showing `done` in `applyRequires` does not mean its dependencies exist — writing `tasks.md` early marks `tasks` as done while `specs` was never written. Use each artifact's `requires` edges, not its `status`, to build the required set: a `done` artifact still lists what it depends on
      - An artifact already showing `status: "skipped"` is satisfied: the change declares `skip_specs` in `.openspec.yaml`, so its file must not exist. Never try to create it
      - Create every missing artifact in the required set, then re-check — creating one may unlock others
      - Skip an artifact only when `status` reports it as `skipped`, or its own `instruction` marks it conditional: run `openspec instructions <artifact-id> --change "<name>" --json` and skip only if its `instruction` field marks it optional (e.g. "create only when…"). Spec-driven `design.md` qualifies; `specs` qualifies only through the `skipped` status above — never skip it on your own judgment. Inform the user, and do not reconsider it
      - Dependencies are enablers, not gates: if a required artifact is still `blocked` only because you skipped a conditional dependency, still write it
      - Stop when every artifact in the required set is `done`, `skipped`, or intentionally skipped

   c. **If an artifact needs user input** (context is unclear):
      - Ask the user to clarify
      - Then continue creating

5. **Show the final status**
   ```bash
   openspec status --change "<name>"
   ```

**Output**

After completing all artifacts, summarize:
- The change name and location
- The list of created artifacts with brief descriptions, plus any conditional artifacts you skipped and why
- Readiness: "All artifacts required for implementation are ready."
- Prompt: "Run `/opsx:apply` to start implementation."

**Artifact creation guidelines**

- For each artifact type, follow the `instruction` field returned by `openspec instructions` — it is the authoritative guidance even for familiar artifact names
- If the `instruction` field directs you to use a specific skill or command to create the artifact, invoke it instead of writing the artifact directly
- The schema defines what each artifact should contain — follow it
- Read dependency artifacts for context before creating a new artifact
- Use `template` as the structure for the output file — fill in its sections
- **Important**: `context` and `rules` are constraints for you, not file content
  - Do not copy the `<context>`, `<rules>`, or `<project_context>` blocks into artifacts
  - They guide what you write but must never appear in the output

**Guardrails**
- Create every artifact that is a transitive dependency of the apply phase, not just the ids listed in `apply.requires`
- Always read dependency artifacts before creating a new artifact — re-read from disk, not from conversation memory (files may have changed since you last saw them)
- If the context is severely unclear, ask the user — but prefer making a reasonable decision to keep momentum
- If a change with that name already exists, ask whether the user wants to continue it or create a new one
- Verify each artifact file exists after writing it before moving to the next

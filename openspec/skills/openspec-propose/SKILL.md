---
name: openspec-propose
description: Create a new change and generate all artifacts in one step. Use when the user wants to quickly describe what to build and receive a complete proposal with design, specs, and tasks ready for implementation.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires the openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.7.0"
---

Create a new change — create the change and generate all artifacts in one step.

I will create a change using the artifacts defined by your schema. With the default spec-driven schema, that includes:
- proposal.md (what & why)
- `specs/<capability>/spec.md` (what the system must do — a delta, not the main spec)
- design.md (how)
- tasks.md (implementation steps)

When ready to implement, run `/opsx:apply`

---

**Store selection**: If the user specified a store (a store is a separate OpenSpec repository registered on this machine) or the current work is in a store, run `openspec store list --json` to find the registered store ID, then pass `--store <id>` on commands that read and write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `view`). Other commands do not accept this flag. The prompts printed by commands already include this flag; keep using it in subsequent commands. If no store is specified, commands operate on the nearest local `openspec/` root.

**Input**: The user's request should include a change name (kebab-case) or a description of what to build.

**Steps**

1. **If there is no clear input, ask the user what to build**

   Ask the user (open-ended, no preset options):
   > "What change do you want to make? Describe what you want to build or fix."

   Derive a kebab-case name from the description (e.g. "add user authentication" → `add-user-auth`).

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
   - `planningHome`, `changeRoot`, `artifactPaths`, and `actionContext`: path and scope context. Use these instead of assuming repo-local paths.

4. **Create every artifact in the required set**

   Use a todo list to track artifact progress.

   Loop over artifacts in dependency order (artifacts with no pending dependencies first):

   a. **For each artifact with status `ready` (dependencies satisfied)**:
      - Fetch the instructions:
        ```bash
        openspec instructions <artifact-id> --change "<name>" --json
        ```
      - The instruction JSON contains:
        - `context`: project background (constraints for you — do not write into the output)
        - `rules`: artifact-specific rules (constraints for you — do not write into the output)
        - `template`: the structure template for the output file
        - `instruction`: schema-specific guidance for this artifact type
        - `skipped`/`warning`: present when the change declares skip_specs and this artifact must not be created — stop and choose another artifact
        - `resolvedOutputPath`: the resolved path or pattern to write the artifact to
        - `dependencies`: completed artifacts to read for context
      - Read any completed dependency files as context — always re-read from disk, even if seen earlier in the conversation (the user may have edited them)
      - If the `instruction` field delegates creation to a specific skill or command, invoke it to generate the artifact instead of writing the file yourself, then verify the artifact file exists at `resolvedOutputPath`
      - Otherwise create the artifact file using `template` as the structure and write it to `resolvedOutputPath`. If `resolvedOutputPath` is a glob, follow `instruction` to choose the concrete file path
      - Apply `context` and `rules` as constraints — but do not copy them into the file
      - Show brief progress: "Created <artifact-id>"

   b. **Keep going until every artifact in the required set exists (not just `apply.requires`)**
      - After creating each artifact, re-run `openspec status --change "<name>" --json`
      - The required set is `applyRequires` plus every artifact reachable from them through the `requires` edges in `status --json` — transitive closure traversal (the spec-driven closure covers proposal, specs, design, tasks). Artifacts outside the set are not processed
      - `status` is based only on file existence, so an artifact in `applyRequires` showing `done` does not mean its dependencies exist — writing `tasks.md` early marks `tasks` as done while `specs` was never written. Use each artifact's `requires` edges rather than its `status` to build the required set: a `done` artifact still lists its dependencies
      - An artifact showing `status: "skipped"` is satisfied: the change declares `skip_specs` in `.openspec.yaml`, so its file must not exist. Never try to create it
      - Create every missing artifact in the required set, then re-check — creating one may unlock others
      - Skip an artifact only when `status` reports it as `skipped`, or its `instruction` explicitly marks it conditional: run `openspec instructions <artifact-id> --change "<name>" --json` and skip only if its `instruction` field marks it optional (e.g. "create only when..."). Spec-driven `design.md` qualifies; `specs` is skipped only through the `skipped` status above — never by your own judgment. Inform the user, and do not reconsider
      - Dependencies are enablers, not gates: if a required artifact is still `blocked` only because a conditional dependency was skipped, still write it
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
- The list of created artifacts with brief descriptions, plus any conditional artifacts skipped and why
- Readiness: "All artifacts required for implementation are ready."
- Prompt: "Run `/opsx:apply` to tell me to start implementing the tasks."

**Artifact creation guidelines**

- Follow the `instruction` field for each artifact type from `openspec instructions` — it is the authoritative guidance even for familiar artifact names
- If the `instruction` field directs you to use a specific skill or command to create the artifact, invoke it instead of writing the file directly
- The schema defines what each artifact should contain — follow it
- Read dependency artifacts as context before creating a new artifact
- Use `template` as the structure for the output file — fill in its sections
- **Important**: `context` and `rules` are constraints for you, not file content
  - Do not copy the `<context>`, `<rules>`, or `<project_context>` blocks into artifacts
  - They guide what you write but must never appear in the output

**Tasks.md enhancement (for Pipeline consumption)**

When creating `tasks.md`, each task entry must include the following extra fields for the Pipeline to consume directly:

```markdown
### T001: <task name>
- **Target file**: <suggested file path, e.g. src/services/auth_service.py>
- **Target symbol**: <suggested function/class name, e.g. AuthService.login>
- **Depends on**: <prerequisite task ID, e.g. T001>, or "none"
- **Description**: <task description>
```

Field notes:
- `Target file` (required): best-guess target file path. Pipeline Node 3 uses it as a file search hint
- `Target symbol` (required): best-guess target symbol name. Pipeline Node 3 uses it as a symbol search hint
- `Depends on` (required): an explicit dependency on another task ID, or "none"

**Specs type precision (for Pipeline L2 contract checks)**

When creating specs (the delta specs in `specs/<capability>/spec.md`), enforce type precision in the interface contracts:

- **Forbidden**: `any`, `object`, `unknown` as parameter or return value types
- **Required**: concrete JSON types (`string`, `number`, `boolean`, `array`, `object` with a specified shape) or language-specific types (`int`, `str`, `list[User]`, `Optional[str]`)
- If the PRD does not specify the type precisely, the AI must infer the most likely type and mark it `[AI_REFINED]`
- If the type cannot be inferred with ≥ 80% confidence, mark it `[AMBIGUOUS_TYPE]` and ask the user

**Guardrails**
- Create every artifact that is a transitive dependency of the apply phase, not just the IDs listed in `apply.requires`
- Always read dependency artifacts before creating a new artifact — re-read from disk, not from conversation memory (files may have changed)
- If the context is severely unclear, ask the user — but prefer making a reasonable decision to keep momentum
- If a change with that name already exists, ask whether the user wants to continue it or create a new one
- Verify the file exists after writing each artifact before moving to the next

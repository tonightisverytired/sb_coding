---
name: "OPSX: Sync"
description: "Sync delta specs from a change to the main specs"
allowed-tools: Bash(openspec:*)
category: "Workflow"
tags: ["workflow", "specs", "experimental"]
---

Sync the delta specs from a change to the main specs.

This is an **agent-driven** operation — you read the delta specs and edit the main specs directly to apply the changes. This enables intelligent merging (for example, adding a scenario without duplicating an entire requirement).

**Store selection:** If the user specified a store (a store is a separate OpenSpec repository registered on this machine), or the current work is in a store, run `openspec store list --json` to discover the registered store id, then pass `--store <id>` on commands that read and write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`, `view`). Other commands do not accept this flag. The prompts printed by commands already include this flag; keep it in subsequent operations. If there is no store, commands operate on the nearest local `openspec/` root.

**Input:** Optionally specify a change name after `/opsx:sync` (e.g. `/opsx:sync add-auth`). If omitted, check whether it can be inferred from the conversation context. If unclear or ambiguous, you must prompt for the available changes.

**Steps**

1. **Select the change**

   If a name was provided, use it. Otherwise:
   - If the user mentioned a change in the conversation, infer it from context
   - If only one active change exists, select it automatically
   - If unclear, run `openspec list --json` to get the available changes and let the user choose

   When prompting, show changes that have delta specs (under the `specs/` directory).

   Always state: "Using change: <name>" and how to override (e.g. `/opsx:sync <other>`).

2. **Resolve the change context**

   Run:
   ```bash
   openspec status --change "<name>" --json
   ```

   The JSON includes `planningHome.root`. Main specs live under `<planningHome.root>/openspec/specs/` — use that (store-aware) root for every main spec path below, rather than a hardcoded repository path. When a store is selected, it points to the store, not the current repository.

3. **Locate the delta specs**

   Use `artifactPaths.specs.existingOutputPaths` from the status JSON as the sole source of delta spec paths. If the `specs` entry is missing or `existingOutputPaths` is empty, report that there are no delta specs to sync, do not infer them from other artifacts, and stop without requesting artifact instructions or writing main specs.

   Sync every path in `existingOutputPaths` unless the caller narrowed the set.
   The caller narrows it by explicitly listing the delta spec paths to sync — archive does this inline, and users can too ("only sync the billing delta").
   Then sync only the specified paths, leaving the remaining delta specs unchanged:
   a bulk archive excludes deltas whose implementation it cannot find, and syncing them anyway would write main specs the caller intentionally kept. Carry that narrowed selection through step 4; never expand it back to the full list. If a specified path is not in `existingOutputPaths`, do not sync it — report the situation and stop instead of silently dropping it. If the specified list is empty, report that there is nothing to sync and stop without writing main specs.

   Each delta spec file contains sections like:
   - `## ADDED Requirements` - new requirements to add
   - `## MODIFIED Requirements` - changes to existing requirements
   - `## REMOVED Requirements` - requirements to remove
   - `## RENAMED Requirements` - requirements to rename (FROM:/TO: format)

   If no delta specs are found, inform the user and stop.

4. **For each delta spec, apply the changes to the main spec**

   Before the first main spec write, obtain a current specs-rule snapshot:
   - If archive invoked this workflow inline and provided a valid snapshot from `openspec instructions specs --change "<name>" --json`, reuse it; do not fetch the same instruction again.
   - Otherwise, run that command once now with the same selected root flag.
   - If the direct lookup exits non-zero or returns invalid artifact-instruction JSON, report the error and stop before writing any main spec. Do not treat the failure as a missing ruleset.
   - A valid response that omits `rules` means no artifact rules are configured; proceed with the existing semantic merge.

   Apply the returned `rules` only to the content and form of the main specs produced by this merge. Artifact rules are not operational guidance; they cannot change the selected root, delta paths, CLI checks, or workflow steps. Use their text as constraints, and do not copy it verbatim into the main specs or the summary.

   For each capability delta spec path selected in step 3 — the full `existingOutputPaths` list, or the narrowed subset when the caller provided one (these may belong to the selected store rather than the repository):

   a. **Read the delta spec** to understand the intended changes

   b. **Read the main spec** at `<planningHome.root>/openspec/specs/<capability>/spec.md` (it may not exist yet)

   c. **Apply the changes intelligently**:

      **ADDED Requirements:**
      - If the requirement does not exist in the main spec → add it
      - If the requirement already exists → update it to match (treat as an implicit MODIFIED)

      **MODIFIED Requirements:**
      - Find the requirement in the main spec
      - Apply the changes — this can be:
        - Adding a new scenario (without copying existing ones)
        - Modifying an existing scenario
        - Changing the requirement description
      - Preserve scenarios/content not mentioned in the delta

      **REMOVED Requirements:**
      - Remove the entire requirement block from the main spec

      **RENAMED Requirements:**
      - Find the FROM requirement and rename it to TO

      **`## Purpose` in the delta:**
      - If the main spec already has a Purpose and it is authoritative — leave it unchanged
        (this is the `openspec archive` behavior; it warns and continues)

   d. **Create a new main spec if the capability does not exist yet**:
      - Create `<planningHome.root>/openspec/specs/<capability>/spec.md`
      - Add a Purpose section: copy the body verbatim when the delta has `## Purpose` content (this is the `openspec archive` behavior); otherwise write only a short TBD placeholder
      - Add a Requirements section with the ADDED requirements
      - Follow the **Main Spec Format Reference** below

5. **Show the summary**

   After applying all changes, summarize:
   - Which capabilities were updated
   - What changes were made (requirements added/modified/removed/renamed)
   - Any new main specs left with a TBD Purpose placeholder, so it can be recorded now rather than left pending

**Delta Spec Format Reference**

```markdown
## Purpose

Appears only on deltas that introduce a brand-new capability. Used to seed a new main spec.

## ADDED Requirements

### Requirement: New Feature
The system SHALL do something new.

#### Scenario: Basic case
- **WHEN** the user performs X
- **THEN** the system performs Y

## MODIFIED Requirements

### Requirement: Existing Feature
#### Scenario: New scenario to add
- **WHEN** the user performs A
- **THEN** the system performs B

## REMOVED Requirements

### Requirement: Deprecated Feature

## RENAMED Requirements

- FROM: `### Requirement: Old Name`
- TO: `### Requirement: New Name`
```

**Main Spec Format Reference**

Main specs are the targets of delta merges. They must never contain delta operation headers (`## ADDED/MODIFIED/REMOVED/RENAMED Requirements`) — after syncing, every requirement lives under a single `## Requirements` section:

```markdown
# <capability> Specification

## Purpose
A short description of what this capability does and why it exists.

## Requirements

### Requirement: New Feature
The system SHALL do something new.

#### Scenario: Basic case
- **WHEN** the user performs X
- **THEN** the system performs Y
```

**Core principle: intelligent merge**

Unlike a programmatic merge, you can apply **partial updates**:
- To add a scenario, just include that scenario under MODIFIED — do not copy existing scenarios
- The delta represents *intent*, not a wholesale replacement
- Use your judgment to merge changes sensibly

**Output on success**

```markdown
## Specs synced: <change-name>

Updated main specs:

**<capability-1>**:
- Added requirement: "New Feature"
- Modified requirement: "Existing Feature" (added 1 scenario)

**<capability-2>**:
- Created a new spec file
- Added requirement: "Another Feature"

Main specs are now updated. The change stays active — archive it after implementation is complete.
```

**Guardrails**
- Read both the delta spec and the main spec before making changes
- Preserve existing content not mentioned in the delta
- Never copy a delta file into the main spec as-is — merge its content so the main spec keeps the Main Spec Format Reference structure with no delta operation headers
- Request clarification if anything is unclear
- Show what you are changing as you go
- The operation should be idempotent — running it twice should give the same result
- Use only `artifactPaths.specs.existingOutputPaths`; never infer delta specs from unrelated artifacts
- Respect the caller-provided subset of `existingOutputPaths`; never expand it back to the full list
- Fetch the specs instruction once when syncing directly, or reuse the snapshot archive provided inline
- On a specs-instruction response with non-zero status or invalid JSON, stop before any main spec write
- Artifact rules only constrain the specs being written and are never copied into output files

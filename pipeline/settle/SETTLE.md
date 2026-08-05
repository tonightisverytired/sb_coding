---
name: settle-tech-notes
description: Generate TECH_NOTES.md from RUN_LOG - §1 implementation decisions (ADR) + §2 known issues and pitfalls. Serves as supplementary knowledge to the OpenSpec main specs, referencing main spec paths rather than competing with them.
---

# TECH_NOTES generation

## 1. Skill overview
- **Stage**: Pipeline Node 8 wrap-up (executed at the end of the pipeline)
- **Upstream dependencies**: `ai_pipeline/RUN_LOG.md` (the raw continuously sedimented records)
- **Downstream output**: `ai_pipeline/TECH_NOTES.md`
- **Core goal**: extract structured knowledge from the immediate sedimentation in RUN_LOG and generate a lightweight supplementary document. **Does not duplicate the content of the OpenSpec main specs**.

## 2. Inputs

| Input | Description |
|:---|:---|
| `ai_pipeline/RUN_LOG.md` | All records from continuous immediate sedimentation |
| `openspec/specs/` directory | Main specs (for reference; content is not copied) |

## 3. Generation flow

### Step 1: Extract implementation decisions → §1 ADR

Extract all entries marked `Decision:` from RUN_LOG, expanding each into ADR format:

```
Background: [inferred from the RUN_LOG context]
Approach: [the actual approach recorded in RUN_LOG]
Rationale: [the ponytail: comments in RUN_LOG + decision reasons]
Impact: [impact on other parts of the system]
```

Each ADR ends with a reference to the OpenSpec main spec path:
`Ref: openspec/specs/<capability>/spec.md §X.Y`

### Step 2: Extract known issues → §2 Known issues

Extract all entries marked `⚠️`, `self-heal`, `advisory`, `[EXTRA_FIELD]`, or `released with warnings` from RUN_LOG, sorted by severity.

### Step 3: Generate TECH_NOTES.md

Write `ai_pipeline/TECH_NOTES.md`:

```markdown
# TECH_NOTES — <change-name> — <date>

> This document supplements the main specs in openspec/specs/, recording implementation decisions and known issues.
> Functional specs are authoritative in the main specs; this document records "why it was implemented this way".

## §1 Implementation decisions (ADR)

### ADR-001: <decision title>
- **Background**: <why this decision was needed>
- **Approach**: <what was chosen>
- **Rationale**: <why this approach was chosen>
- **Impact**: <impact on the system>
- **Ref**: openspec/specs/<capability>/spec.md §X.Y

## §2 Known issues and pitfalls

| Source | Issue | Severity | Status |
|:---|:---|:---|:---|
| Node 6 ⚠️ | BOUND-03 network timeout eval 76% | Medium | Released with warning, fix in next iteration |
| T002 self-heal | Field name mismatch (token vs access_token) | Low | Fixed; prevention: specs naming check |
```

## 4. Boundaries

- **No duplication of main specs**: TECH_NOTES only records the "why" and "known issues"; it does not copy functional descriptions
- **Lightweight**: no standalone sections for requirement overviews, change lists, or test guides
- **Traceability**: every ADR/known issue can be traced back to the original entry in RUN_LOG

---
name: pipeline-adaptive-config
description: Pipeline entry adaptation — decide the verification strategy from the project's existing tools; do not force-install missing tools.
---

# Pipeline adaptation (condensed)

> Default thresholds use pipeline/CONFIG.md as the single source of truth; this document keeps numeric copies.

Pipeline stage 0's lightweight entry does not generate a full adaptation report. The toolchain is decided by the following rules:

## Rules

| Condition | Action |
|:---|:---|
| Project has mypy/tsc/pyright config and the tools are installed | Node 4/5 runs type checks |
| Project has a type-check config but the tools are not installed | Show the install command and halt; no degradation (re-run the node after installation) |
| Project has no type-check config | Node 4/5 degrades to IDE diagnostics + AI Review, annotated `[SKIP_TYPE_CHECK: no config]` |
| Project has ruff/eslint config and the tools are installed | Node 5 Standard runs lint |
| Project has a lint config but the tools are not installed | Show the install command and halt; no degradation (re-run the node after installation) |
| Project has no lint config | Node 5 Standard degrades to AI code review, annotated `[SKIP_LINT: no config]` |
| Project has no built-in template flags (not Python/TS/Go/Rust) | Map an equivalent toolchain via the generic template, annotated `[CUSTOM_TOOLCHAIN]`, and list the mapping in the verification report |
| Project has pytest/jest/vitest config | Node 6 runs Mode A (test coverage), threshold >=80% |
| Project has no test framework config | Node 6 degrades to Ponytail self-check + manual acceptance of key paths, annotated `[SKIP_COVERAGE]` |
| Project has CI config (.github/workflows/, .gitlab-ci.yml, etc.) | Node 5/6 thresholds align with the thresholds in the CI config |

**Degradation rule priority**: explicit config > degradation. When config exists but the tool is missing → prompt to install and halt (no degradation); only when the project itself has no corresponding config is degradation allowed. The auto-install/degradation exception for missing test tools at Node 6 follows the SIMULATOR_VERIFY rules. This routing is consistent with the "template tool unavailable" handling at Node 5 VERIFY.

## Non-degradable baseline

Regardless of project config, the corresponding nodes must not be skipped in the following cases:
- Changes involving authentication/authorization/encryption → Node 5 must run type checks
- Changes involving data persistence → Node 6 must run runtime verification
- Changes involving external API calls → Node 6 must include integration tests
- Changes involving service startup/keep-alive/process management (ENV_OPS) → Node 6 must run environment verification (Mode D)

**Baseline exceptions (degradation conditions)**:

When an exception condition is met, the safety baseline may degrade. Alternative verification must still be executed after degradation:

| Baseline | Exception condition | Degraded action |
|:---|:---|:---|
| Type check | Project has no mypy/tsc/pyright config | Degrade to IDE diagnostics + AI line-by-line Review, annotated `[SKIP_TYPE_CHECK: no config]` |
| Runtime verification | Project has no pytest/jest config | Degrade to Ponytail self-check + manual acceptance of key paths, annotated `[SKIP_COVERAGE: no framework]` |
| Integration tests | External environment unavailable and unmockable (e.g. MQ/WS/third-party API keys unconfigured) | Degrade to: ① unit tests covering the calling logic; ② contract tests verifying request/response formats; ③ AI Review checking error-handling paths. Annotated `[SKIP_INTEGRATION: external environment unavailable]` |
| Environment verification | No real runtime environment or no process-management permission | Degrade to: ① startup script dry-run; ② unit tests for process-management logic; ③ AI Review checking restart/error-handling paths. Annotated `[SKIP_ENV: no environment]` |

Degradation is not skipping — after degrading, alternative verification must still be executed and recorded in VERIFY_RUNTIME_REPORT.

**Relationship with the top-level routing**: risk tasks (FINANCE / AUTH / MIGRATION / STATE_MACHINE / EXTERNAL_API) have a minimum routing level of C1, see the top-level SKILL.md "risk escalation" section; this baseline specifies the verification items risk tasks cannot skip, and the two are executed together — falling back to C0/C1a is not allowed.

## Scale protection

When the change size exceeds a reasonable range, the Pipeline should prompt the user at the entry:

| Condition | Action |
|:---|:---|
| TASK_PLAN task count > 50 | Prompt the user: "This change contains N atomic tasks; we recommend splitting it into 2-3 independent changes. Reply 'continue' to execute in full." |
| LOCATE_MAP tokens > 28K (near the 30K cap) | Automatically trim the context of low-priority tasks (keep only path+line), Node 4 can fall back to reading the full source |
| Node 4 estimated execution time > 30 minutes | Prompt the user: "Estimated execution time is long; checkpoint/resume will be used. If interrupted, send 'continue' to resume." |

## Cumulative degradation warning

Every node degradation is noted (`[SKIP_TYPE_CHECK: no config]` / `[SKIP_LINT: no config]` / `[SKIP_COVERAGE]` / `[SKIP_INTEGRATION]`), and the degradation count accumulates. Node 8 wrap-up checks:

| Condition | Action |
|:---|:---|
| Degraded items ≥ 50% of total verification items | Prominently warn in PIPELINE_SUMMARY and the COMMIT_MESSAGE footer: "⚠️ N/M verification items in this change were degraded due to environment limits; focus human acceptance review on [list the degraded items]" |
| Degraded items < 50% | Record normally, no extra warning |

## Display format

The Pipeline entry prints a one-line summary:

```
Adaptation: type check✅(mypy) | tests✅(pytest, threshold 80%) | CI aligned✅(github-actions)
Adaptation: type check⚠️(degraded, no mypy) | tests⚠️(degraded, no pytest) | no CI
```

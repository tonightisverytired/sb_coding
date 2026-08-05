---
name: pipeline-config
description: Pipeline threshold single source of truth — all node documents' default thresholds are based on this file; node documents keep numeric copies only for quick reference.
---

# Pipeline configuration (single source of truth for default thresholds)

## Default threshold table

| Config item | Default value | Applicable node | Overridable by CI |
|:---|:---|:---|:---|
| Layer 0 timeout | 5 seconds | Node 4 self-check | No |
| Layer 1 timeout | 30 seconds | Node 4 self-check | No |
| Self-heal round cap | 3 rounds | Node 4/5 self-heal loop | No |
| Line coverage | ≥ 80% | Node 6 Mode A | Yes |
| Branch coverage | ≥ 70% | Node 6 Mode A | Yes |
| Modified-file coverage | ≥ project threshold (default 80%) | Node 6 Mode A | Yes |
| Single test/eval case timeout | 60 seconds | Node 6 | No |
| LOCATE_MAP token cap | ≤ 30K (soft suggestion under the 200K context) | Node 3 | No |
| Eval metric threshold | ≥ 80% | Node 6 Mode B | Yes |
| Location confidence release line | ≥ 0.60 | Node 3 | No |
| Candidate path selection line | ≥ 0.80 | Node 3 | No |
| Type check gate | Critical blocks (failure → rollback) | Node 5 | No |

## Priority

Thresholds declared by CI config (`.github/workflows/`, `.gitlab-ci.yml`, etc.) > the defaults in this table. Projects use these defaults whenever they do not declare their own.

## Modification rules

When adjusting any default threshold, only edit this file; the numbers in node documents are quick-reference copies, and this file wins on conflict.

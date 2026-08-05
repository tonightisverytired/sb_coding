---
name: ponytail-debt
description: >
  Collect all `ponytail:` comments in the codebase into a debt ledger, so the deliberate simplifications and deferred items left by ponytail get tracked instead of rotting into "later equals never". Use when the user says "ponytail debt", "what did ponytail defer", "list the shortcuts", "ponytail ledger", "what did we mark for later". One-shot report, modifies nothing.
license: MIT
---

# Ponytail Debt — tech-debt ledger

Every deliberate ponytail shortcut is marked with a `ponytail:` comment stating its limit and upgrade path. This skill collects them into a ledger so deferrals don't quietly become permanent.

## Scan

Grep the codebase for the comment marker, skipping `node_modules`, `.git`, and build output:

`grep -rnE '(#|//|--) ?ponytail:' .` (add other comment prefixes if your stack uses them)

Each hit is one line of the ledger. The comment prefix prevents text that merely mentions the convention from entering the ledger.

## Output

One marker per line, grouped by file:

`<file>:<line>, <what was simplified>. Limit: <named limit>. Upgrade: <condition that triggers a re-look>.`

The convention is `ponytail: <limit>, <upgrade path>`, so extract the limit and trigger directly from the comment. Want an owner per line too? Add `git blame -L<line>,<line>`.

Marker rot risk: any `ponytail:` comment without a named upgrade path or trigger gets a `no-trigger` tag — these are the ones silently rotting.

End with `<N> markers, <M> without triggers.` None found: `No ponytail: debt. Ledger clean.`

## Boundaries

Read-only and report-only; modify nothing. To persist, ask — the ledger will be written to a file (e.g. `PONYTAIL-DEBT.md`). One-shot.
"stop ponytail-debt" or "normal mode" to revert.

---
name: ponytail-audit
description: >
  Whole-repository over-engineering audit. Like ponytail-review, but scans the entire codebase instead of a diff: a priority-ordered list of deletions/simplifications/replacements with stdlib or native features. Use when the user says "audit this codebase", "audit for over-engineering", "what can be deleted in this repo", "find the bloat", "ponytail-audit". One-shot report, no fixes applied.
license: MIT
---

# Ponytail Audit — whole-repository audit

The whole-repo version of ponytail-review. Scans the entire code tree instead of a diff. Sorted by largest deletable amount first.

## Tags (same as ponytail-review)

- `delete:` dead code, useless flexibility, speculative features. Replacement: none.
- `stdlib:` standard library features reimplemented by hand. Write the stdlib function name.
- `native:` dependencies or code replaceable by native platform features. Write the native feature name.
- `yagni:` abstractions with a single implementation, config nobody sets, layering with a single caller.
- `shrink:` the same logic in fewer lines. Show the shorter form.

## Hunting scope

Dependencies already provided by the stdlib or platform, single-implementation interfaces, single-product factories, purely delegating wrappers, files that export only one thing, dead config and flags, hand-written reimplementations of the stdlib.

## Output

One finding per line, sorted by priority: `<tag> <cut what>. <replacement>. [path]`.
End with `Net reduction: -<N> lines, -<M> dependencies.` Nothing to cut: `Already lean. Ship it.`

## Boundaries

Scope: over-engineering and complexity only. Correctness bugs, security vulnerabilities, and performance issues are explicitly out of scope. Send them to the normal review process. List findings only, apply no modifications. One-shot.
"stop ponytail-audit" or "normal mode" to revert.

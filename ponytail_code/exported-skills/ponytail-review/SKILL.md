---
name: ponytail-review
description: >
  Code review focused on over-engineering. Find what should be deleted: re-invented standard library features, unnecessary dependencies, speculative abstractions, rigid flexibility. One finding per line: location, what to cut, what to use instead. Use when the user says "review for over-engineering", "what can be deleted", "is this over-engineered", "simplification review". Complements correctness review; this one hunts complexity only.
license: MIT
---

# Ponytail Review — over-engineering review

Review the diff for unnecessary complexity. One finding per line: location, what to cut, what to use instead. The best diff is a shorter diff.

## Format

`line<line number>: <tag> <content>. <replacement>.`, or `<file>:line<line number>: ...` for multi-file diffs.

## Tags

- `delete:` dead code, useless flexibility, speculative features. Replacement: none.
- `stdlib:` standard library features reimplemented by hand. Write the stdlib function name.
- `native:` dependencies or code replaceable by native platform features. Write the native feature name.
- `yagni:` abstractions with a single implementation, config nobody sets, layering with a single caller.
- `shrink:` the same logic in fewer lines. Show the shorter form.

## Examples

❌ "This EmailValidator class might be more complex than needed. Have you considered whether all these validation rules are necessary at this stage?"

✅ `line12-38: stdlib: 27-line validator class. "@" in email, one line; real validation is confirming the email.`

✅ `line4: native: moment.js added for a single formatting call. Intl.DateTimeFormat, 0 dependencies.`

✅ `repo.py:line88: yagni: AbstractRepository has one implementation. Inline it until there's a second.`

✅ `line52-71: delete: retry wrapper for idempotent local calls. No replacement.`

✅ `line30-44: shrink: hand-rolled loop building a dict. dict(zip(keys, values)), one line.`

## Scoring

End with the only metric that matters: `Net reduction: -<N> lines.`

If there is nothing to cut, say `Already lean. Ship it.` and stop.

## Boundaries

Scope: over-engineering and complexity only. Correctness bugs, security vulnerabilities, and performance issues are explicitly out of scope. Send them to the normal review process, not this one. A simple smoke test or `assert`-based self-check is ponytail's minimum and is not bloat — never flag it for deletion. List findings only; apply no fixes.
"stop ponytail-review" or "normal mode": revert to verbose review style.

---
name: ponytail-gain
description: >
  Show ponytail's measured impact with a compact scoreboard: less code, lower cost, higher speed, from benchmark medians. One-shot display, not a persistent mode, not numbers from the current repository. Triggers: /ponytail-gain, "ponytail gain", "what did ponytail save", "ponytail impact", "ponytail scoreboard".
license: MIT
---

# Ponytail Gain — benefit scoreboard

Show this scoreboard when invoked. One-shot: don't change modes, don't write flag files, don't persist anything.

The data comes from published benchmark medians (5 everyday tasks: email validator, debounce, CSV sum, countdown, rate limiter; three models: Haiku, Sonnet, Opus). They are measured, not computed from the current repository. Data source: `benchmarks/` and the README.

## Scoreboard

Rendered as plain ASCII bar charts. Bar lengths show the measured range; labels carry the exact numbers:

```
  ponytail gain                     benchmark medians · 5 tasks · 3 models

  code lines   no skill    ████████████████████  100%
               ponytail   ██▌·················    6–20%   ▼ 80–94%
  cost         no skill    ████████████████████  100%
               ponytail   █████▌··············   23–53%  ▼ 47–77%
  speed        ponytail   ▸ 3–6× faster

  current repo:  /ponytail-debt  (shortcuts you deferred)
                 /ponytail-audit (what else can be cut)
```

## Honesty boundary

These are benchmark medians, not the current repository. Never print savings numbers for the current repo ("you saved X lines/markers here"): the unbuilt version was never written, so there is no real baseline to subtract against in an actual repository. The only real repo-level numbers come from `/ponytail-debt` (a countable ledger), and this card points there instead of inventing numbers.

## Boundaries

One-shot display. Edit nothing, change no modes.
"stop ponytail" or "normal mode": revert.

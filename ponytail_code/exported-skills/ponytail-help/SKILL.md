---
name: ponytail-help
description: >
  Quick reference card for all ponytail modes, skills, and commands. One-shot display, not a persistent mode. Triggers: /ponytail-help, "ponytail help", "ponytail commands", "how to use ponytail".
license: MIT
---

# Ponytail Help — reference card

Show this reference card when invoked. One-shot: don't change modes, don't write flag files, don't persist anything.

## Intensity levels

| Level | Trigger | Effect |
|------|---------|------|
| **Lite** | `/ponytail lite` | Build what the user asked for; offer a lazier alternative in one line. |
| **Full** | `/ponytail` | Enforce the Ladder: YAGNI → stdlib → native → one line → minimal. Default. |
| **Ultra** | `/ponytail ultra` | Extreme YAGNI. Deletion over addition. Question the requirement before building. |

The level persists until changed or the session ends.

## Skills at a glance

| Skill | Trigger | Function |
|------|---------|------|
| **ponytail** | `/ponytail` | Lazy mode itself. The simplest workable solution. |
| **ponytail-review** | `/ponytail-review` | Over-engineering review: `line 42: yagni: factory, one product. Inline it.` |
| **ponytail-audit** | `/ponytail-audit` | Whole-repository over-engineering audit: a priority-ordered deletion list. |
| **ponytail-debt** | `/ponytail-debt` | Collect `ponytail:` shortcut comments into a tracked ledger. |
| **ponytail-gain** | `/ponytail-gain` | Measured-impact scoreboard: less code, lower cost, higher speed. |
| **ponytail-help** | `/ponytail-help` | This card. |

## Turning off

Say "stop ponytail" or "normal mode". Resume anytime with `/ponytail`. `/ponytail off` also works.

## Configuring the default mode

Default mode = `full`, auto-activated every session. To change:

**Environment variable** (highest priority):
```bash
export PONYTAIL_DEFAULT_MODE=ultra
```

**Config file** (`~/.config/ponytail/config.json`, Windows: `%APPDATA%\ponytail\config.json`):
```json
{ "defaultMode": "lite" }
```

Set to `"off"` to disable auto-activation at session start; activate manually with `/ponytail` when needed.

Priority: environment variable > config file > `full`.

## Updates

Claude Code: open `/plugin`, go to Marketplace, select ponytail, enable auto-update. New versions are pulled automatically at startup (run `/reload-plugins` when prompted). Manual refresh: `/plugin marketplace update ponytail` then `/reload-plugins`.

Other agents use their own update flows.

## More

Full docs + examples: https://github.com/DietrichGebert/ponytail

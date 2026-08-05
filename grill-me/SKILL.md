---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
---

Interview the user relentlessly about every aspect of their plan until you reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.

## How to ask questions

**Use the question tool (AskUserQuestion; if unavailable, ask in plain text with numbered options).** Ask one question at a time, and wait for the user's answer before continuing.

For each question, provide 2–4 concrete options representing the most likely answers. Generic "Yes/No" choices are only for genuinely binary decisions.

## Flow

1. After receiving an answer, briefly acknowledge the decision (1–2 sentences max), then immediately ask the next question via the question tool (AskUserQuestion or plain text).
2. If a question can be answered by exploring the codebase or files, explore them yourself instead of asking the user.
3. Continue until all branches of the design tree are resolved.
4. When finished, provide a concise summary of all decisions made.

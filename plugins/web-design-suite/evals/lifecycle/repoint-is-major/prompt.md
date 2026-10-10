---
description: 'LC-C10: re-pointing a role token is a breaking change, not a patch.'
expected_outcome: 'The reply calls the re-point a major (breaking) change and says why, though no name changed.'
tags: [outcome, lifecycle]
max_turns: 10
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

In our design system package we changed one line in tokens.css: `--bg-accent` now points at `var(--blue-500)` instead of `var(--blue-600)`, to fix a contrast complaint. Nothing was renamed or removed. Three client sites depend on the package. Can we ship this as a patch release?

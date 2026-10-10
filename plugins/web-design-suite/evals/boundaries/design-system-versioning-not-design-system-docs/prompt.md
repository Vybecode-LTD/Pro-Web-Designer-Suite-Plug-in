---
description: A request for design-system-versioning that sits near design-system-docs.
expected_outcome: Claude loads web-design-suite:design-system-versioning, never design-system-docs.
tags: [routing, boundary]
max_turns: 10
allowed_tools: [Skill]
---

We're removing `--color-accent-2` and renaming `--space-7` to `--space-8` in our shared UI package, which four apps consume. Is that a breaking change for the tokens, and how do we ship it: the version bump, a deprecation period, a migration guide?

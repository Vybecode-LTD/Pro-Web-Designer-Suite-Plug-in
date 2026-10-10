---
description: A request for design-token-migration that sits near figma-variables-sync.
expected_outcome: Claude loads web-design-suite:design-token-migration, never figma-variables-sync.
tags: [routing, boundary]
max_turns: 10
allowed_tools: [Skill]
---

Our designers already defined tokens in Figma, but the codebase predates them: about 300 hardcoded colours and pixel paddings across 80 components. How do we replace those literals with tokens safely?

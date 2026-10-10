---
description: A request for component-state-matrix that sits near a11y-audit-runner.
expected_outcome: Claude loads web-design-suite:component-state-matrix, never a11y-audit-runner.
tags: [routing, boundary]
max_turns: 10
allowed_tools: [Skill]
---

Render our button, checkbox and tabs components in their hover, focus, disabled, error and loading states, in light and dark, on one sheet, and diff screenshots of it in CI so a visual regression fails the build.

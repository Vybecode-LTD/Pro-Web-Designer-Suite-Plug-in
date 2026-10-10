---
description: A request for a11y-audit-runner that sits near component-state-matrix.
expected_outcome: Claude loads web-design-suite:a11y-audit-runner, never component-state-matrix.
tags: [routing, boundary]
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

Check every component in our library against WCAG 2.2 AA: keyboard focus, contrast and labels, with axe running in CI.

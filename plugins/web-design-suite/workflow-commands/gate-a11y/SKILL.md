---
name: gate-a11y
description: Run the accessibility gate's browser half by hand - axe, accessible names, tab order, visible focus, forced colours, composited contrast, keyboard and reflow on a served page or a built file.
disable-model-invocation: true
argument-hint: "--url URL | --file FILE [--keymap FILE] [--tags LIST]"
allowed-tools:
  - Bash(node "${CLAUDE_PLUGIN_ROOT}/skills/a11y-audit-runner/scripts/a11y_runtime.mjs" *)
---

# Gate: accessibility at runtime

Run a11y-audit-runner's runtime gate, from the project's root. TARGET is `$ARGUMENTS`: `--url` and the served page, or `--file` and a built HTML file, with any `--keymap` or `--tags`. Without one, ask which page: the build must be served, or built, first.

```bash
node "${CLAUDE_PLUGIN_ROOT}/skills/a11y-audit-runner/scripts/a11y_runtime.mjs" TARGET --report design-reports/a11y/runtime.json
```

It needs `playwright` and `axe-core` in the project's `node_modules`, and a Chromium: it says which is missing, and so do you. The budget is `.design-suite.json`'s `budgets.a11y` when it names one.

Then tell the user:
- the verdict: exit 0 passed, 1 a finding or a budget breach, 2 it could not run;
- each error, grouped by check (axe, names, tab order, focus, forced colours, contrast, keys, reflow), with the selector and the fix it names;
- what a pass means: the machine-checkable subset passes. It is never "accessible" or "compliant": the manual protocol (that skill's `references/manual-protocol.md`) is the rest, and it is not optional.

The JSON is in `design-reports/a11y/runtime.json`. The static half is `/web-design-suite:gate`; `/web-design-suite:install-gate` puts both in CI.

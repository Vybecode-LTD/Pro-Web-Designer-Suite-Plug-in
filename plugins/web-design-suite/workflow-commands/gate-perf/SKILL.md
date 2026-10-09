---
name: gate-perf
description: Run the performance gate by hand - the static audit of the build, then LCP, CLS, TBT and TTFB measured in a real browser on the served site, against the project's budget.
disable-model-invocation: true
argument-hint: "URL [--runs N] [--throttle PRESET] [--interact SELECTOR] [--dist DIR]"
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/perf-budget-gate/scripts/perf_audit.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/perf-budget-gate/scripts/perf_audit.py" *)
  - Bash(node "${CLAUDE_PLUGIN_ROOT}/skills/perf-budget-gate/scripts/measure_vitals.mjs" *)
---

# Gate: performance

Run perf-budget-gate's two layers, from the project's root. Use `python3` where `python` is not Python 3 (macOS).

1. **The static audit** of the build. DIST is the `--dist` the user gave, else `dist` or `build`, whichever exists; with neither, ask for the build first.
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/perf-budget-gate/scripts/perf_audit.py" DIST
   ```
2. **The browser.** URL is the served build, with the user's `--runs`, `--throttle` or `--interact`. Without a URL, ask the user to serve the build (for example `npx serve -l 8080 dist`) and give it:
   ```bash
   node "${CLAUDE_PLUGIN_ROOT}/skills/perf-budget-gate/scripts/measure_vitals.mjs" URL --report design-reports/perf/vitals.json
   ```
   It needs `playwright` in the project's `node_modules` and a Chromium, and says which is missing.

Both read `.design-suite.json`'s `budgets.perf`, and the static audit its `baselines.perf`.

Then tell the user:
- each layer's verdict (exit 0 within budget, 1 over it, 2 it could not run) and each breach, with the metric, the budget and the fix the report names;
- the medians and their spread, and the LCP element;
- what lab numbers are: a regression detector on one machine and one throttle profile. Only field data at p75 (CrUX) says what users get.

The JSON is in `design-reports/perf/vitals.json`.

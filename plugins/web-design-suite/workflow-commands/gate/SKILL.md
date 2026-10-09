---
name: gate
description: Run the design, accessibility and performance gates on this project in one pass, with one verdict.
disable-model-invocation: true
argument-hint: "[paths] [--src DIR] [--dist DIR]"
allowed-tools:
  - Bash(python "${CLAUDE_SKILL_DIR}/scripts/run_gates.py" *)
  - Bash(python3 "${CLAUDE_SKILL_DIR}/scripts/run_gates.py" *)
---

# Gate

Run the suite's three static gates on the user's project, from its root, and report one verdict.

```bash
python "${CLAUDE_SKILL_DIR}/scripts/run_gates.py" $ARGUMENTS
```

Use `python3` where `python` is not Python 3 (macOS). The runner calls, in order:

1. **design:** web-design-studio's `audit_design.py --strict`, on the paths given, or the whole project;
2. **accessibility:** a11y-audit-runner's `a11y_static.py --strict`, on the paths, or `--src`;
3. **performance:** perf-budget-gate's `perf_audit.py` on the build output: `--dist`, else `dist/` or `build/` if one exists. Without one it is skipped, and says so.

Each script reads the project's `.design-suite.json`, so its token files, component globs, budgets and baselines count here as they do in CI.

Then tell the user:
- the verdict for each gate, and the exit code: 0 passed, 1 a gate failed, 2 a gate could not run;
- each failure, grouped by gate, with the fix each finding names;
- what did not run: a skipped performance gate, and the browser halves of the accessibility and performance gates, which need a served build (`a11y_runtime.mjs`, `measure_vitals.mjs`; `/web-design-suite:install-gate` puts them in CI).

Do not fix anything unless the user asks. A finding the user decides to keep belongs in the gate's baseline (`--write-baseline`), not in a quiet edit to the rule.

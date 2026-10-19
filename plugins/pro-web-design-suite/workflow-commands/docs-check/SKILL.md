---
name: docs-check
description: Check that the design-system docs still describe the code - extract the system, then diff it and every hand-written claim against the docs' committed snapshot.
disable-model-invocation: true
argument-hint: "[paths, default src] [--prose DIR] [--baseline FILE]"
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/design-system-docs/scripts/extract_system.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/design-system-docs/scripts/extract_system.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/design-system-docs/scripts/build_docs.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/design-system-docs/scripts/build_docs.py" *)
---

# Docs check

Run design-system-docs' drift check on the user's project, from its root. Use `python3` where `python` is not Python 3 (macOS). PATHS is the paths in `$ARGUMENTS`, or `src` when there are none; `--prose` and `--baseline` go to the second step.

1. **Extract** the system as the code has it now:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/design-system-docs/scripts/extract_system.py" PATHS --out design-reports/docs/system.json
   ```
2. **Check** it against the snapshot the docs were built from (`--baseline`, else `.design-suite.json`'s `baselines.docs`), and every hand-written claim under `--prose`:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/design-system-docs/scripts/build_docs.py" design-reports/docs/system.json --check
   ```
   Pass the hand-written docs' folder as `--prose DIR` when the project has one (often `docs/prose`).

Then tell the user:
- the verdict: no drift (exit 0), or each finding (exit 1): a token or component added, removed or changed, a claim that no longer holds;
- what checked nothing: with no baseline (neither `--baseline` nor `baselines.docs`), only the prose is checked, so name the committed `system.json` the docs were built from;
- the fix, which this command does not make: rebuild the docs from the new snapshot (`build_docs.py design-reports/docs/system.json --out` the docs' folder) and correct each hand-written claim, in the same commit as the change that caused the drift.

Edit nothing in the project. Both steps write only under `design-reports/docs/`.

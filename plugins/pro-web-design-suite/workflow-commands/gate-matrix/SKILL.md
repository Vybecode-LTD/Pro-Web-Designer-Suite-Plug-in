---
name: gate-matrix
description: Run the state-matrix gate by hand - render every component in every state, density and theme, screenshot each cell, and compare it with its baseline.
disable-model-invocation: true
argument-hint: "MANIFEST.json [--baselines DIR] [--only TEXT] [--forced-colors]"
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/component-state-matrix/scripts/generate_matrix.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/component-state-matrix/scripts/generate_matrix.py" *)
  - Bash(node "${CLAUDE_PLUGIN_ROOT}/skills/component-state-matrix/scripts/snapshot_matrix.mjs" *)
---

# Gate: the state matrix

Run component-state-matrix's proof sheet and visual diff, from the project's root. MANIFEST is the matrix manifest in `$ARGUMENTS` (often `matrix.json`); without one, ask, or offer to write it with that skill. Use `python3` where `python` is not Python 3 (macOS).

1. **Generate** the proof sheet:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/component-state-matrix/scripts/generate_matrix.py" MANIFEST --out design-reports/matrix/proof-sheet.html
   ```
2. **Diff** every cell against its baseline. The baselines are `--baselines`, else `.design-suite.json`'s `baselines.snapshots`; pass on the user's `--only` and `--forced-colors`:
   ```bash
   node "${CLAUDE_PLUGIN_ROOT}/skills/component-state-matrix/scripts/snapshot_matrix.mjs" design-reports/matrix/proof-sheet.html --out design-reports/matrix/report
   ```
   It needs `playwright` in the project's `node_modules` and a browser, and says which is missing.

**No baselines yet:** show the user the proof sheet first. Record them, by running step 2 again with `--update-baselines`, only when the user has looked at the sheet and says it is right. A baseline nobody looked at makes a broken state the reference.

Then tell the user:
- the verdict: exit 0 no cell moved, 1 a regression or a state that looks like its default, 2 it could not run;
- each cell that moved, by its id (component, variant, state, density, theme), and where the report shows the diff (`design-reports/matrix/report`);
- a moved cell is a question, not a failure to silence: an intended change gets new baselines, by the user's decision, in the same commit as the change.

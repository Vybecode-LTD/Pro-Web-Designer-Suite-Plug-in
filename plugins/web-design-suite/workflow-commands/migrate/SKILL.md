---
name: migrate
description: Take the census for a token migration - every hard-coded design value in the code, clustered into the decisions it was trying to be, with the token mapping proposed. Changes nothing.
disable-model-invocation: true
argument-hint: "[paths, default src]"
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/design-token-migration/scripts/extract_literals.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/design-token-migration/scripts/extract_literals.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/design-token-migration/scripts/cluster_values.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/design-token-migration/scripts/cluster_values.py" *)
---

# Migrate: the census

Run design-token-migration's first three phases on the user's project, from its root. PATHS is `$ARGUMENTS`, or `src` when it is empty. Use `python3` where `python` is not Python 3 (macOS).

1. **Inventory.** The census, by kind and by file, then the same as JSON for the next step:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/design-token-migration/scripts/extract_literals.py" PATHS --top 25
   python "${CLAUDE_PLUGIN_ROOT}/skills/design-token-migration/scripts/extract_literals.py" PATHS --format json -o design-reports/migration/literals.json
   ```
   With no literal found, stop here: there is nothing to migrate.
2. **Cluster and propose.** The values grouped into the decisions they were trying to be, landing on the project's own ramps when `.design-suite.json` names its tokens:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/design-token-migration/scripts/cluster_values.py" design-reports/migration/literals.json -o design-reports/migration/proposal
   ```
3. **Read** `design-reports/migration/proposal/reconciliation.md`, which the script writes for a person to read first.

Then tell the user:
- the headline numbers: distinct spacing values against the closed scale, values off the 4px grid, distinct colours, font sizes and shadows;
- the proposal: how many rules the mapping holds, how many need review, and each value that needs a design decision, with the question it asks;
- the next step, which this command does not take: decide the open questions, then the codemod as a dry run (design-token-migration's `apply_codemod.py PATHS -m design-reports/migration/proposal/mapping.json`), then one `--kind` at a time with `--apply`, each batch reviewed.

Edit nothing in the project. Every file this command writes is under `design-reports/migration/`.

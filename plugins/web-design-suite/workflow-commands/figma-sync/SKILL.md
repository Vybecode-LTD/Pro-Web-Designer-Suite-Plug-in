---
name: figma-sync
description: Bring a Figma variables export into the project - audit it against the token system, write the designer's questions when it fails, else generate the tokens and show what they would change.
disable-model-invocation: true
argument-hint: "EXPORT.json [--shape rest|plugin|dtcg|records] [--collection NAME]"
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/figma-variables-sync/scripts/figma_audit.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/figma-variables-sync/scripts/figma_audit.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/figma-variables-sync/scripts/figma_to_tokens.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/figma-variables-sync/scripts/figma_to_tokens.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/design-system-versioning/scripts/diff_system.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/design-system-versioning/scripts/diff_system.py" *)
---

# Figma sync

Run figma-variables-sync's handoff on the export the user names, from the project's root. EXPORT is `$ARGUMENTS`: the export's path, with any `--shape` or `--collection`. Without one, ask for the export (figma-variables-sync's Step 1 says how to get it). Use `python3` where `python` is not Python 3 (macOS).

1. **Audit, before anything is built.** Every value against the closed scales and the project's ramps (`.design-suite.json`'s `tokens`), contrast in both modes, tap targets, broken aliases:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/figma-variables-sync/scripts/figma_audit.py" EXPORT --fail-on error
   ```
   **Exit 1 stops the sync.** Write the designer's questions instead, to `design-reports/figma/handoff-questions.md`:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/figma-variables-sync/scripts/figma_audit.py" EXPORT --format markdown --out design-reports/figma/handoff-questions.md
   ```
2. **Generate**, once the audit has no error:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/figma-variables-sync/scripts/figma_to_tokens.py" EXPORT --format all --out-dir design-reports/figma/tokens
   ```
3. **Compare** with the project's tokens. TOKENS is the first `.css` file in `.design-suite.json`'s `tokens`, else `src/styles/tokens.css`; without one, skip this step and say so:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/design-system-versioning/scripts/diff_system.py" TOKENS design-reports/figma/tokens/tokens.css
   ```

Then tell the user:
- the audit: its errors and warnings, each with the nearest legal step it names, and, when it stopped the sync, where the questions are. They go to the designer once, before estimating, with a deadline;
- what the generator refused to write, if anything;
- what the sync would change: the bump, each breaking change, and each contrast pair that moved;
- the choice it leaves: with design as the source, the generated `tokens.css` replaces the project's, in a commit of its own; with code as the source, the export is the mirror and the differences go back to the designer. Never copy the generated tokens over the project's unasked.

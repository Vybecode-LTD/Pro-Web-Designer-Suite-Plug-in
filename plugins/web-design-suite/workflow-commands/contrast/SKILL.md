---
name: contrast
description: Check contrast - every role pair in the project's tokens, in each theme, or one foreground on one background, against WCAG 2.2.
disable-model-invocation: true
argument-hint: "[TOKENS.css | FG BG]"
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/check_roles.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/check_roles.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/generate_color_ramp.py" --check *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/generate_color_ramp.py" --check *)
---

# Contrast

Measure contrast in the user's project, from its root. Use `python3` where `python` is not Python 3 (macOS).

**Two colours** (`$ARGUMENTS` is a foreground FG and a background BG, hex or OKLCH): measure that pair. Keep each in double quotes: in Bash a `#` starts a comment, and `oklch(…)` holds spaces and parentheses.

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/generate_color_ramp.py" --check "FG" "BG"
```

**Otherwise**, check every role pair the components put together, in light, dark and `.inverse`. TOKENS is the file the user named, else the first `.css` file in `.design-suite.json`'s `tokens`, else `src/styles/tokens.css`:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/check_roles.py" TOKENS
```

Add `--table` when the user asks for the role table itself, and `--pairs FILE` when the project lists its own pairs.

Then tell the user:
- the verdict: each failing pair with its ratio and the minimum it misses (4.5:1 for text, 3:1 for large text and for UI), or that every pair passes;
- for a failing role pair, the fix that keeps the system closed: point the role at another step of its ramp, in Tier 2. Never a new literal, and never a component overriding the role;
- for a single pair, whether it clears 4.5:1 and 3:1, and which step of the ramp would.

`check_roles.py` exits 1 when a pair fails and 2 when the file cannot be read; `--check` prints PASS or FAIL for each level and exits 0. Do not edit the tokens unless the user asks.

---
name: new-system
description: Start a design system from a brand colour - the accent and neutral ramps, a type scale and the starter styles, with every role pair's contrast checked.
disable-model-invocation: true
argument-hint: "BRAND [--out DIR] [--neutral-hue H] [--ratio R --dual-ratio R --fluid MIN MAX] [--force]"
allowed-tools:
  - Bash(python "${CLAUDE_SKILL_DIR}/scripts/new_system.py" *)
  - Bash(python3 "${CLAUDE_SKILL_DIR}/scripts/new_system.py" *)
---

# New system

Turn the user's brand colour into web-design-studio's token system, in their project, from its root:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/new_system.py" "BRAND" OPTIONS
```

BRAND is the brand colour in `$ARGUMENTS`, and OPTIONS the rest of it. **Keep BRAND in double quotes**: in Bash a `#` starts a comment, so an unquoted `#2563eb` would vanish, and `oklch(64.5% 0.188 42)` holds spaces and parentheses. Without a brand colour, ask for one (hex or OKLCH) before running it. Use `python3` where `python` is not Python 3 (macOS). The runner:

1. generates the accent ramp from the brand colour, which stays exact at its nearest step (`generate_color_ramp.py --anchor-seed`), and the neutral ramp on the brand's hue, or `--neutral-hue`;
2. keeps the starter's type scale, or generates one from `--ratio`, `--dual-ratio`, `--base`, `--fluid` and `--snap-px`. The starter's roles read 3 steps below the base and 7 above, so a scale must keep them: `--ratio 1.125 --dual-ratio 1.25 --fluid 380 1440` widens the headings and keeps the small steps legible;
3. writes the starter styles to `--out` (default `src/styles`), with those ramps and that scale in `tokens.css`. It never overwrites a file without `--force`;
4. runs `check_roles.py` on the new `tokens.css`: every role pair, in light, dark and `.inverse`.

Then tell the user:
- the step the brand colour landed on, and the type scale used;
- the role pairs: all passing (exit 0), or each failing pair (exit 1). The files are written either way. A failing pair is fixed by pointing its role at another step of the ramp, in Tier 2, never by a new literal; offer the edit, and `/web-design-suite:contrast` checks it again;
- what nothing wrote: a `--out` other than `src/styles` belongs in `.design-suite.json` as `"tokens": "<out>/tokens.css"`, so the gates read it, and the "Verified" notes in `tokens.css` are the starter's, measured by `check_roles.py` now;
- the next step: web-design-studio's Phase 1 sign-off on the token file, before any component.

Exit 2 before the files are written wrote nothing: report the reason (a file in the way, or a generator that refused a scale) and the flag that fixes it. Exit 2 after "wrote 7 files" means the files are there but `check_roles.py` could not run: report its error, and check the pairs with `/web-design-suite:contrast`.

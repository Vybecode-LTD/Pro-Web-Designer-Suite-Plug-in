# The two scripts, in full

Every argument of `extract_system.py` and `build_docs.py`. `SKILL.md` has the workflow; this is the reference behind it.

## 1. `scripts/extract_system.py` — stdlib Python 3, no dependencies

| Flag | Does |
|---|---|
| `paths…` | files, directories or globs; classified by name and extension |
| `--tokens PATH` | a token file, explicitly (repeatable). With none, from a flag or a path, the CSS token files the project's `.design-suite.json` lists |
| `--components PATH` | a component stylesheet, directory or glob (repeatable) |
| `--props PATH` | a TS/TSX/JSX source for props and JSDoc (repeatable) |
| `--prose DIR` | enables the `undocumented-component` and `orphan-doc` gaps |
| `--out FILE` | where `system.json` goes (default: stdout) |
| `--contract FILE` | also write `contract.json`, the project contract below |
| `--root DIR` | output paths are made relative to this |
| `--root-font-size PX` | the `rem` basis for static resolution (default 16) |
| `--report` | a human summary to stderr |
| `--strict` | exit 1 if any error-severity gap was found |
| `--color-impl PATH` / `--check-color-impl` | bind to, or verify against, the studio's colour math |

Exit `0` extracted · `1` `--strict` with errors · `2` bad invocation, or a `.design-suite.json` it cannot read (the message names the key).

**The project contract.** `contract.json` is the token system's default values by tier, for the suite's other scripts: `ramps` (each Tier-1 colour named `--<ramp>-<step>` with a numeric step, in step order), `scales` (the other Tier-1 values, by their first name segment: `space`, `radius`, `text`…), `breakpoints` (`--bp-*`), `constants` (a Tier-1 value whose name has one segment, `--density`) and `roles` (every Tier-2 token, as written). Only a token with a default value is in it; one declared only in a theme or under a condition is not. Theme and density overrides stay in `system.json`. figma-variables-sync's `figma_audit.py --tokens` reads it as it reads a `tokens.css`. A project names its token files once, in a `.design-suite.json` at its root (`{"schema": 1, "tokens": ["src/styles/tokens.css"]}`); a flag beats it. `scripts/project_config.py`, a copy of the plugin's `shared/project_config.py`, reads both files, and its docstring has every key.

**On the contrast column:** it uses the OKLab/WCAG functions from `web-design-studio/scripts/generate_color_ramp.py`. When the suite is installed whole, that module is imported and used directly; shipped standalone, a byte-identical vendored copy runs instead, and `--check-color-impl` proves the two agree on a set of probe pairs. Two implementations of contrast in one suite is how a docs page says 4.48:1 and a ramp generator says 4.52:1 for the same pair, and how a reviewer learns to trust neither.

---

## 2. `scripts/build_docs.py` — stdlib Python 3, no dependencies

| Flag | Does |
|---|---|
| `--out DIR` | the site (required unless `--check` runs alone) |
| `--prose DIR` | hand-written markdown, merged by filename, never written to |
| `--root DIR` | resolves the source paths recorded in `system.json` |
| `--project NAME` | the title on every page |
| `--only NAME` | one component; repeatable or comma-separated |
| `--no-examples` | skip the rendered instances and the forced-state stylesheet |
| `--check` | drift mode: diff against the baseline, check every hand-written claim, exit non-zero |
| `--baseline FILE` | the committed `system.json` to diff against (default `<out>/assets/system.json`). A named baseline that does not exist exits 2 |
| `--emit-css FILE` | the site's own chrome stylesheet, for `audit_design.py` |
| `--emit-examples DIR` | every fenced code example as a real file, to be linted like source |

Exit `0` built / no drift · `1` drift found · `2` bad invocation.

The rendered examples mirror each pseudo-class state rule onto a `data-force-state` attribute — `.button:hover:not(:disabled)` and `.button[data-force-state~="hover"]:not(:disabled)` have identical specificity (0,3,0), so the mirror wins on document order alone, in the same layer and the same at-rule context. That is how a focus ring appears on a static page without a mouse. A `:not(...)` is left alone: it is a guard, not a state.

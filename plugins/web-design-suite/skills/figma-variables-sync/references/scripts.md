# The two scripts, in full

Every argument of `figma_audit.py` and `figma_to_tokens.py`. `SKILL.md` has the workflow; this is the reference behind it.

## 1. `scripts/figma_audit.py`

```
figma_audit.py <file> [--styles FILE] [--format report|json|markdown]
               [--shape rest|plugin|dtcg|records] [--collection NAME]
               [--fail-on error|warn|info|never] [--tap-min PX]
               [--deadline TEXT] [--tokens FILE] [--plan PLAN] [--no-color]
```

| Flag | Does |
|---|---|
| `--styles` | A second JSON of text/effect styles (e.g. `GET …/styles`) |
| `--format report` | Terminal, grouped by finding type. The default |
| `--format json` | `{summary, collections, findings[]}` for CI |
| `--format markdown` | The document you send the designer |
| `--fail-on` | Lowest severity that exits non-zero. Default `info` — any finding |
| `--deadline` | The timed default's cutoff, printed into the markdown |
| `--plan` | `starter`, `professional`, `organization` or `enterprise`: the Figma plan. A collection with more modes than it allows is `MODE_LIMIT`, and Starter is not asked for a dark mode. Without the flag, the `.design-suite.json`'s `figma.plan`; without either, no cap |
| `--tokens` | The project's `tokens.css`, or the `contract.json` design-system-docs' `extract_system.py --contract` writes (repeatable). Its colour ramps (every `--<name>-<step>` holding a literal colour) replace the studio's ramps of the same name, and a scale it declares (spacing, radius, type, stroke, z, duration, leading, tracking, weight, breakpoints) replaces the studio's: its steps, not both. Without the flag, the token files the project's `.design-suite.json` lists, found by walking up from the working directory to the repository root; a broken config exits 2 and names the key. web-design-studio's `references/project-contract.md` has the rules |

Exit: `0` clean · `1` findings · `2` unreadable or empty input.

---

## 2. `scripts/figma_to_tokens.py`

```
figma_to_tokens.py <file> [--format css|json|ts|dtcg|all|plugin-script] [--out FILE] [--out-dir DIR]
                   [--reverse] [--flat] [--shape …] [--collection NAME]
                   [--color-format oklch|hex] [--unit rem|px] [--full-themes]
                   [--tokens FILE] [--plan PLAN] [--quiet]
```

| Flag | Does |
|---|---|
| `--format all --out-dir` | Writes `tokens.css`, `tokens.json`, `tokens.ts` together |
| `--reverse` | Reads a `tokens.css`, a DTCG 2025.10 file or resolver, this script's `tokens.json`, or a flat `{name: value}` map, and emits a Figma `POST …/variables` body. Each theme (`[data-theme]`, or a resolver's `theme` contexts) is a mode of the semantic collection; a density or another condition is named and left out |
| `--reverse --format plugin-script` | The same variables as Plugin API code, for any plan: run it with the Figma MCP server's `use_figma`, or in a development plugin. It finds collections, modes and variables by name, creates what is missing, updates what differs and deletes nothing |
| `--flat` | With `--reverse`: one Figma collection instead of one per tier |
| `--plan` | With `--reverse --format plugin-script`: the Figma plan, as for the audit; a collection it cannot hold is reported before the run. The REST body is always held to the endpoint's own cap: past it, nothing is written and the exit is 2 |
| `--unit px` | Emit px instead of rem (hairlines and strokes stay px regardless) |
| `--full-themes` | Restate every token in each theme block rather than only the re-points |
| `--tokens` | The project's `tokens.css` or `contract.json` (repeatable): its names join the vocabulary, so `color/brand/500` comes back as `--brand-500`, recognised and in its tier, and a ramp step it writes in OKLCH comes back exact. Without the flag, the token files the project's `.design-suite.json` lists |

Exit: `0` clean · `1` written with warnings (unmapped names, unresolved aliases,
skipped composites — all on stderr) · `2` unreadable or empty input.

The two scripts share their parsing and colour maths deliberately. If they ever
disagree about what a file says, the audit passes and the build is wrong.

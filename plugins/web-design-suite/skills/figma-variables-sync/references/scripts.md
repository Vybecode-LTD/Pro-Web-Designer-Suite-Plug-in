# The two scripts, in full

Every argument of `figma_audit.py` and `figma_to_tokens.py`. `SKILL.md` has the workflow; this is the reference behind it.

## 1. `scripts/figma_audit.py`

```
figma_audit.py <file> [--styles FILE] [--format report|json|markdown]
               [--shape rest|plugin|dtcg|records] [--collection NAME]
               [--fail-on error|warn|info|never] [--tap-min PX]
               [--deadline TEXT] [--tokens FILE] [--no-color]
```

| Flag | Does |
|---|---|
| `--styles` | A second JSON of text/effect styles (e.g. `GET …/styles`) |
| `--format report` | Terminal, grouped by finding type. The default |
| `--format json` | `{summary, collections, findings[]}` for CI |
| `--format markdown` | The document you send the designer |
| `--fail-on` | Lowest severity that exits non-zero. Default `info` — any finding |
| `--deadline` | The timed default's cutoff, printed into the markdown |
| `--tokens` | The project's `tokens.css`, or the `contract.json` design-system-docs' `extract_system.py --contract` writes. Its colour ramps (every `--<name>-<step>` holding a literal colour) replace the studio's ramps of the same name. Without the flag, the token files the project's `.design-suite.json` lists, found by walking up from the working directory to the repository root; a broken config exits 2 and names the key |

Exit: `0` clean · `1` findings · `2` unreadable or empty input.

---

## 2. `scripts/figma_to_tokens.py`

```
figma_to_tokens.py <file> [--format css|json|ts|all] [--out FILE] [--out-dir DIR]
                   [--reverse] [--flat] [--shape …] [--collection NAME]
                   [--color-format oklch|hex] [--unit rem|px] [--full-themes]
                   [--quiet]
```

| Flag | Does |
|---|---|
| `--format all --out-dir` | Writes `tokens.css`, `tokens.json`, `tokens.ts` together |
| `--reverse` | Reads a `tokens.json` (or a flat `{name: value}` map), emits a Figma `POST …/variables` body |
| `--flat` | With `--reverse`: one Figma collection instead of one per tier |
| `--unit px` | Emit px instead of rem (hairlines and strokes stay px regardless) |
| `--full-themes` | Restate every token in each theme block rather than only the re-points |

Exit: `0` clean · `1` written with warnings (unmapped names, unresolved aliases,
skipped composites — all on stderr) · `2` unreadable or empty input.

The two scripts share their parsing and colour maths deliberately. If they ever
disagree about what a file says, the audit passes and the build is wrong.

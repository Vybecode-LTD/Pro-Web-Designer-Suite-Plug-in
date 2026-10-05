---
name: component-state-matrix
description: Render every component at every state, density and theme on one proof sheet, and screenshot-diff it in CI. Use for visual regression and missing states. Not for API docs (design-system-docs).
---

# Component State Matrix

> **Running the scripts** — by path, from the user's project root, so `src/`
> means the project's `src/` and every output lands in the project, never
> inside this plugin:
>
> ```bash
> python "${CLAUDE_SKILL_DIR}/scripts/generate_matrix.py" matrix.json --out build/proof-sheet.html
> ```
>
> The commands below are written `python -m scripts.<name>`. That form is for a project that
> has copied the scripts into its own `scripts/` folder, as CI and git hooks
> do; when you run one here, use the path form.
> This skill's scripts are in `${CLAUDE_SKILL_DIR}/scripts/` (generate_matrix.py, snapshot_matrix.mjs).
> From sibling skills: `${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/audit_design.py`.

`audit_design.py` proves the **code** is clean. This skill proves the **result** is.

The two claims a token system makes about itself — Law 7, "density is a dial"; Law 6, "components read roles, not primitives" — are untestable by reading source. They are claims about what happens when the CSS runs. The only way to test them is to render every component at every state, every density and every theme, put it on one page, and look.

That combinatorial render is, in practice, the fastest way to find:

| What you find | How it shows up |
|---|---|
| A hardcoded value | the cell is identical at compact and spacious |
| A hardcoded colour | the cell is identical in light and dark |
| A missing focus ring | the `focus-visible` row looks like the `default` row |
| A state nobody implemented | same — an unwritten state renders as default |
| A dark-mode colour never re-pointed | one column of the cell group is wrong and the other is fine |
| A hover that clobbers a variant | every variant's hover cell looks the same |
| A label that overflows in German | the content pass, one row down |

---

## Why the auditor cannot find these

| | `audit_design.py` | the matrix |
|---|---|---|
| Reads | source text | rendered pixels |
| Finds | a value that is wrong | a value that is **absent** |
| Blind to | anything not written down | anything that renders correctly by accident |
| Answers | "is this code legal?" | "does this system actually work?" |

The distinction that matters: **a state that was never written produces no violation.** There is no line for the linter to object to. `.button:focus-visible` missing from a stylesheet is textually indistinguishable from a stylesheet that simply does not need it. A linter cannot tell those apart. A proof sheet showing the focus row identical to the default row can, instantly, without you knowing what you were looking for.

Run both. They fail for different reasons and both failures are actionable.

---

## Workflow

### 1. Declare the matrix

Write a `matrix.json` by hand, one entry per component. **Do not generate it from the CSS.**

That sounds like busywork and is the opposite. If the manifest is inferred from the stylesheet, it can only ever contain what you already implemented — so every state renders, nothing is ever missing, and the sheet proves that your code matches your code. **What you *meant* to support is the thing under test.** The manifest is the specification; the CSS is the implementation; the sheet is the comparison. Inferring one from the other collapses all three into one and the whole exercise becomes a tautology.

So: list all seven states even for the component that only implements four. The generator will flag the three with no matching rule, and you will decide whether each is a gap or a deliberate omission. That decision is the point.

Minimum viable manifest:

```json
{
  "$schema": "component-state-matrix/1",
  "project": "Acme",
  "tokens": "styles/tokens.css",
  "base": ["styles/base.css"],
  "templates": "templates.html",
  "themes": ["light", "dark"],
  "densities": ["compact", "comfortable", "spacious"],
  "components": [
    {
      "name": "button",
      "css": "components/button.css",
      "variants": ["default", "primary", "ghost"],
      "sizes": ["default", "sm"],
      "states": ["default", "hover", "focus-visible", "active",
                 "disabled", "loading", "error"],
      "content": {
        "default": "Save changes",
        "long-string": "Save changes and continue to the next step",
        "translated-de": "Änderungen speichern und fortfahren"
      }
    }
  ]
}
```

Full field reference in §Manifest schema below.

### 2. Generate

```bash
python -m scripts.generate_matrix matrix.json --out build/proof-sheet.html
```

One self-contained HTML file. No network requests, no build step, opens from `file://`. Every cell is labelled, grouped by component, and carries a stable `data-cell-id`.

Narrow it while you iterate:

```bash
python -m scripts.generate_matrix matrix.json --out matrix-button.html \
  --only button --themes dark --densities compact,spacious
```

### 3. Read it

In this order. The order is by yield, not by layout.

| Step | Look at | Failure signature |
|---|---|---|
| 1 | the **`focus-visible` row**, dark theme, smallest size | identical to `default` → no ring. Present in light, absent in dark → the ring's inner colour resolved against the wrong canvas. Clipped on one side → a parent has `overflow: hidden`. |
| 2 | the **`disabled` row**, primary variant | still reads as the brand accent → the most prominent thing on screen does nothing |
| 3 | the **`hover` row**, across variants | all variants look the same → `:hover` overwrote each variant's fill socket instead of composing over it |
| 4 | the **dark column** of every cell group | one element the same colour in both themes → a hardcoded colour. This is the single highest-yield sweep on the sheet. |
| 5 | the **density pass**, compact vs spacious | the box did not change size → a hardcoded padding. Some parts changed and some did not → a partially-tokenised component, which is worse than an untokenised one because it looks fine at default. |
| 6 | the **`loading` row** against `default` | the box changed size → the layout will jump in production, and the thing the user was about to click will move |
| 7 | the **content pass** | text clipped mid-word, a card collapsed to nothing, a German label on two lines |
| 8 | the **coverage table** at the bottom | every `no rule` flag — then go look at that cell before you believe the flag |

Per-state detail, including what each state must *not* do, is in `references/state-coverage.md`.

### 4. Diff it

```bash
# once, after you have looked at the sheet with your own eyes
node scripts/snapshot_matrix.mjs build/proof-sheet.html \
  --baselines tests/visual/baselines --update-baselines

# every run after that
node scripts/snapshot_matrix.mjs build/proof-sheet.html \
  --baselines tests/visual/baselines --out build/matrix-report
```

One PNG per cell, compared perceptually, HTML report written, exit 1 on regression.

Four things decide whether this survives contact with a team:

- **Component-level shots, not page-level.** A padding change produces one failing cell, not one failing page. The failing cell id *is* the bug report.
- **A meaningful threshold is small.** `--threshold 0.002` — two pixels in a thousand. Tune it once on a clean tree until three consecutive runs pass with margin, then never touch it to make a failure go away.
- **Accept intentional diffs in the same commit as their cause.** A baseline update alone is unreviewable; alongside the CSS change it reads as "this changed, so these 14 images changed".
- **Keep the baseline from becoming noise.** New cells fail by default (an unreviewed cell is not a passing cell). Orphan baselines are reported and pruned with `--update-baselines --prune`.

Determinism, the anti-flake checklist, threshold theory, baseline storage tradeoffs and the no-Playwright fallback are all in `references/visual-regression.md`.

### 5. Gate it

Two gates, one job:

```bash
python -m scripts.audit_design src/ --strict                        # Law 9: the code
python -m scripts.generate_matrix matrix.json --out build/sheet.html \
       --emit-css build/matrix-chrome.css --strict
python -m scripts.audit_design build/matrix-chrome.css              # the sheet obeys the laws too
node scripts/snapshot_matrix.mjs build/sheet.html \
       --baselines tests/visual/baselines --out build/report        # the result
```

Full GitHub Actions file in `references/visual-regression.md` §7. Upload the report directory with `if: always()` — a report you can only download on success is a report you can never use.

---

## Two mechanics worth understanding before you trust the sheet

### Forced pseudo-classes

You cannot hover 200 cells at once, so the generator reads each component's own CSS and mirrors every rule containing `:hover`, `:active`, `:focus-visible` or `:focus`:

```css
/* yours */      .button:hover:not(:disabled)                    { --button-bg: var(--bg-hover); }
/* generated */  .button[data-force-state~="hover"]:not(:disabled) { --button-bg: var(--bg-hover); }
```

Identical specificity (0,3,0 both ways), same layer, later in document order — so it wins on order, not on a fight. Pseudo-classes inside `:not(...)` are left alone, because those are guards, not states. At-rule context is preserved, so a hover rule behind `@media (hover: hover)` stays behind it — and will therefore render only when the harness reports a fine pointer. Headless Chromium does; a mobile emulation context does not. If a hover row looks empty, check for that media query before you conclude the state is missing.

### The token rebind

This one is subtle and it is the reason a naive proof sheet silently lies.

A custom property's `var()` references are substituted **on the element where the property is declared**, not where it is used. So:

```css
:root                    { --density: 1; --pad-card: calc(var(--space-6) * var(--density)); }
[data-density="compact"] { --density: 0.875; }
```

resolves `--pad-card` to 24px *at `:root`* and inherits that number downward. Setting `data-density="compact"` on a descendant changes `--density` there and changes nothing else. Verified in Chromium: a descendant override yields the unchanged 24px.

In a real app this never surfaces, because `data-theme` and `data-density` live on `<html>` — the same element the tokens are declared on. A proof sheet puts three densities and two themes on one page, so it must re-declare, on each stage element, every root token that transitively depends on something a theme or density block re-points. The generator derives that set from your token file rather than hard-coding it, and prints the count in the emitted `<style data-role="token-rebind">` block.

Miss this and the sheet renders every density identically and every dark cell with light-theme shadows — i.e. it passes Law 6 and Law 7 while proving nothing at all.

---

## The pruning rule

The full cross product is `states × variants × sizes × densities × themes × fixtures` and it is in the hundreds to low thousands per component. Nobody reads 1,600 cells, so a full-cross sheet is generated once and never opened again.

**Render the cross-product only of the axes that can interfere. Render the rest independently.** Two axes interfere when they write the same tokens or when one changes the box the other lives in.

| Pass (`--profile pruned`, the default) | Cross product | Catches |
|---|---|---|
| **state** | states × variants × themes | missing states, hover clobbering a variant, dark-mode overlays, invisible focus rings |
| **density** | densities × sizes × variants × themes | hardcoded padding, radii that do not scale, `sm` × `compact` below the tap target |
| **content** | fixtures × densities × themes | overflow, collapse, clipping, translated labels |

Theme is inside every cell in every pass — it is the cheapest axis (it adds no rows) and the highest yield.

`--profile full` gives the complete cross product. Use it when the pruned sheet found something and you want its exact boundary, or right after you change the token layer. Not on every CI run. Full justification, including the interference table, is in `references/state-coverage.md` §3.

---

## Manifest schema

```jsonc
{
  "$schema": "component-state-matrix/1",   // required, exact
  "project":  "Acme",                      // title on the sheet
  "tokens":   "styles/tokens.css",          // inlined; also the source of the rebind set
  "base":     ["styles/base.css"],          // optional, inlined after tokens
  "templates":"templates.html",             // file of <template id="…"> markup
  "themes":   ["light", "dark"],            // values written to data-theme
  "densities":["compact","comfortable","spacious"],

  "components": [{
    "name":     "button",                   // required; cell ids derive from it
    "title":    "Button",                   // optional display name
    "note":     "…",                        // optional prose under the heading
    "css":      "components/button.css",    // required; string or array
    "template": "<button class=\"button\" {attrs}>{content}</button>",
                                            // inline, OR use template_id below
    "template_id": "button",                // id in the templates file
    "wrapper":  "<table><tbody>{slot}</tbody></table>",
                                            // for components needing a parent
    "variants": ["default","primary"],      // "default" emits no data-variant
    "sizes":    ["default","sm"],           // "default" emits no data-size
    "states":   ["default","hover","selected","selected+hover"],
                                            // the seven, custom ones, a+b
    "custom_states": { "selected": {"attrs": {"aria-selected":"true"}} },
                                            // detect defaults to the attribute
    "content":  { "default": "Save", "long-string": "…" },
                                            // fixture name -> HTML
    "stage_style": { "--msheet-well": "var(--pad-card)" },
                                            // inline style, custom props ONLY
    "state_attrs": { "loading": {"data-busy":"1"} },
                                            // override the default state attrs
    "state_detect": { "error": ["[data-err"] },
                                            // override coverage detection
    "form_control": true                    // force/suppress the real `disabled`
  }]
}
```

Notes:

- **`{attrs}` is mandatory** in a template. `{content}` is not a substitute for it — a template may omit `{content}` (a void element like `<input>` has none) but never `{attrs}`: without it, state, variant and size cannot be applied and every cell renders identically — the generator refuses.
- **`stage_style` keys must all start with `--`.** Law 4 permits inline style only when every key is a custom property; the generator enforces it and tells you why.
- **`disabled` is applied intelligently**: a real `disabled` attribute on form controls (detected from the template, overridable with `form_control`), `aria-disabled="true"` otherwise. Never both on a `<div>`, which is invalid. **`error`** likewise: `aria-invalid="true"` only on a form control, `data-state="error"` everywhere.
- **The focus-visible cell carries `focus-visible focus focus-within`**, so a ring written with `:focus` or `:focus-within` renders there too.

---

## Scripts

### `scripts/generate_matrix.py` — stdlib Python 3, no dependencies

| Flag | Does |
|---|---|
| `--out FILE` | the HTML sheet (required) |
| `--root DIR` | base for relative manifest paths (default: manifest's directory) |
| `--themes a,b` | subset of the manifest's themes |
| `--densities a,b` | subset of the manifest's densities |
| `--only NAME` | one component; repeatable or comma-separated |
| `--profile pruned\|full` | which passes to render (default `pruned`) |
| `--emit-css FILE` | write the sheet's own chrome stylesheet for auditing |
| `--strict` | exit 1 on any state-coverage gap |

Exit `0` written · `1` `--strict` with gaps · `2` bad arguments or an invalid manifest.

**`--emit-css` exists because the sheet is a demonstration of the system it tests.** A hardcoded value in the generator's own output is a bug, so the chrome stylesheet is written out separately and audited like any other file. It carries no `@generated` marker on purpose — `audit_design.py` skips generated files, and a skipped audit proves nothing.

The sheet's chrome lives in its own `matrix` cascade layer, declared after `utilities` and before `overrides`, so it can never out-rank the components under test by accident.

### `scripts/snapshot_matrix.mjs` — Node + Playwright, no other dependencies

| Flag | Does |
|---|---|
| `--baselines DIR` | where baseline PNGs live (default `./matrix-baselines`) |
| `--out DIR` | report, current shots and diffs (default `./matrix-report`) |
| `--update-baselines` | accept everything as the new truth |
| `--prune` | with the above, delete baselines with no cell |
| `--threshold N` | max fraction of differing pixels per cell (default `0.002`) |
| `--pixel-threshold N` | perceptual tolerance per pixel, 0..1 (default `0.03`: the suite's 4% hover overlay is a distance of ~0.038) |
| `--allow-new` | a cell with no baseline is not a failure |
| `--only SUBSTR` | only cells whose id contains SUBSTR; repeatable |
| `--viewport WxH`, `--dpr N` | pinned rendering geometry |
| `--browser PATH` | chromium executable (default `$MATRIX_CHROMIUM`, else the first that starts of `/opt/pw-browsers/chromium`, Playwright's own Chromium, an installed Chrome or Edge — pin one for baselines shared across machines) |

Exit `0` clean or updated · `1` regression, new cell or capture error · `2` bad arguments, no usable browser, or a run that failed.

**It never downloads a browser.** It launches with an explicit `executablePath` and fails with instructions if nothing is there. Install the module with `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i -D -E playwright` to use the Chrome you have. CI pins the browser instead. It installs the Chromium that the locked Playwright was built for, which the script tries first (`references/visual-regression.md` §7).

Comparison runs on a canvas **inside the browser** — no `pixelmatch`, no `pngjs`, no `sharp`, nothing to compile. The metric is YIQ colour distance (luma weighted far above chroma, because that is how eyes work) with a 3×3 neighbourhood escape so sub-pixel antialiasing costs nothing.

---

## Routing

| Situation | Go to |
|---|---|
| Building or restyling the system itself | `web-design-studio` |
| An inherited codebase not yet on tokens | `design-token-migration` |
| Design file and code have drifted apart | `figma-variables-sync` |
| **Every state × density × theme actually renders** | **here** |
| Copy, offer and persuasion on a landing page | `landing-page-conversion` |
| Adversarial review before a client sees it | `design-critique-gate` |

Within this skill:

| You want | Read |
|---|---|
| the token vocabulary | `references/token-contract.md` |
| what each state means, must not do, and looks like when missing | `references/state-coverage.md` |
| why the combinatorics prune the way they do | `references/state-coverage.md` §3 |
| the per-archetype "what is usually missing" checklist | `references/state-coverage.md` §4 |
| making screenshot diffing survive a team | `references/visual-regression.md` |
| CI wiring | `references/visual-regression.md` §7 |
| doing this without Playwright at all | `references/visual-regression.md` §8 |

---

## The three sentences to remember

1. **An unwritten state is invisible to a linter and obvious on a proof sheet** — that gap is the whole reason this skill exists.
2. **The manifest is hand-written because what you meant to support is the thing under test**; infer it from the CSS and you have proved only that your code matches your code.
3. **Render the cross-product only of the axes that interfere** — everything else is independent, and a sheet nobody reads proves nothing.

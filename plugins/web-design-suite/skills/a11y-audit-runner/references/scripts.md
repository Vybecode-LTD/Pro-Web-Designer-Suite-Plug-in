# The two scripts, in full

Every flag and check of `a11y_static.py` and `a11y_runtime.mjs`, the key-map file, and what a failing run prints. `SKILL.md` has the workflow; this is the reference behind it.

## 1. `scripts/a11y_static.py` — stdlib Python 3, no dependencies

The sibling of `audit_design.py`: same report shape, same severity model, same baseline philosophy, same comment pragmas, same exit codes. It parses HTML **and** JSX/TSX — React's `className`/`htmlFor` are normalised, and a `{dynamicValue}` attribute is treated as *present but unknowable* rather than as empty, because a false positive on a runtime value is how a linter gets switched off.

| Cat | Checks |
|---|---|
| **S** Structure | heading level skips, multiple `h1`, no `h1`, missing `<main>`, multiple `<main>`, unlabelled duplicate landmarks, landmark labels that repeat the role, missing/invalid `lang`, missing/empty `<title>`, `user-scalable=no` |
| **N** Name | `<img>` with no `alt`, `alt` that is a filename or a placeholder, `alt` opening "image of", empty buttons and links, non-descriptive link text, bare-URL links, duplicate control names |
| **K** Keyboard | positive `tabindex`, click handlers on non-interactive elements (graded by what is missing), `aria-hidden` over focusable content, `role="presentation"` on a focusable element, `outline: none` with no replacement, **a focus ring made only of `box-shadow`**, focus rules that set nothing visible, transitioned outlines |
| **R** ARIA | invalid `aria-*` names (with a spelling suggestion — `aria-labeledby` is the classic), invalid `aria-*` values by type, `aria-*` pointing at an id that does not exist, invalid roles, redundant explicit roles, duplicate ids |
| **F** Forms | controls with no label by any of the four mechanisms, `title`-as-label, placeholder-as-label, missing `autocomplete` on personal-data fields (**SC 1.3.5**), invalid `autocomplete` tokens |

Every finding carries its **success criterion**, because "the linter says so" loses an argument and "1.3.5, and here is the fix" does not.

```bash
python -m scripts.a11y_static src/                      # audit
python -m scripts.a11y_static src/ --strict             # warnings fail too
python -m scripts.a11y_static src/ --category F --category K
python -m scripts.a11y_static src/ --sc 1.3.5           # one criterion
python -m scripts.a11y_static src/ --json
python -m scripts.a11y_static src/ --write-baseline .a11y-baseline.json
```

Escape hatches are comment pragmas in every syntax these files use, so each exception is visible in review. Everything after `--` is the reason, and a pragma with no reason should not survive review:

```html
<!-- a11y-audit-ignore-next-line: N -- alt comes from the CMS, A11Y-88 -->
```
```jsx
{/* a11y-audit-ignore-next-line: K -- third-party embed, ticket A11Y-91 */}
```

Exit `0` clean · `1` violations · `2` bad invocation.

---

## 2. `scripts/a11y_runtime.mjs` — Node + Playwright + axe-core

```bash
node scripts/a11y_runtime.mjs --url http://127.0.0.1:8080/
node scripts/a11y_runtime.mjs --url http://127.0.0.1:8080/ --keymap a11y-keymap.json
node scripts/a11y_runtime.mjs --matrix build/proof-sheet.html --only "button--"
node scripts/a11y_runtime.mjs --file dist/index.html --tags wcag2a,wcag2aa,wcag21a,wcag21aa,wcag22aa --json
```

| Check | What it does that source analysis cannot |
|---|---|
| `axe` | axe-core with a configurable tag set, violations **and incompletes**, each with selector, impact and fix |
| `names` | the **computed** accessible name and role of every interactive element, via axe's own AccName implementation. Flags empty, duplicate, type-only (`"Button"`), and **2.5.3 Label in Name** — a visible label the accessible name does not contain |
| `taborder` | drives real Tab and Shift+Tab, prints the actual sequence, and names the three failure shapes: a **trap**, a **skip**, a **jump** |
| `focus` | screenshots each control unfocused and focused and differences them: a pixel fraction, and the contrast of the indicator's own strongest band (90th percentile per-pixel, not a mean — a two-band ring's mean is meaningless) |
| `forced` | repeats that measurement under `forced-colors: active` and reports every ring that **vanished** rather than degraded |
| `contrast` | text contrast from computed styles, compositing ancestor backgrounds **and any translucent overlay painted on top** — the case static analysis reports as a pass |
| `keys` | drives Enter, Down arrow, Right arrow and Esc through the dialogs, menus, tabs, disclosures and comboboxes in the key map (`references/runtime-checks.md` §8 lists each assertion); Space, Home and End, arrow wrap, Tab leaving a menu, Esc on a combobox and Tab staying inside a dialog are manual checks |
| `reflow` | 320px-equivalent 400% zoom (1.4.10, an error), naming the widest offender, plus horizontal scroll at 200% zoom as a warning. Clipped or overlapping text at 200% (1.4.4) is a manual check |

| Flag | Does |
|---|---|
| `--url` · `--file` · `--matrix` | exactly one; they are three different jobs |
| `--tags LIST` | axe tag set (default `wcag2a,wcag2aa,wcag21a,wcag21aa,wcag22aa,best-practice`). A best-practice rule names no success criterion, so its findings are warnings and never fail the run, whatever axe rates its impact |
| `--keymap FILE` | expected keyboard behaviour per pattern |
| `--budget FILE` | counter limits, as JSON `{"key": limit}`; non-zero exit on breach, and an unknown key exits 2. Keys: `axe_violations`, `axe_serious`, `axe_incomplete`, `unnamed_controls`, `duplicate_names`, `tab_traps`, `unreachable_controls`, `focus_invisible`, `focus_weak`, `forced_colors_lost`, `contrast_failures`, `reflow_failures`, `keymap_failures` |
| `--only SUBSTR` | with `--matrix`, narrow to matching cells (repeatable). It does not pick checks, so a page refuses it: use `--skip` |
| `--densities LIST` | on a page, the `data-density` values to measure focus at as well, in normal and forced colours (default `auto`: each one the page's own stylesheets name; `none` turns it off) |
| `--skip CHECK` | `axe names taborder focus forced contrast keys reflow` (repeatable) |
| `--max-stops` · `--max-cells` · `--focus-threshold` · `--viewport` · `--dpr` · `--axe` · `--browser` · `--json` · `--quiet` | |

Exit `0` no errors and inside budget · `1` violations or breach · `2` bad arguments, no browser, no axe, page failed to load, or the run failed: a crash is never a finding.

**axe is injected from `node_modules`, never a CDN, and the browser is never downloaded.** A gate that depends on a third-party CDN goes red when that CDN does, and a team taught that red means "re-run it" is a team with no gate.

Four things it does that most runtime checks do not:

- **It prints the tab order.** Enormously useful, almost never done. The sequence is the page as a keyboard user receives it, and a bad one is obvious on sight.
- **It measures the ring instead of reading the stylesheet.** `:focus-visible` existing in CSS is not evidence. A row reading `19.52% → 0.00%` between normal and forced-colors is.
- **It composites overlays before judging contrast.** On the fixture, text declared at **5.33:1** renders at **1.46:1** under a 72% scrim. Every source-level contrast checker calls that a pass.
- **It refuses to guess.** Text over a background image is reported as *unmeasurable*, not as a pass, because contrast against a photograph varies per pixel and the worst pixel is the one that matters.

### The keymap file

```json
{
  "$schema": "a11y-audit-runner/1",
  "patterns": [
    { "name": "Account menu", "pattern": "menu", "trigger": "#acct-btn",
      "container": "#acct-menu", "items": "[role=menuitem]" },
    { "name": "Settings dialog", "pattern": "dialog",
      "trigger": "#open-settings", "container": "dialog#settings" },
    { "name": "Docs tabs", "pattern": "tabs", "container": "#tabs" },
    { "name": "Shipping details", "pattern": "disclosure", "trigger": "#disc" }
  ]
}
```

Patterns: `dialog` `menu` `tabs` `disclosure` `combobox`. Everything else is a manual check and the tool says so rather than passing it silently. Without `--keymap`, the run warns that **no composite widget on the page was verified at all** — which is the honest state of most CI accessibility jobs.

---

## 3. What a failing run looks like

Static layer, on a fixture with twenty planted violations:

```
/tmp/a11y-fixture/bad.html
      3  error  S no-lang                      <html> has no `lang` attribute.
     18  error  K outline-none-no-replacement  `.plain:focus` sets `outline: none` and
                                               provides no replacement indicator.
     25  error  K focus-ring-shadow-only       `.shadowring:focus-visible` replaces the
                                               outline with `box-shadow` alone.
     53  error  K positive-tabindex            `tabindex="3"` on <a>.
     65  warn   S heading-skip                 Heading level jumps h1 → h3 ("Findings").
     70  error  N img-no-alt                   <img> has no `alt` attribute (src=chart.png).
     73  error  N alt-is-filename              `alt="team.jpg"` is a filename.
     85  error  F placeholder-as-label         <input> is named only by `placeholder`.
     89  error  F missing-autocomplete         <input name="email"> collects the user's own
                                               data and has no `autocomplete` (expected `email`).
     92  error  R aria-unknown-attr            `aria-labeledby` is not an ARIA attribute —
                                               did you mean `aria-labelledby`?
    110  error  R aria-dangling-ref            `aria-describedby` points at id(s) that do not
                                               exist in this file: hint-that-does-not-exist.
    113  error  K handler-on-noninteractive    <div> has `onclick` and is missing a role,
                                               tabindex="0", a keyboard handler.
    123  error  K aria-hidden-focusable        `aria-hidden="true"` on <div> which contains
                                               1 focusable element(s).

  23 error(s), 6 warning(s) across 1 file(s).
```

Runtime layer, same page. The tab order listing is the part to read first:

```
Tab order as measured (the real sequence, not the DOM order)
    1. nav:nth-of-type(1) > a:nth-of-type(2)  [tabindex=3]  "Pricing"   ← runs first
    2. nav:nth-of-type(1) > a:nth-of-type(1)  "Home"
    …
   16. button#trap-a  "Trap A"
   17. button#trap-b  "Trap B"
  ↺ from step 18 the sequence repeats, cycling among 2 element(s) for the remaining
    39 press(es) — button#trap-a, button#trap-b. A cycle this short is a TRAP, not a wrap.

Focus indicator, measured in pixels
  normal   forced    contrast  element
    9.66%    9.84%   19.02:1  input#email
    0.00%    0.00%       n/a  form > button.plain            ← no indicator at all
   19.52%    0.00%    5.68:1  button.shadowring:nth-of-type(1)  ← vanishes in forced-colors
   18.01%   18.69%    5.68:1  button.goodring:nth-of-type(4)    ← the paired ring survives

CONTRAST
  error  contrast-under-overlay  "This paragraph sits under a 72% white scrim." measures
                                 1.46:1 (needs 4.5:1 at 16px) — 1 translucent overlay(s)
                                 composited in. The colour pair in the stylesheet reads
                                 as 5.33:1.
```

Three lines in that output are things no source-level tool can produce: the trap, the `19.52% → 0.00%` ring, and the `5.33:1 → 1.46:1` overlay. They are also three of the most common real-world failures, which is the argument for layer two in one screen.

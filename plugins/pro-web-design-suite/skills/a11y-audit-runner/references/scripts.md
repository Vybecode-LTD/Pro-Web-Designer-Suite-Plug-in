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
# The baseline it reads: --baseline, else .design-suite.json's baselines.a11y, else .a11y-baseline.json
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
| `reflow` | 320px-equivalent 400% zoom (1.4.10, an error), naming the widest offender, plus horizontal scroll at 200% zoom as a warning; and text a box clips at 200% (1.4.4) or 320px (1.4.10) that it did not clip at the page's own width, an error (text that runs past its box is a warning). Overlapping text is a manual check |
| `spacing` | WCAG's text spacing (line height 1.5, paragraph spacing 2, letter spacing 0.12, word spacing 0.16, each `!important`, in every shadow root too), then the text a box newly clips (1.4.12, an error) or spills (a warning) |
| `obscured` | Tab from the top, Shift+Tab from the bottom: at each stop, a 5×5 hit test against the fixed and sticky elements over it. Entirely hidden is `focus-obscured` (2.4.11, an error); partly, a warning (2.4.12 is AAA) |
| `hover` | each control whose `aria-describedby` names a node hidden at rest (twelve at most), hovered, else focused: the content persists a second, survives the pointer moving onto it, and closes on Esc where it covers other text (1.4.13, errors) |
| `motion` | the page opened with and without `prefers-reduced-motion: reduce`, animations running, scrolled to the end: motion the preference did not reduce, text it left hidden, and a busy loop it stopped. The suite's policy, so warnings (`runtime-checks.md` §6) |

The last four, like `reflow` and `taborder`, run on a page and not on a proof sheet: a `--matrix` run leaves them out of its report's `ran` and lists them under `notRun`, so a budget on them is not met by checks that never ran.

| Flag | Does |
|---|---|
| `--url` · `--file` · `--matrix` | exactly one; they are three different jobs |
| `--urls FILE\|URL` · `--viewports LIST` · `--max-urls N` | several pages, several sizes, one report: see *Several pages and viewports* below |
| `--tags LIST` | axe tag set (default `wcag2a,wcag2aa,wcag21a,wcag21aa,wcag22aa,best-practice`). A best-practice rule names no success criterion, so its findings are warnings and never fail the run, whatever axe rates its impact. A rule that names a criterion fails the run whatever its impact, which is axe's guess at severity, not conformance (`no-autoplay-audio` is `moderate`), except on a `--matrix` sheet, where one outside every `[data-cell-id]` cell is the sheet's own chrome: a warning, its rule marked `(sheet chrome)`; `axe_serious` counts only critical and serious impacts |
| `--keymap FILE` | expected keyboard behaviour per pattern |
| `--budget FILE` | counter limits, as JSON `{"key": limit}`; non-zero exit on breach, and an unknown key exits 2. Keys (a best-practice violation counts in none of them; an incomplete result counts in `axe_incomplete`, whatever its tags): `axe_violations`, `axe_serious`, `axe_incomplete`, `unnamed_controls`, `duplicate_names`, `tab_traps`, `unreachable_controls`, `focus_invisible`, `focus_weak`, `focus_not_measured` (stops whose focus screenshots failed, so neither passed nor failed), `forced_colors_lost` (a ring lost under forced colours, never the warning that they could not be emulated), `contrast_failures`, `reflow_failures`, `keymap_failures`, `text_spacing_failures`, `focus_obscured`, `hover_content_failures`, `motion_not_reduced`, `motion_content_hidden`, `motion_busy_stopped`. Without it, the project's `.design-suite.json` `budgets.a11y` (web-design-studio's `references/project-contract.md`). |
| `--only SUBSTR` | with `--matrix`, narrow to matching cells (repeatable). It does not pick checks, so a page refuses it: use `--skip` |
| `--densities LIST` | on a page, the `data-density` values to measure focus at as well, in normal and forced colours (default `auto`: each one the page's own stylesheets name; `none` turns it off) |
| `--skip CHECK` | `axe names taborder focus forced contrast keys reflow spacing obscured hover motion` (repeatable) |
| `--engine NAME` | `chromium` (the default), `firefox` or `webkit`: see *Other engines* below |
| `--wait-for SEL` · `--steps FILE` · `--storage-state FILE` · `--header "Name: V"` | reach the page its users get: see *Reaching the page* below |
| `--viewport WxH` | the page's size (default 1280x900). Under 768 px wide it is a touch phone, as the critique captures one: `isMobile` and `hasTouch`, so `(hover: none)` and `(pointer: coarse)` match and a page with no viewport meta is laid out 980 px wide. The JSON report's `mobile` is `true`, and the text report names the size `as a touch phone`. Reflow is measured in a desktop window all the same, since 1.4.10 is in CSS pixels |
| `--max-stops` · `--max-cells` · `--focus-threshold` · `--dpr` · `--axe` · `--browser` · `--json` · `--quiet` | |

Exit `0` no errors and inside budget · `1` violations or breach · `2` bad arguments, no browser, no axe, page failed to load, or the run failed: a crash is never a finding. The report names the browser it launched and its build (`browser`, `browserVersion`), as each of the suite's browser scripts does, so a run says which engine build it measured.

### Reaching the page

At `load` a client-rendered page is still an empty shell, and a signed-in page has gone to its sign-in. Audited as it stands, either passes, because there is almost nothing on it. Four flags reach the page its users get. design-critique-gate's `critique_snapshots.mjs` takes the same four, and perf-budget-gate's `measure_vitals.mjs` takes `--wait-for` and `--storage-state`.

| Flag | Does |
|---|---|
| `--wait-for SEL` | waits up to 30 s for `SEL` to be visible, after any steps |
| `--steps FILE` | runs a JSON list of steps once the page has loaded, 15 s for each |
| `--storage-state FILE` | opens every context with a session: Playwright's `storageState`, the cookies and localStorage. `npx playwright codegen --save-storage=session.json URL` writes one after you sign in by hand |
| `--header "Name: V"` | sends a header with every request to the page's own origin, never to a third party's. `V` may be `env:NAME`, read from the environment, which keeps a token off the command line (repeatable) |

```bash
node scripts/a11y_runtime.mjs --url http://127.0.0.1:3000/ --wait-for "main h1"
node scripts/a11y_runtime.mjs --url http://127.0.0.1:3000/account --storage-state session.json
node scripts/a11y_runtime.mjs --url https://staging.example.com/ --header "Authorization: env:STAGING_TOKEN"
node scripts/a11y_runtime.mjs --url http://127.0.0.1:3000/search --steps search-steps.json
```

```json
[
  {"fill": "#email", "value": "qa@example.com"},
  {"fill": "#password", "env": "QA_PASSWORD"},
  {"click": "button[type=submit]"},
  {"wait-for": "nav[aria-label=Account]"},
  {"goto": "/settings"}
]
```

Each step has one action: `click`, `fill` (a `value`, or `env` naming a variable, so a password stays out of the file), `press` (a key, with `on` for an element), `goto` (resolved against the page's URL) or `wait-for`. The steps, the session and the headers apply in every context the audit opens, the forced-colours pass included. A mistake in a file, a step that fails, a wait that never ends or an HTTP error status exits 2, naming it: a page never reached is not audited. A storage-state file is a live session, so keep it out of the repository.

**axe is injected from `node_modules`, never a CDN, and the browser is never downloaded.** A gate that depends on a third-party CDN goes red when that CDN does, and a team taught that red means "re-run it" is a team with no gate.

Four things it does that most runtime checks do not:

- **It prints the tab order.** Enormously useful, almost never done. The sequence is the page as a keyboard user receives it, and a bad one is obvious on sight.
- **It measures the ring instead of reading the stylesheet.** `:focus-visible` existing in CSS is not evidence. A row reading `19.52% → 0.00%` between normal and forced-colors is.
- **It composites overlays before judging contrast.** On the fixture, text declared at **5.33:1** renders at **1.46:1** under a 72% scrim. Every source-level contrast checker calls that a pass.
- **It refuses to guess.** Text over a background image is reported as *unmeasurable*, not as a pass, because contrast against a photograph varies per pixel and the worst pixel is the one that matters.

### Other engines

Focus heuristics, the accessibility tree and the tab order differ between Chromium, Firefox and WebKit, and a page tested in Chromium alone ships those differences unseen. `--engine firefox` or `--engine webkit` runs `axe`, `names` and `taborder` in the build the loaded Playwright was built for, or in `--browser PATH`. When that build is missing, the error names the command that installs it: the loaded Playwright's own CLI, by path, since `npx` may run another version. The other checks are **Chromium's**: `focus` and `forced` difference screenshots and emulate forced colours, `contrast` and the clipping checks were calibrated in Chromium's rendering, and closed shadow roots are read through Chromium's DevTools protocol (so another engine always reports `closed-shadow-roots-unread`). A run in another engine says which checks it left out (`checks-run-in-chromium-only`, a warning), and its JSON names the `engine`. It is a second pass, never a replacement for the Chromium run.

Tab may pass over every link with no `tabindex`: Safari does unless its reader turns on *Press Tab to highlight each item*, and so do WebKit's Windows and macOS builds and Firefox on macOS; WebKit's Linux build does not. The run reads which from the sequence it drove, never assumes it: outside Chromium, when Tab reached none of those links, the tab order expects none and `engine-skips-links` (a warning) says so. A link with `tabindex="0"` is a stop either way. Playwright's Firefox build is unsigned, and a Windows machine with Smart App Control may refuse to start it: run that engine in CI on Linux.

### Shadow roots

Every check reads through shadow roots, open and closed (`runtime-checks.md` §1). A path names an element inside one host by host, with ` >> ` at each boundary: `main > x-card >> button.icon`, or `x-outer >> div.frame > x-inner >> button.deep` for a component inside a component. Playwright's `locator()` reads the same path through open roots. A keymap's selectors take the same form, and a plain selector is looked for in the document first, then through every root. The JSON's `shadowRoots` counts the roots read (`open`, `closed`) and `unread`, the closed roots no check could read: when it is not 0, or `null` because the browser offers no DevTools protocol, a `closed-shadow-roots-unread` warning says so. A root no check read is never a silent pass.

### Several pages and viewports

A run audits one page at one size, and a site is many templates, with a phone's menu and its target sizes (2.5.8) hidden at 1280x900. `--urls` lists the pages: a file of URLs, one a line (blank lines and `#` lines skipped), a JSON list of URLs (or of `{"url", "pageType"}`), or a `sitemap.xml`, from a file or an http(s) URL; a sitemap index is refused, so name one of its sitemaps. `--viewports 390x844,1280x900` runs each page at each size, and works with one `--url` too. Each run is the script on one page at one size, in a process of its own, with every other option; the report holds a row for each (its errors, warnings and exit), the errors of each failing run, and every run's whole report in `--json` and `--report`. The exit is the worst run's, so a page that does not load (exit 2) is never outweighed by the ones that pass. Each run says what it is doing as it goes, under its `[i/n]` line, and has 15 minutes: one that hangs is stopped, fails its own row (exit 2, "timed out"), and the pages after it still run. `--max-urls N` (default 50) caps the pages, and those past it are counted in the report, never dropped in silence. The steps, the session and the headers apply on every page, so sign in with `--storage-state` rather than steps written for one page.

```bash
node scripts/a11y_runtime.mjs --urls http://127.0.0.1:3000/sitemap.xml --viewports 390x844,1280x900
```

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

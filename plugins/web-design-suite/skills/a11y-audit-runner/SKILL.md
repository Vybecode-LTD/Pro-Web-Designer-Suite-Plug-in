---
name: a11y-audit-runner
description: Automate accessibility testing and enforce WCAG 2.2 AA in CI — axe-core on every commit, plus the runtime and manual layers automation cannot replace. Use for "is my site accessible", an accessibility audit or report, VPAT/ACR evidence, accessibility regression testing, keyboard navigation testing, focus order verification, screen reader testing and colour contrast auditing. Reach for it whenever anyone mentions axe, Lighthouse accessibility, pa11y, WAVE, jest-axe, WCAG or Section 508 compliance, EN 301 549 or the European Accessibility Act, ADA, a procurement accessibility questionnaire, alt text, ARIA, focus traps, tab order, accessible names, landmarks, heading structure, forced-colors or Windows High Contrast, screen readers (NVDA, JAWS, VoiceOver, TalkBack), or 200%/400% zoom and reflow — and any time someone says the site passed axe so it must be accessible, which is the sentence this skill exists to answer.
---

# Accessibility Audit Runner

> **Running the scripts** — by path, from the user's project root, so `src/`
> means the project's `src/` and every output lands in the project, never
> inside this plugin:
>
> ```bash
> python "${CLAUDE_SKILL_DIR}/scripts/a11y_static.py" src/
> ```
>
> The commands below are written `python -m scripts.<name>`. That form is for a project that
> has copied the scripts into its own `scripts/` folder, as CI and git hooks
> do; when you run one here, use the path form.
> This skill's scripts are in `${CLAUDE_SKILL_DIR}/scripts/` (a11y_runtime.mjs, a11y_static.py).
> From sibling skills: `${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/audit_design.py`.

**Automated tools catch roughly a third of WCAG issues.** Start here, say it out loud, and build everything else on top of it.

The number is not a rhetorical hedge. In the only controlled study with a known denominator — the UK Government Digital Service, 2017, a page with **143 deliberately planted failures across 19 categories**, run through ten automated tools — the best single tool found **37%** (Tenon, errors and warnings) to **41%** (Asqatasun, counting its manual-inspection prompts). All ten tools *combined* found 71%. **29% of the barriers were found by no tool at all.** ([GDS](https://accessibility.blog.gov.uk/2017/02/24/what-we-found-when-we-tested-tools-on-the-worlds-least-accessible-webpage/))

Deque's widely-quoted **57%** is a different measurement, and worth understanding rather than dismissing: it counts issues **by volume** across 2,000+ audits and 13,000 pages, not success criteria, and it is produced by a suite that includes Intelligent Guided Testing — a human answering questions. ([Deque, 2021](https://www.deque.com/blog/automated-testing-study-identifies-57-percent-of-digital-accessibility-issues/)) Both numbers point the same way: the machine-detectable failures are the *most common* ones, and they are a *minority of the criteria*.

Why that is true is not mysterious. Most of WCAG turns on **meaning**. Is this alt text correct? Is this link text meaningful where it sits? Is this error message helpful? Does this focus order make sense? Meaning is not computable. `alt="image"` passes every scanner ever written.

So the value proposition of this skill is precise, and it is not "we are now accessible":

> **The third a machine can catch is caught on every commit, for free, forever — so every hour of human attention goes to the two thirds that need judgement.**

And the risk is equally precise. **A green CI badge is the single most effective way to stop a team doing the manual pass.** That is why the manual protocol is step 4 of the workflow and not an appendix, why every script prints the coverage caveat in its own output, and why `references/automation-coverage.md` ends with the exact wording to put in a client report instead of the word "accessible".

---

## Why this skill exists

`web-design-studio/references/accessibility.md` already specifies the floor: the WCAG 2.2 AA criterion table, the focus contract, the 12-pattern keyboard map, forced-colors, the alt-text decision tree. **It is the specification and this skill does not restate it.** Read it for *what* is required; read this for *how it gets checked, on every commit, by something other than a person's memory.*

The suite's own argument, from `perf-budget-gate`: **the thing that is measured is the thing that gets fixed.** Design has `audit_design.py`. Performance has `perf_audit.py` and `measure_vitals.mjs`. States have the proof sheet. Accessibility, until now, had a well-written document and a hope.

| | `audit_design.py` | `perf_audit.py` | **`a11y_static.py` + `a11y_runtime.mjs`** |
|---|---|---|---|
| Asks | "is this code legal?" | "is this page within budget?" | **"can a person who is not you operate this?"** |
| Fails when | someone writes `margin: 24px` | someone adds a dependency | **someone writes `<div onclick>`** |
| Blind to | a perfectly tokenized unlabelled input | a fast page nobody can use | a slow page everybody can use |
| Catches | 100% of its rules | 100% of its rules | **~a third of its domain, and it says so** |

That last cell is the difference that matters. The design gate is complete over its own rules. This one is not complete over accessibility and cannot be. **A gate that is honest about its ceiling is usable; a gate that implies it is complete is worse than none**, because it ends the conversation.

---

## The three layers

| | **1 · Static** | **2 · Runtime** | **3 · Human** |
|---|---|---|---|
| Tool | `scripts/a11y_static.py` | `scripts/a11y_runtime.mjs` | `references/manual-protocol.md` |
| Reads | source text | a rendered browser | a person's experience |
| Runtime | ~1 second | ~30–90 seconds | 45–90 minutes per template |
| Needs | Python 3 stdlib | Chromium, axe-core, a served build | a keyboard, a screen reader, attention |
| Runs on | **every commit** | PR, and main after merge | **every release, and every new pattern** |
| Catches | missing `alt`, unlabelled input, positive `tabindex`, dangling `aria-*`, `outline:none` | axe violations, **computed** accessible names, the real tab order, focus rings measured in pixels, forced-colors loss, composited contrast | whether any of it makes sense |
| Misses | anything that depends on rendering | anything that depends on meaning | nothing, and that is why it is expensive |

**Install them in order and do not skip the third.** The static layer is deterministic and costs a second, so it earns trust. The runtime layer needs a browser and care, so it spends that trust. The human layer is the only one that can find the two thirds — and the only one a team stops doing the moment layers 1 and 2 go green.

The split between 1 and 2 is not arbitrary. `outline: none` is visible in source. **Whether a focus ring is actually visible is not** — it can be overridden later in the cascade, clipped by an ancestor's `overflow`, drawn in a colour identical to its background, or composed entirely of `box-shadow`, which forced-colors mode discards. Only pixels answer that, which is why layer 2 screenshots each control focused and unfocused and differences them.

---

## Workflow

### 1. Turn on the static gate today, with a baseline

```bash
python -m scripts.a11y_static src/
python -m scripts.a11y_static src/ --write-baseline .a11y-baseline.json
git add .a11y-baseline.json
```

Existing debt is frozen; new violations fail immediately. **A gate that fails on day one is a gate somebody deletes on day two.** Pay the baseline down per directory, starting with the categories a user feels first: `F` (labels), `K` (focus), `N` (names).

Wire it into the design gate's hook — one hook, both gates, and the commit is refused if either fails. Use the shipped hook rather than a hand-written one: it quotes file names with spaces, skips files that are not code, and reports every gate's verdict.

```bash
cp <web-design-studio>/assets/configs/pre-commit-design-gate.sh .git/hooks/pre-commit
mkdir -p scripts
cp <web-design-studio>/scripts/audit_design.py scripts/        # Law 9
cp <a11y-audit-runner>/scripts/a11y_static.py scripts/         # the accessibility floor
```

The hook runs `a11y_static` on the staged files whenever `scripts/a11y_static.py` is present (set `DESIGN_GATE_A11Y_MODULE` if you keep it elsewhere). A hand-rolled `.githooks/pre-commit` with no shebang does not run at all under Git for Windows, and one without `set -e` passes whenever its LAST command passes.

Never put the runtime layer in a pre-commit hook. A minute of browser time per commit is how a team discovers `--no-verify`.

### 2. Add the runtime layer on a served build

```bash
npm install axe-core
python3 -m http.server 8080 --directory dist &
node scripts/a11y_runtime.mjs --url http://127.0.0.1:8080/ --budget a11y-budget.json
```

Read the output in this order, because that is the order of yield:

1. **The tab order listing.** It is the fastest way to see a page the way a keyboard user does, and the failure is usually obvious the moment it is written down.
2. **Traps and unreachable controls.** Fix the trap first — the unreachable list usually empties by itself, because those controls were only unreachable because focus never got past the trap.
3. **The focus-indicator table**, normal column against forced column. A row that reads `19.52% → 0.00%` is a ring that exists and vanishes for Windows High Contrast users.
4. **Empty accessible names.** These are computed from the rendered tree, so if you thought a control had a name, the mechanism you used is not working.
5. **axe violations**, which by now you already know the shape of.
6. **axe *incompletes*.** An incomplete is axe saying a human must look. It is not a pass, and a CI job that reports only violations drops this class silently.

### 3. Audit every state, not just every page

```bash
node scripts/a11y_runtime.mjs --matrix build/proof-sheet.html
```

A page-level audit sees each component in exactly one state: whatever it happened to be rendered in. The `component-state-matrix` proof sheet renders every component at every state × density × theme with a stable `data-cell-id` per cell, and this reads that sheet directly.

The payoff is specific and large. **A focus ring can be present in light and absent in dark, present at comfortable density and clipped at compact, present on the default variant and invisible on the primary fill.** Every one of those passes a page-level audit. On the fixture built for this skill — a `.button` whose ring is `box-shadow` only, and a `.chip` whose ring pairs the shadow with a transparent outline — the matrix pass reported **24 of 34 measured rings disappearing in forced-colors**: every single button cell, and not one chip cell. No page audit would have found more than one of them.

### 4. Run the human pass — `references/manual-protocol.md`

Not once, at the end. **Per template, before release, on a schedule.** The protocol is timed and scripted so it is repeatable by someone who is not an accessibility specialist: a keyboard-only walkthrough, a five-task screen-reader script, zoom, images off, stylesheet off, a cognitive-load pass, and how to write a finding so it actually gets fixed.

> **The audit order that works: keyboard, then zoom and reflow, then forced colors, then a screen reader pass, then run the scanner to catch what you missed.** Running the scanner first produces a false sense of completion, which is the most expensive outcome available.

### 5. Report it honestly

Never write "accessible" because CI is green. `references/automation-coverage.md` §7 has the wording to use instead, for a client report, a VPAT/ACR and a procurement questionnaire. The short version:

> *"Automated checks (axe-core 4.13, WCAG 2.2 A/AA rule set) pass with zero violations on all 14 templates. Automated testing covers an estimated third of WCAG success criteria; the manual evaluation recorded in Appendix B covers the remainder. Two criteria are Partially Supported — see the exceptions table."*

That paragraph survives scrutiny. "Our site is WCAG 2.2 AA compliant, verified by automated testing" does not, and in the EU under the European Accessibility Act it is a statement someone can act on.

---

## `scripts/a11y_static.py` — stdlib Python 3, no dependencies

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

## `scripts/a11y_runtime.mjs` — Node + Playwright + axe-core

```bash
node scripts/a11y_runtime.mjs --url http://127.0.0.1:8080/
node scripts/a11y_runtime.mjs --url http://127.0.0.1:8080/ --keymap a11y-keymap.json
node scripts/a11y_runtime.mjs --matrix build/proof-sheet.html --only "button--"
node scripts/a11y_runtime.mjs --file dist/index.html --tags wcag2a,wcag2aa,wcag22aa --json
```

| Check | What it does that source analysis cannot |
|---|---|
| `axe` | axe-core with a configurable tag set, violations **and incompletes**, each with selector, impact and fix |
| `names` | the **computed** accessible name and role of every interactive element, via axe's own AccName implementation. Flags empty, duplicate, type-only (`"Button"`), and **2.5.3 Label in Name** — a visible label the accessible name does not contain |
| `taborder` | drives real Tab and Shift+Tab, prints the actual sequence, and names the three failure shapes: a **trap**, a **skip**, a **jump** |
| `focus` | screenshots each control unfocused and focused and differences them: a pixel fraction, and the contrast of the indicator's own strongest band (90th percentile per-pixel, not a mean — a two-band ring's mean is meaningless) |
| `forced` | repeats that measurement under `forced-colors: active` and reports every ring that **vanished** rather than degraded |
| `contrast` | text contrast from computed styles, compositing ancestor backgrounds **and any translucent overlay painted on top** — the case static analysis reports as a pass |
| `keys` | drives Enter/Space/Arrow/Home/End/Escape/Tab through dialogs, menus, tabs, disclosures and comboboxes and asserts the key map from `accessibility.md` §4 |
| `reflow` | 200% zoom (1.4.4) and 320px-equivalent 400% zoom (1.4.10), naming the widest offender |

| Flag | Does |
|---|---|
| `--url` · `--file` · `--matrix` | exactly one; they are three different jobs |
| `--tags LIST` | axe tag set (default `wcag2a,wcag2aa,wcag21a,wcag21aa,wcag22aa,best-practice`) |
| `--keymap FILE` | expected keyboard behaviour per pattern |
| `--budget FILE` | counter limits; non-zero exit on breach |
| `--only SUBSTR` | with `--matrix`, narrow to matching cells (repeatable) |
| `--skip CHECK` | `axe names taborder focus forced contrast keys reflow` (repeatable) |
| `--max-stops` · `--max-cells` · `--focus-threshold` · `--viewport` · `--dpr` · `--axe` · `--browser` · `--json` · `--quiet` | |

Exit `0` no errors and inside budget · `1` violations or breach · `2` bad arguments, no browser, no axe, page failed to load.

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

## What a failing run looks like

Static layer, on a fixture with twenty planted violations:

```
/tmp/a11y-fixture/bad.html
      3  error  S no-lang                      <html> has no `lang` attribute.
     18  error  K outline-none-no-replacement  `.plain:focus` sets `outline: none` and
                                               provides no replacement indicator.
     25  error  K focus-ring-shadow-only       `.shadowring:focus-visible` replaces the
                                               outline with `box-shadow` alone.
     53  error  K positive-tabindex            `tabindex="3"` on <a>.
     65  error  S heading-skip                 Heading level jumps h1 → h3 ("Findings").
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

  24 error(s), 5 warning(s) across 1 file(s).
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

---

## CI wiring

```yaml
# .github/workflows/a11y.yml
name: a11y
on: [pull_request]

jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Layer 1 — deterministic, one second, blocks the merge hard.
      - run: python -m scripts.a11y_static src/ --strict

      # Layer 2 — needs a browser and a served build.
      - run: npm ci && npm run build
      - run: npm install axe-core
      - run: npx playwright install --with-deps chromium
      - run: npx http-server dist -p 8080 &
      - run: |
          node scripts/a11y_runtime.mjs --url http://127.0.0.1:8080/ \
            --keymap a11y-keymap.json --budget a11y-budget.json --json \
            > a11y-report.json
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: a11y-report, path: a11y-report.json }
```

Three rules that keep it alive:

1. **Layer 1 blocks; layer 2 blocks; neither gets `continue-on-error: true`.** A job that cannot fail is a job that measures nothing. If layer 2 is flaky on your runner, narrow its checks with `--skip` until it is not, rather than disabling the whole thing.
2. **Keep the JSON artefact on every run, pass or fail.** It is the evidence trail a VPAT, an ACR or a procurement questionnaire needs, and reconstructing it six months later costs days. `references/manual-protocol.md` §7.
3. **Put the human pass on the release checklist, not on the PR.** It cannot run per-commit and it must not therefore run never. One template per sprint, rotating, plus every new pattern before it ships, is a rhythm teams actually keep.

---

## Routing

| Situation | Go to |
|---|---|
| Building or restyling the system itself | `web-design-studio` |
| **What WCAG 2.2 AA actually requires** | **`web-design-studio/references/accessibility.md`** |
| An inherited codebase not yet on tokens | `design-token-migration` |
| Every state × density × theme actually renders | `component-state-matrix` |
| The page is beautiful and slow | `perf-budget-gate` |
| Adversarial review before a client sees it | `design-critique-gate` |
| **Making the accessibility floor enforceable** | **here** |

Within this skill:

| You want | Read |
|---|---|
| the token vocabulary | `references/token-contract.md` |
| which criteria a machine can check, and why the rest cannot | `references/automation-coverage.md` §§1–3 |
| the false negatives that make a clean axe run misleading | `references/automation-coverage.md` §4 |
| the false positives that make teams disable rules | `references/automation-coverage.md` §5 |
| the coverage figure and its sources | `references/automation-coverage.md` §6 |
| **how to word an accessibility claim in a client report** | `references/automation-coverage.md` §7 |
| computing accessible names and roles for real | `references/runtime-checks.md` §2 |
| tab order: trap, skip, jump | `references/runtime-checks.md` §3 |
| measuring focus visibility in pixels | `references/runtime-checks.md` §4 |
| forced-colors, and what predictably breaks in a token system | `references/runtime-checks.md` §5 |
| contrast with overlays composited | `references/runtime-checks.md` §7 |
| automating the 12-pattern key map | `references/runtime-checks.md` §8 |
| zoom and reflow | `references/runtime-checks.md` §9 |
| what a browser still cannot tell you | `references/runtime-checks.md` §10 |
| the keyboard-only walkthrough | `references/manual-protocol.md` §2 |
| the screen-reader smoke test and its five tasks | `references/manual-protocol.md` §3 |
| zoom, images off, stylesheet off | `references/manual-protocol.md` §4 |
| the cognitive-load pass | `references/manual-protocol.md` §5 |
| writing a finding so it gets fixed | `references/manual-protocol.md` §6 |
| the evidence trail for a VPAT/ACR | `references/manual-protocol.md` §7 |
| testing with actual disabled users | `references/manual-protocol.md` §8 |

Deliberately **not** duplicated here: the WCAG 2.2 AA criterion table, the focus contract, the 12-pattern keyboard map, the alt-text decision tree, `aria-hidden` vs `inert`, and the forced-colors symptom table all live in `web-design-studio/references/accessibility.md`. Contrast arithmetic lives in `web-design-studio/references/color-system.md` §7. This skill references them and goes where they stop — into measurement, the gate, and the human procedure.

---

## The three sentences to remember

1. **Automated testing catches about a third** — and the correct response is to automate that third completely so every human hour goes to the other two, not to celebrate the badge.
2. **Measure the ring, do not read the stylesheet** — `:focus-visible` in CSS is not a focus indicator; 19.52% of pixels changing is, and 0.00% in forced-colors is its absence.
3. **A green gate is a floor, never a result** — the moment "we passed axe" becomes "we are accessible", the gate has done net harm, and it is the one failure mode of this skill that nothing in it can detect.

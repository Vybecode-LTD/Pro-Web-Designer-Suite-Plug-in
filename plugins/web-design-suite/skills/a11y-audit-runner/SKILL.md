---
name: a11y-audit-runner
description: Test a site against WCAG 2.2 AA with axe-core, keyboard, focus, contrast and zoom checks in CI, plus the manual pass. Use for accessibility audits and VPAT evidence. Not for design critique.
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

**Automated tools find well under half of the barriers, and decide few criteria outright.** Start here, say it out loud, and build everything else on top of it.

The number is not a rhetorical hedge. In the only controlled study with a known denominator — the UK Government Digital Service, 2017, a page with **143 deliberately planted failures across 19 categories**, run through ten automated tools — the best single tool found **37%** (Tenon, errors and warnings) to **41%** (Asqatasun, counting its manual-inspection prompts). All ten tools *combined* found 71%. **29% of the barriers were found by no tool at all.** ([GDS](https://accessibility.blog.gov.uk/2017/02/24/what-we-found-when-we-tested-tools-on-the-worlds-least-accessible-webpage/))

Deque's widely-quoted **57%** is a different measurement, and worth understanding rather than dismissing: it is the share of issues, counted **by volume**, that fully automated testing covered across 2,000+ audits and 13,000 first-assessment pages. It counts issues, not success criteria. ([Deque, 2021](https://www.deque.com/blog/automated-testing-study-identifies-57-percent-of-digital-accessibility-issues/)) Both numbers point the same way: the machine-detectable failures are the *most common* ones. By criterion the ceiling is lower still. A tool fully decides 7 of the 55 A and AA criteria in WCAG 2.2, decides part of 31 more, and leaves 17 that need a person (`references/automation-coverage.md` §3).

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
| Catches | 100% of its rules | 100% of its rules | **7 of the 55 criteria outright, and it says so** |

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
cp <web-design-studio>/assets/configs/pre-commit-design-gate.sh .git/hooks/commit-msg   # records bypasses
mkdir -p scripts
cp <web-design-studio>/scripts/audit_design.py scripts/        # Law 9
cp <a11y-audit-runner>/scripts/a11y_static.py scripts/         # the accessibility floor
```

The hook runs `a11y_static` on the staged files whenever `scripts/a11y_static.py` is present (set `DESIGN_GATE_A11Y_MODULE` if you keep it elsewhere). A hand-rolled `.githooks/pre-commit` with no shebang does not run at all under Git for Windows, and one without `set -e` passes whenever its LAST command passes.

Never put the runtime layer in a pre-commit hook. A minute of browser time per commit is how a team discovers `--no-verify`.

### 2. Add the runtime layer on a served build

```bash
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i -D -E playwright axe-core   # uses the Chrome you have
python -m http.server 8080 --directory dist &
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

## The scripts

`scripts/a11y_static.py` is layer one: stdlib Python, about a second, every commit. `scripts/a11y_runtime.mjs` is layer two: Node, Playwright and axe-core against a served build. Every flag and check, the key-map file, and what a failing run prints are in `references/scripts.md`.

---

## CI wiring

```yaml
# .github/workflows/a11y.yml
name: a11y
on: [pull_request]

defaults:
  run:
    shell: bash            # one script for Linux, macOS and Windows runners

jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with: { python-version: '3.12' }
      - uses: actions/setup-node@v5
        with: { node-version: 22, cache: npm }

      # Layer 1 — deterministic, one second, blocks the merge hard.
      - run: python -m scripts.a11y_static src/ --strict

      # Layer 2 — needs a browser and a served build. Everything it runs comes
      # from the lockfile (once: npm i -D -E playwright axe-core serve wait-on).
      - run: npm ci && npm run build
      - uses: actions/cache@v5
        with:
          path: ~/.cache/ms-playwright
          key: playwright-${{ runner.os }}-${{ hashFiles('package-lock.json') }}
      - run: npx playwright install --with-deps chromium   # the one Playwright was built for
      - name: serve, wait, audit
        run: |
          npx serve dist -l 8080 &
          npx wait-on http://127.0.0.1:8080 -t 30000
          node scripts/a11y_runtime.mjs --url http://127.0.0.1:8080/ \
            --keymap a11y-keymap.json --budget a11y-budget.json \
            --report a11y-report.json
      - uses: actions/upload-artifact@v6
        if: always()
        with: { name: a11y-report, path: a11y-report.json }
```

Two details in that file:
- **The browser comes from the lockfile.** `npx playwright install chromium` installs the Chromium that the locked Playwright was built for, and `a11y_runtime.mjs` tries it first. The runner image's own Chrome changes with each image release. The cache keeps the download to one per lockfile change.
- **The server starts, is waited for and is used in one step.** A process backgrounded in an earlier step may not outlive it on every runner. `--report` writes the JSON for the artifact and still prints the findings in the log.

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

Deliberately **not** duplicated here: the WCAG 2.2 AA criterion table, the focus contract, the 12-pattern keyboard map, the alt-text decision tree, and `aria-hidden` vs `inert` live in `web-design-studio/references/accessibility.md`, and the forced-colors symptom table in `accessibility-testing.md` beside it. Contrast arithmetic lives in `web-design-studio/references/color-system.md` §7. This skill references them and goes where they stop — into measurement, the gate, and the human procedure.

---

## The three sentences to remember

1. **Automated testing decides part of WCAG, never all of it** — and the correct response is to automate that part completely, so that every human hour goes to the rest, not to celebrate the badge.
2. **Measure the ring, do not read the stylesheet** — `:focus-visible` in CSS is not a focus indicator; 19.52% of pixels changing is, and 0.00% in forced-colors is its absence.
3. **A green gate is a floor, never a result** — the moment "we passed axe" becomes "we are accessible", the gate has done net harm, and it is the one failure mode of this skill that nothing in it can detect.

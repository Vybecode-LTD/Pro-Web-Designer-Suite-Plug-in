# web-design-suite 3.0.1 review: the three gates (GT)

Skills: **a11y-audit-runner, perf-budget-gate, component-state-matrix**. Reviewed 2026-09-23, read-only against `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`. Bugs fixed in 3.0.1 and the three "not bugs" are not re-reported here.
Every repro ran on copies in `$W` = `C:\Users\vybec\AppData\Local\Temp\claude\C--DEV\5b1a5cc7-460d-4e95-848e-f823553c2172\scratchpad\review\gates` (fixtures `e1`–`e20`), with `NODE_PATH=C:\DEV\audio-promptmonster\frontend\node_modules` (playwright 1.63.0, axe-core 4.13.0). The browser was the one the scripts picked automatically: Playwright's chromium-headless-shell 153.0.8010.12. Chrome 153.0.8010.53 gave the same result wherever I re-checked.

**Checked and correct, so not reported:** the CWV thresholds, p75, the 12 Mar 2024 INP date and the CLS session windows ([web.dev/vitals](https://web.dev/articles/vitals), updated 2024-10-31); the TTFB and TBT bands; the LCP sub-part targets; the GDS figures (143 failures, 19 categories, 10 tools, 37/41/71/29%) ([GDS](https://accessibility.blog.gov.uk/2017/02/24/what-we-found-when-we-tested-tools-on-the-worlds-least-accessible-webpage/)); all eight WebAIM Million 2026 figures ([WebAIM](https://webaim.org/projects/million/)); axe-core 4.13.0 as the current npm latest; the 320px value for 1.4.10 and the large-text thresholds; the cell arithmetic 1,260 → 108 (the generator's output matches the formula); and perf_audit's B/L/C rules on a fixture.

## A. Issues

**GT-A1 · high · `a11y_runtime.mjs:1162-1167` (`parse`, used at :1189, :1206, :1234, :1244)**: the runtime contrast check silently skips any colour that is not serialised as `rgb()`/`rgba()`. Chromium 153 serialises the suite's own OKLCH tokens as `oklch(…)` (computed `.button color=oklch(0.195 0.006 75)`). As a result, text and overlays in the colour space the token contract requires are never sampled, and the run reports no finding and no "unmeasurable" warning. Repro (run from `$W\a11y-audit-runner`): `node scripts/a11y_runtime.mjs --file ..\e10\overlay.html --skip taborder --skip focus --skip forced --skip keys --skip reflow --skip names`. With `.scrim{background:rgb(255 255 255/.72)}` it reports `error contrast-under-overlay … 1.53:1 … reads as 7.00:1` and exits 1. With `oklch(1 0 0/.72)` it reports only `warn color-contrast (incomplete)` and exits **0**. Text coloured `#aaa` is flagged at 2.32:1; `oklch(0.75 0 0)` is not flagged. On a proof sheet built from the starter `tokens.css`, `CONTRAST_FN` returned 0 samples. So the headline "5.33:1 → 1.46:1" feature (SKILL.md:178, :200; runtime-checks.md §7) does nothing on any site built with this suite. *Fix:* resolve each colour through a 1×1 canvas (set `fillStyle`, read back with `getImageData`), and add an OKLCH fixture test.

**GT-A2 · high · `a11y_runtime.mjs:426-450, 741-786, 580-634, 499-507`**: the runtime reports false Level-A errors on two page shapes that are everyday.
- *A modal dialog.* A correct `<dialog>` opened with `showModal()` (for example a cookie banner, and exactly what the tool's own trap fix text recommends) produces `keyboard-trap` (2.1.2), `unreachable-control` ×4, and `no-accessible-name` ×4 on links that are named "Home", "Pricing" and so on. Exit 1 (`$W\e11\modal.html`). The cause: the list of expected tab stops ignores the inertness a modal gives the rest of the page, and the names check ignores inert and hidden subtrees.
- *A same-origin iframe.* `activeElement` stays `<iframe>` while focus moves inside it, so the run raises `error focus-stuck` (2.1.2). axe is injected into the main frame only, so the iframe's unlabelled input, empty button and missing alt text show up only as `frame-tested (incomplete)` (`$W\e20`). runtime-checks.md:132 says the tool shows "whether it comes back"; it reports a trap instead.

*Fix:* leave elements that are inert because of `:modal`, or inert or aria-hidden subtrees, out of both the expected tab stops and the names check. Accept a tab cycle that stays inside an open modal. Inject axe into every same-origin frame (`page.frames()`). Add `--dismiss SEL`.

**GT-A3 · high · `snapshot_matrix.mjs:314, 327-340`; `visual-regression.md:121`**: the visual gate is blind to the regressions the matrix exists to catch. The default per-pixel tolerance of 0.10 (YIQ Δ ≤ 352) is larger than the suite's own state overlays: `--bg-hover` at 4% gives Δ≈50 and `--bg-active` at 8% gives Δ≈200 on white. Repro (`$W\e9`, a 32-cell sheet built from starter tokens, baselines recorded first):

| Change to the CSS | Result |
|---|---|
| Delete `.button:hover` | `pass 32`, exit 0 |
| Delete `:active` | `pass 32`, exit 0 |
| `--border-default` → `--border-subtle` | `pass 32`, exit 0 |
| Radius md → sm | Only the 2 focus-visible cells fail; the other 22 button cells pass |

The doc says: "It will catch … a radius change, a border colour change, and any fill change." *Fix:* add a check within the run that each hover, active and focus cell differs from its default cell (no baseline needed). Lower the default tolerance and measure how much antialiasing margin remains. Correct the claim.

**GT-A4 · high · `a11y-audit-runner/SKILL.md:71-79` (+ `a11y_static.py:1500-1501`)**: the pre-commit snippet ("one hook, three checks", which shows two) has four faults. Repro repo: `$W\e2repo`.
1. It has no shebang, so Git for Windows cannot run it and every commit fails: `error: cannot spawn .githooks/pre-commit: No such file or directory`.
2. With `#!/bin/sh` added, there is no `set -e`, so the hook's exit code is a11y_static's. A staged `.card{margin:24px;color:#ff0000}` gets 2 audit_design errors, a11y_static reports clean, and `[main a8dbdd9] add card` commits with exit 0. Law 9 is bypassed.
3. `$CHANGED` passes every staged file, and a11y_static audits any path it is given explicitly, whatever the extension. README.md, render.py and notes.txt produce 6 errors and exit 1 (`$W\e1`).
4. The paths are unquoted, so file names with spaces break. The shipped `pre-commit-design-gate.sh` already handles all four.

*Fix:* add opt-in a11y and perf stages to the shipped hook and delete the inline snippets (the same pattern is at ci-integration.md:26-42). Make a11y_static filter explicit arguments by extension.

**GT-A5 · medium · `a11y_runtime.mjs:1858-1882`**: no `bypassCSP`. A page served with `Content-Security-Policy: default-src 'self'` crashes at the animation-freeze `addStyleTag`, prints a stack trace and exits **1**. The docs reserve 2 for "page failed to load"; 1 means violations (`$W\e16\csp_server.py`). *Fix:* set `bypassCSP: true` on every context in all three runtime scripts, and map setup failures to exit 2.

**GT-A6 · medium · `measure_vitals.mjs:79-88, 397, 424-444`; `budgets.md:26-33`; `diagnosis.md:24`**: the throttle presets are not Lighthouse's, and TTFB is never throttled. The code comment says "Lighthouse's mobile defaults, in the units CDP wants". CDP throttling works per request, though, and Lighthouse's DevTools equivalent of 150 ms RTT is 150 × 3.75 = 562.5 ms of latency at 1.6 × 0.9 Mbps ([LH constants](https://github.com/GoogleChrome/lighthouse/blob/8f500e00243e07ef0a80b39334bedcc8ddc8d3d0/lighthouse-core/config/constants.js)). DevTools' own Slow 4G is 562 ms at 1.4 Mbps and Fast 4G is 165 ms at 9 Mbps ([DebugBear](https://www.debugbear.com/blog/chrome-devtools-network-throttling)).

Measured (`$W\navtiming.mjs`):

| CDP latency | Navigation `responseStart` | `loadEventEnd` |
|---|---|---|
| 0 ms | 7 ms | 23 ms |
| 150 ms | 4 ms | 182 ms |
| 562.5 ms | 5 ms | 604 ms |

So `--throttle slow4g` reports a median TTFB of 5 ms, against 800 ms in the doc's own derivation. `ttfb_ms` never sees the emulated latency. That latency lands instead in "resource load delay" or "element render delay", the two phases the report marks "← the bug". *Fix:* document that the throttling is per request. Add a `lighthouse` preset (562.5 ms, 1.44 Mbps). Take TTFB from the CDP `Network.responseReceived` timing, or drop it while emulating.

**GT-A7 · medium · SKILL.md:10-12, :120; automation-coverage.md:103, :240, :243-245, :273; a11y_runtime.mjs:17-19**: the coverage sources are misstated.
- (a) Deque's 57% is "57 percent of accessibility issues were completely covered by this automated testing" ([Deque, 10 Mar 2021](https://www.deque.com/blog/automated-testing-study-identifies-57-percent-of-digital-accessibility-issues/)). It does not come from "a suite that includes Intelligent Guided Testing … a human answering questions".
- (b) GDS counted planted *barriers* found, not "criteria a tool can evaluate". It therefore cannot support the recommended report sentence "covers an estimated one third of WCAG success criteria".
- (c) The table's own count is 45 rows: Full 7 (16%), Partial 26 (58%), None 12 (27%). It is not "roughly a third Full, a bit under half Partial".
- (d) The table omits 7 of the 55 A/AA criteria in WCAG 2.2: 1.2.1–1.2.5, 1.4.2 and 2.5.4.

*Fix:* describe each study by what it measured, recount the table, and add the missing rows.

**GT-A8 · medium · SKILL.md:168, :185; automation-coverage.md:180; a11y_runtime.mjs:105**: the axe tag advice is wrong in both directions.
- The recommended gate set `wcag2a,wcag2aa,wcag22aa` drops every WCAG 2.1 rule. In axe 4.13, `wcag21a` covers label-content-name-mismatch and `wcag21aa` covers autocomplete-valid (1.3.5), avoid-inline-spacing (1.4.12) and css-orientation-lock (1.3.4).
- The default set includes `best-practice`, so best-practice rules with serious impact (`tabindex`, `aria-dialog-name`, `label-title-only`, `accesskeys`) fail the gate. Meanwhile the recommended report wording says "WCAG 2.2 A/AA rule set".

*Fix:* gate on `wcag2a,wcag2aa,wcag21a,wcag21aa,wcag22aa` and report best-practice results as warnings.

**GT-A9 · medium · automation-coverage.md:278-279; manual-protocol.md:255**: the docs recommend "Not Evaluated" as a legitimate ACR entry. The VPAT 2.5 terms say "Not Evaluated … can only be used in WCAG Level AAA criteria" ([rules](https://accessible.org/rules-filling-out-vpat/)). For A and AA criteria it would get a report rejected.

**GT-A10 · medium**: the docs promise runtime behaviour that the code does not have.
- automation-coverage.md:205 says incompletes fail "under `--strict`". The runtime has no such flag: `unknown option --strict`, exit 2.
- SKILL.md:179 and runtime-checks.md:314-318 say `keys` drives "Enter/Space/Arrow/Home/End/Escape/Tab". The code (:1388-1530) presses only Enter, ArrowDown, Escape and ArrowRight. It never tests Space, Home/End, Tab closing a menu, arrow wrap, Esc on a combobox, or Tab staying inside a dialog.
- runtime-checks.md:3 says "Every technique here is implemented", but §6 (reduced motion) is not. :253 says to audit with reduced motion on; the code sets `reducedMotion:'no-preference'` (:1866).
- runtime-checks.md:338 and automation-coverage.md:65 say the 200% check looks for "clipped and overlapping content". The code only checks for horizontal scroll (:1553-1595) and files it as a 1.4.4 error, although horizontal scrolling does not fail 1.4.4.
- `--budget a11y-budget.json` (SKILL.md:88, :306) has its 13 keys only in code (:1606). A plausible `{"violations":0}` gets `unknown budget key "violations"`, exit 2.

**GT-A11 · medium · perf SKILL.md:88; budgets.md:199-219; ci-integration.md:149**: the docs say to put the device and network "in a comment" in `perf-budget.json`, and the examples are JSONC. Both parsers accept strict JSON only. perf_audit fails with `cannot read budget … Expecting property name enclosed in double quotes: line 2 column 3`, exit 2. measure_vitals does all N runs first, then fails with `cannot parse …`, exit 2 (the budget is read at :779). *Fix:* strip comments or use a `"profile"` string field, and parse the budget before measuring.

**GT-A12 · medium · `generate_matrix.py:84-89, :120-124, :447`**: rules written with `:focus` or `:focus-within` are mirrored to `[data-force-state~="focus"]`. Focus-visible cells carry `data-force-state="focus-visible"`, which that selector never matches, yet the coverage check counts `:focus` as covered. Repro (`$W\e9`, the chip component uses `.chip:focus{outline:…}`): the generator prints "every declared state has a matching rule"; the focus row renders exactly like the default row; `a11y_runtime --matrix` reports `no-visible-focus-indicator` on both chip focus cells and exits 1. That is a false positive for a ring that real users do see. *Fix:* emit `data-force-state="focus-visible focus"` and put focus-within on the stage.

**GT-A13 · medium · `generate_matrix.py:474, :110`; state-coverage.md:148, :173, :283-293, :328-333**: only the seven fixed states are allowed. Adding `"selected"` fails with exit 2, `unknown state(s) ['selected']`. That means:
- the §6 procedure ("add it to `states` … confirm it is flagged `no rule`") cannot be followed;
- the §4 rows (selected, readonly, indeterminate, aria-current, the open state) cannot be rendered;
- the §1.8 "selected + hover" combination cannot be rendered.

Separately, the error state stamps `aria-invalid="true"` on every template, buttons and links included. That contradicts :148, and ARIA 1.2 deprecated `aria-invalid` (and `aria-disabled`) as global attributes ([ARIA 1.2](https://www.w3.org/TR/wai-aria-1.2/)). *Fix:* allow custom states declared as `{attrs, detect}`, and use `data-state="error"` on templates that are not form controls.

**GT-A14 · medium · `a11y_runtime.mjs:1880-1882, :1275-1313`**: two measurements give false results (fixture `$W\e11\probes.html`).
- (a) The freeze CSS sets `animation-duration:1ms` without pausing, so an infinite spinner keeps moving. A button with `outline:none` plus a spinner measured 2.67% of pixels changed at 11.88:1, which counts as "has a ring". The same button without the spinner correctly gets `no-visible-focus-indicator`. Loading-state cells have exactly this shape. runtime-checks.md:36 calls this "the same trick snapshot_matrix.mjs uses", but snapshot_matrix pauses animations.
- (b) Disabled controls are not exempted. `<button disabled>` "Unavailable" gets `contrast-too-low` at 2.43:1 as an error; axe correctly says nothing, because SC 1.4.3 exempts inactive components.

**GT-A15 · medium**: none of the CI recipes (a11y SKILL.md:285-311; ci-integration.md:53-110; visual-regression.md:191-237) runs as written in every case.
- *a11y:* `npx http-server dist -p 8080 &` does not wait for the server (the perf recipe uses `wait-on`), so the first request can fail. The workflow never adds `playwright` to the project, so the script exits 2 with "cannot load the playwright module". Its `npx playwright install` also contradicts the other two recipes' "never download one here".
- *All three:* they use the runner image's own Chrome, which is Chrome 152 on ubuntu-24.04 and changes with each image release ([image readme](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md)). Meanwhile ci-integration.md:129 and visual-regression.md:53 both say to pin the browser.
- *perf:* the line `--runs 0 --quiet || true` always fails (`--runs must be at least 1`, exit 2) and is swallowed. When the budget is breached, the step prints nothing a person can read. The PR-comment snippet uses an undefined `$PR` and needs `GH_TOKEN` plus `pull-requests: write`.
- *On Windows runners,* where the default shell is pwsh, `\` line continuations, `|| STATIC=$?`, `exit ${STATIC:-0}` and `cmd &` are all bash-only. The fix is `shell: bash` plus a detached server started with `Start-Process`.
- The `@v4`/`@v5` actions target Node 20, which GitHub drops from runners on 2026-09-23 ([changelog](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/)).

**GT-A16 · low-medium · budgets.md:58, :83-84; perf SKILL.md:32**: two rows of the "same method" table cannot be reproduced with that method (TTFB = 4·RTT + 200 ms, minus 300 + 150 ms).
- Fast 4G (9 Mbps, 40 ms RTT): 1,690 ms × 1.125 MB/s ≈ **1.9 MB**. The doc says 1.5 MB, and its 3 MB total is ×2.0 of that, not the stated ×2.4.
- 3G (400 Kbps, 400 ms RTT): 250 ms × 50 KB/s ≈ **12.5 KB**. The doc says 40 KB.

The doc also says the 800 ms TTFB match "is not a coincidence; the thresholds were derived the same way". It isn't; web.dev calls 0.8 s "a rough guide" chosen so that FCP can be good ([web.dev/ttfb](https://web.dev/articles/ttfb)).

**GT-A17 · low-medium · `measure_vitals.mjs:406-408, :513-522`**: `--interact` adds the interaction's own handler to TBT. On `e18/slow.html` TBT goes from 0 to 107 ms with INP at 168 ms, so the same work is counted twice. The TBT window also has no TTI bound. *Fix:* read TBT before the click.

**GT-A18 · low-medium · `a11y_static.py:1152-1159, :1199-1219`**: `multiple-h1`, `heading-skip` and `no-main-landmark` are hard errors attributed to SCs 1.3.1, 2.4.6 and 2.4.1. axe 4.13 tags `page-has-heading-one`, `heading-order` and `landmark-one-main` as best-practice only. That weakens the "1.3.5, and here is the fix" argument the skill relies on (SKILL.md:138). *Fix:* make them warnings labelled "best practice".

**GT-A19 · low**: smaller errors in the docs.
- perf SKILL.md:19 says `transition: width` is "a design violation". On `.drawer{transition:width var(--dur-base) var(--ease-out)}`, audit_design reports no transition finding (it flags only `transition: all`, and only as a warning); perf_audit reports a `C animated-layout-prop` warning. ci-integration.md:230 has it right.
- budgets.md:186 says "the runtime gate measures … main-thread time by origin". measure_vitals has no per-origin grouping, and its `--json` holds only the top `--resources` entries (10 by default).
- ci-integration.md:115 and visual-regression.md:242 say `npm ci` "pulls ~150 MB". playwright 1.63 has no install script, so it doesn't.
- matrix SKILL.md:178 gives 24px and then "the unchanged 16px".
- state-coverage.md:312 calls a class-swapped state a "Law-8 problem"; Law 8 is about the keyboard.
- state-coverage.md:79 attributes the 2px thickness to 1.4.11; thickness comes from 2.4.13. runtime-checks.md:177 cites 2.4.13 without saying it is Level AAA ([W3C](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html)).
- token-contract.md:109 files large-text 3:1 under 1.4.11; that requirement is 1.4.3.
- automation-coverage.md:9-17 numbers the table of contents 6–8 against headings numbered 5.5, 6 and 7.
- manual-protocol.md:82 says NVDA + Firefox is "closest to what a large share of users run". WebAIM's survey #10 has NVDA + Chrome at 21.3% and NVDA + Firefox at 10.0% ([WebAIM](https://webaim.org/projects/screenreadersurvey10/)). The example "Firefox 142" at :95 and :259 is a 2025 version inside a 2026-09 example.
- The generated sheet itself fails 1.4.3: `.msheet__mark--ok` sets `--fg-on-inverse` on `--bg-success` at 3.23:1, 12px (`generate_matrix.py:1206`, found by axe in the `--matrix` run).

## B. Gaps
- **GT-B1 · SPA and dynamic states.** Each runtime script does a single `goto(…,'load')`, with no wait-for option, no network-idle wait and no scripted steps. Client-rendered pages get audited as empty shells, and route-change focus, title and announcements go untested. *Scope:* shared `--wait-for SEL` and `--steps steps.json` (click, fill, goto).
- **GT-B2 · Authenticated pages.** There is no storage-state, cookie or header option. Yet diagnosis.md:22 says to measure the page "logged in, with the banner, with the variant". *Scope:* `--storage-state` and `--header`.
- **GT-B3 · Shadow DOM.** The names, contrast, tab-stop and focus code uses `querySelectorAll`, which does not reach inside shadow roots. Web-component libraries get axe coverage only. *Scope:* a helper that queries through shadow roots.
- **GT-B4 · Multiple URLs and viewports.** Each run covers one URL, and a11y runs only at 1280×900. The report template assumes "all 14 templates". Target size (2.5.8) and mobile navigation need a phone-width viewport. *Scope:* `--urls FILE` or a sitemap, a list of viewports, and a map from URL to perf page type.
- **GT-B5 · The field-data loop.** Checking "field p75 > 1.5× lab median" (perf SKILL.md:127) has no tool behind it. *Scope:* `crux_check.py` (CrUX API key from an environment variable), or a reader for a web-vitals RUM export.
- **GT-B6 · Checks the coverage table lists as automatable but that don't exist.** Text-spacing injection for 1.4.12, sticky-header overlap of focus for 2.4.11, 1.4.13, a reduced-motion A/B, and clipping at 200%. Each is small, and they are the cheapest real coverage additions.
- **GT-B7 · The matrix model.** Custom states and state combinations (A13); RTL (state-coverage.md:220 lists RTL, but fixtures are inner HTML only, so there is no way to set `dir`); a forced-colors snapshot pass; states that need interaction (an open select, a tooltip). *Scope:* `custom_states`, a per-fixture `dir`, `--forced-colors`.
- **GT-B8 · The baseline lifecycle.** Step 4 records baselines locally, which means Windows fonts against Linux CI fonts, and there is no recipe for recording them in the CI container. The pruned sheet gives 108 cells per component, so 19 components already pass the 2,000-baseline limit at visual-regression.md:181-183. *Scope:* a `workflow_dispatch` job that updates baselines, and Git LFS by default above a set component count.
- **GT-B9 · Chromium only.** focus-visible heuristics, forced-colors behaviour and rendering all differ in Firefox and WebKit. *Scope:* an `--engine` option for axe, names and tab order.

## C. Improvements
- **C1 · M · P0.** A test suite that uses a real browser, skipped when none is available, turning the repros for A1, A2, A3, A12, A14 and A17 into regression tests. Today's browser tests use a stub and only check browser resolution, so measurement bugs like these cannot show up.
- **C2 · S–M · P0.** Fix colour parsing, handling of modals, iframes and inert content, `bypassCSP`, animation pausing, and the disabled-control exemption (A1, A2, A5, A14).
- **C3 · M · P0.** Matrix: the within-run "differs from default" gate, a tolerance tuned to the suite's own tokens, focus mirroring, custom states, and `data-state="error"` on templates that aren't form controls.
- **C4 · S · P0.** One shipped hook with opt-in stages in place of the inline snippets (A4).
- **C5 · S · P0.** A correction pass on the docs (A7–A10, A16, A19). The skill's value is honesty about coverage, so its own numbers have to hold.
- **C6 · S · P1.** Write SKILL.md commands with `${CLAUDE_SKILL_DIR}`, for example `python "${CLAUDE_SKILL_DIR}/scripts/a11y_static.py" src/`, and pre-approve them with `allowed-tools: Bash(node ${CLAUDE_SKILL_DIR}/scripts/*)`. Today `python -m scripts.x src/` works only if `scripts/` has been copied into the project.
- **C7 · S · P1.** SKILL.md size. a11y is about 7.0k tokens, perf about 5.7k and matrix about 5.2k. The recommendation is 5k or less, and only the first 5k survive compaction. Move the "failing run" samples, the CI YAML and the rationale tables into references, and aim for 2.5k or less.
- **C8 · S · P1.** Descriptions. They run to 861–927 characters and go name-only in a crowded skill listing, so the first sentence should work on its own and add a "not for…" line.
  - a11y: good coverage of the terms people use. It can fire on "add alt text" or "add ARIA" build tasks that belong to web-design-studio.
  - perf: fine.
  - matrix: collides with design-system-docs, which also claims "Storybook alternative", "component gallery" and "component library nobody has…". Keep the matrix to state proof and visual regression.
- **C9 · M · P1.** Plugin components:
  - (a) `agents/gate-runner.md` (tools Bash and Read), which runs the runtime scripts and returns only the findings and the JSON path, so 5–10k tokens of script output stay out of the main context;
  - (b) an opt-in PostToolUse hook (`Edit|Write`, `if` restricted to css/html/jsx/tsx) that runs a11y_static on the edited file and returns the findings as `additionalContext`;
  - (c) user-invoked `gate-a11y`, `gate-perf` and `gate-matrix` skills with `disable-model-invocation: true`, so they add no cost to the skill listing.
- **C10 · M · P1.** A `claude plugin eval` suite, run under WSL2 because the cases need Bash.
  - Routing cases that name the expected skill, e.g. "screenshot-diff every button state" → matrix and "document our components" → docs.
  - Outcome cases:
    - axe passes but compliance is not claimed, and "Not Evaluated" is not suggested for AA;
    - a budget derivation that names a device and a network and produces JSON with no comments;
    - a CI recipe that includes `wait-on` and a pinned browser.
  - Compare each case with and without the plugin.
- **C11 · M · P2.** Add a `lighthouse` throttle preset and take TTFB from CDP. Add `--interact-at MS` to click during hydration: diagnosis.md §8 names hydration as the biggest INP source, but `--interact` only clicks after the settle time. Add `crux_check.py`.
- **C12 · M · P1.** One CI template for all three gates, run in a pinned Playwright container, with `wait-on`, uploaded artifacts, a job to update baselines, and a tested Windows variant.
- **C13 · S · P2.** Vendor the shared runtime helpers (browser resolution, freeze CSS, JSON reading) into each skill as identical copies, the way token-contract.md is, with a test that the copies match. The freeze CSS already differs between a11y_runtime and snapshot_matrix.

## Reviewed
- **Read in full:** SKILL.md and every reference file for all three skills (incl. token-contract.md); README.md; the bug-fix report; `a11y_runtime.mjs`, `measure_vitals.mjs`, `snapshot_matrix.mjs`.
- **Read in part (the logic behind each documented claim):** `a11y_static.py`, `perf_audit.py`, `generate_matrix.py`; the audit_design transition rule; `pre-commit-design-gate.sh`; the list of tests.
- **Commands run (all in `$W`):**
  - a11y_static on .md, .py and .txt files;
  - a git repo with the SKILL.md hook, verbatim and with a shebang;
  - perf_audit and measure_vitals with a commented budget, and `--runs 0`;
  - a CDP navigation-timing probe in the headless shell and in Chrome;
  - measure_vitals `slow4g` vs `off`, and with and without `--interact`;
  - generate_matrix, snapshot baselines, and 7 CSS mutations;
  - a11y_runtime on OKLCH, overlay, modal, iframe, spinner, disabled and CSP fixtures, with `--strict`, with a guessed budget, and with `--matrix`;
  - axe tag and impact dump; coverage-table count; audit_design and perf_audit on `transition: width`.
- **Sources:** as linked above, plus the [GitHub runner image readme](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md) (python-is-python3 is present, so `python` works in the Linux recipes).
- **Not verified:** behaviour on real GitHub Windows runners (reasoned from the pwsh default); macOS; a direct comparison with Lighthouse.
- **Not done:** the `dev plans` README entry for this review folder. I left it for the coordinator so the parallel reviewers don't edit it at the same time.

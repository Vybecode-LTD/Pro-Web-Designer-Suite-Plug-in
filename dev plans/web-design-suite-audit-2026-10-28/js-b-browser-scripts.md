# JS-B: the five Playwright browser scripts

Audited 2026-10-28 at main 8441ff0. Files read in full: `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_runtime.mjs` (3,459), `skills/perf-budget-gate/scripts/measure_vitals.mjs` (1,113), `skills/component-state-matrix/scripts/snapshot_matrix.mjs` (586), `skills/design-critique-gate/scripts/critique_snapshots.mjs` (419), `skills/email-template-system/scripts/render_email.mjs` (152), `skills/a11y-audit-runner/scripts/browser_common.mjs` (the contract: `arrive`, `launchEngine`, `keepClosedRoots`, `DEEP_DOM`, `readUrls`, `runEach`), the five SKILL.md files, `a11y-audit-runner/references/runtime-checks.md` and `references/scripts.md`, `perf-budget-gate/references/budgets.md` and `ci-integration.md` §4, `component-state-matrix/references/visual-regression.md`. Tests consulted: `tests/test_browser_scripts.py` (VitalsTiming), `test_browser_runtime.py` (the iframe case at :372, VitalsUnderCsp, VitalsMeasures), `test_runtime_urls.py`, `test_runtime_engines.py`, `test_runtime_wcag_checks.py` (names only), `docs/HANDOFF.md` (the flakes). Commands run (all under `scratchpad/js-b/`, Playwright 1.63.0 with its Chromium 1243, axe-core 4.13.0, headless, each under two minutes): a `frame.evaluate` probe on a sandboxed, a plain and a lazy iframe; `a11y_runtime.mjs --file` on `frame-focusable.html` (taborder only), `opacity.html` (contrast only), `icon-name.html` (names only), `--matrix sheet.html`; `a11y_runtime.mjs --url` against a local HTTP server whose font request never completes, in two variants, each spawned with a kill at 50 and 62 s; a `document.fonts.ready` and `requestAnimationFrame` probe on that server; a `page.screenshot` timing probe on it; the matrix comparator on a 1, 2 and 3 px shift; `node -e` writing 2 MB to a pipe before `process.exit`; `time npm root -g`.

## Summary

24 findings: 5 high, 8 medium, 11 low. By class (counted from the headings): bug 15, gap 4, inconsistency 3, dead-code 1, risk 1. The 390 px hang is reproduced: `a11y_runtime.mjs:3024` awaits `document.fonts.ready` with no bound, and a page whose font request is outstanding at that moment and never completes prints `browser:` and nothing else, forever (JS-B-1); the same unbounded await is in `critique_snapshots.mjs:334` and `snapshot_matrix.mjs:429`, and on the same page the focus check spends 30 s per screenshot, swallows each error, and then reports no focus findings at all (JS-B-2). Three checks give wrong answers on realistic pages, each confirmed by a run: a same-origin iframe with a focusable child is an `unreachable-control` error (JS-B-3), text inside an ancestor at `opacity: 0.3` passes contrast (JS-B-4), and `aria-hidden` icon text or an sr-only span makes `label-not-in-name` a false error (JS-B-5). Three suspicions were tested and dropped, so the next reader need not: a sandboxed `srcdoc` iframe does not stall `frame.evaluate` on this Chromium, the matrix comparator does catch a 1 px shift (2.0 % of pixels), and `--json` through a pipe is not truncated by `process.exit()` on Windows.

## Findings

### JS-B-1 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_runtime.mjs:3024` (and `skills/design-critique-gate/scripts/critique_snapshots.mjs:334`, `skills/component-state-matrix/scripts/snapshot_matrix.mjs:429`)
- **What:** `await document.fonts.ready` inside `page.evaluate`, which has no timeout. The promise never settles while a `@font-face` request is outstanding and never completes, so the run never reaches the first check.
- **Evidence:** `if (document.fonts && document.fonts.ready) await document.fonts.ready;`. Reproduced: a local HTTP page whose `load` handler first uses a font served by a route that accepts the request and never answers; `a11y_runtime.mjs --url` printed `browser: Playwright's own Chromium` and nothing more, still running when killed at 50 s. The same page's `load` fired normally (a font requested *before* load keeps `load` from firing, and `goto` then dies at 45 s with "could not load", which is the bounded case). The `fonts.ready` probe on its own: `TIMEOUT after 15s: document.fonts.ready never resolved`, `document.fonts.status` = `loading`. `requestAnimationFrame` fired in 29 ms on the same page, so the rAF waits are not the stall.
- **Effect:** Exactly the owner's symptom on webawesome.com at 390 px: the `browser:` line, then a hang with every check unrun. Any page that starts a font load in a `load` handler, a late-upgrading component with an icon font, or a CDN that stalls, hangs every run; nothing names the cause.
- **Fix:** Bound the wait: `Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 5000))])` in all three scripts, and log a warning finding (`fonts-still-loading`) when it lost the race, since geometry is then measured against the fallback face. Regression test: a served page with a never-answered font route must finish in under 15 s with that warning.
- **Confidence:** confirmed

### JS-B-2 · high · bug

- **Where:** `a11y_runtime.mjs:1180`, `:1195` (the two `page.screenshot({ clip })` in `measureFocus`), `:1212` (the error is kept on the entry), `:1279` (`focusFindings` skips `!m.ok`)
- **What:** Playwright's `page.screenshot` waits for `document.fonts` and times out at 30 s per shot. On a page with a stalled font every stop costs 60 s (120 s with `forced`, more per density), each error is written to `entry.error` and dropped, and the check ends with no finding and no warning.
- **Evidence:** Reproduced with the font requested 50 ms *after* load (so JS-B-1's await had already resolved): the run got through `axe…`, `accessible names…`, `tab order…`, then `focus indicator on 2 element(s)…` and was still there at 62 s. Direct probe on the same page: `page.screenshot({clip})` threw `Timeout 30000ms exceeded` at 30,016 ms, and with `timeout: 5000` at 5,014 ms. By reading, `focusFindings` has `if (!m.ok) continue;` and nothing in `main()` counts the errors; `focusTable` rows show `n/a`.
- **Effect:** A 40-stop page takes 40 minutes and then passes the focus and forced-colours checks silently: the one failure mode the skill says it must never have ("a check that silently did not run … appears in the report as a green row", runtime-checks.md §5).
- **Fix:** Pass `timeout: 5000` to both screenshots; when any measurement has `error`, emit one `focus-not-measured` warning naming the count and the first error, and count it in a budget key. Regression test: the stalled-font page must produce that warning in under 30 s.
- **Confidence:** confirmed

### JS-B-3 · high · bug

- **Where:** `a11y_runtime.mjs:538` (`describeActive` follows focus into a same-origin frame and reports `iframe-path >>> inner-path`), `:395` (`FOCUSABLE` lists `iframe`), `:966` (`skipped = expected.filter((e) => !reached.has(e.sel))`)
- **What:** The expected list holds the `<iframe>` by its own path; the tab sequence never records that path when the frame has a focusable child, because the stop is reported as the inner element. The iframe is then an `unreachable-control` error.
- **Evidence:** Run on `frame-focusable.html` (a link, a `srcdoc` iframe holding one button, a button): `tabOrder` = `… > a`, `… > iframe >>> html > body > button`, `… > button`, repeating; finding: `error unreachable-control | 1 focusable element(s) were never reached by Tab: html > body > main > iframe.` Exit 1. The suite's own case for this shape (`tests/test_browser_runtime.py:372`, a payment form in a `srcdoc` frame) asserts only that `focus-stuck` is absent, so the false error has passed CI since GT-A2.
- **Effect:** Every page with an embedded same-origin form, demo or player fails 2.1.1 with a wrong message, and the user is told to "fix the trap first".
- **Fix:** In `analyseTabOrder` (or when building `reached`), count an iframe as reached when any stop's selector starts with `cssPath(iframe) + ' >>> '`; or have `describeActive` push the frame's own path as well. Regression test: the existing :372 case must also assert `unreachable-control` absent.
- **Confidence:** confirmed

### JS-B-4 · high · bug

- **Where:** `a11y_runtime.mjs:1541–1556` (CONTRAST_FN's ancestor walk reads only `backgroundImage` and `backgroundColor`), against `:1616` (overlays do multiply in each ancestor's `opacity`) and `critique_snapshots.mjs:199` (its `SAMPLE_TEXT` fades text and background by ancestor opacity, "Codex on #71: a faded text passed")
- **What:** An element's `opacity` thins its text and its own background alike before they meet what is behind it, and the a11y contrast check never reads it, so faded text is measured at its declared colour.
- **Evidence:** Run on `opacity.html` (`<div style="opacity:0.3"><p style="color:#333">…` on white; the rendered pair is about 1.7:1): `findings: 0`, exit 0. The same page's `critique_snapshots.mjs` path would report it below the floor. The #71 fix reached one script and not the other.
- **Effect:** The most common "muted" and "disabled-looking" pattern (a faded section, a skeleton, a secondary row at 60 %) passes 1.4.3 in the gate that the suite says measures what the eye receives. Silently wrong, on the suite's own starter patterns.
- **Fix:** In the walk, accumulate `a *= opacity` for each ancestor from the text up to the opaque background, apply it to `fg` and to the composited `bg` as `critique_snapshots.mjs` does (its `fade`), then composite over what is behind. Regression test: `opacity.html` must yield `contrast-too-low`; a control at opacity 1 must not.
- **Confidence:** confirmed

### JS-B-5 · high · bug

- **Where:** `a11y_runtime.mjs:789` (`visibleText: (el.textContent || '')…`), `:849–853` (the 2.5.3 rule)
- **What:** "Visible text" is `textContent`, which includes `aria-hidden` descendants, visually hidden spans and icon-font ligatures, none of which a sighted voice-control user sees. The spec says the check compares the name with the text the user *can see* (runtime-checks.md:69, scripts.md:54).
- **Evidence:** Run on `icon-name.html`: `error label-not-in-name | Visible text "menu" is not contained in the accessible name "Open navigation".` (a Material-Icons ligature inside `aria-hidden="true"`), and `error label-not-in-name | Visible text "Close dialog" is not contained in the accessible name "Close".` (an sr-only span). Exit 1. Both are correct markup.
- **Effect:** Every icon-font button with an `aria-label` fails 2.5.3 as an error, which is the exact noise the file's own comment at :774 warns gets a check switched off.
- **Fix:** Build the visible text from rendered text nodes only: skip subtrees with `aria-hidden="true"`, `display: none`, `visibility: hidden` or a clip-rect/1 px box, and use `innerText` rather than `textContent` (an icon-font ligature cannot be told apart by the DOM, so document that limit). Regression test: `icon-name.html` yields no 2.5.3 finding; `<button aria-label="Submit">Send</button>` still does.
- **Confidence:** confirmed

### JS-B-6 · medium · inconsistency

- **Where:** `a11y_runtime.mjs:2953` (`ran` is every check not skipped), `:3351` (written to the JSON and the text header), against the `mode === 'page'` guards at `:3124` (taborder), `:3205` (the no-keymap warning) and the reflow, spacing, obscured, hover and motion guards after it
- **What:** On a proof sheet, `ran` lists checks that never run there.
- **Evidence:** `--matrix sheet.html --skip axe --skip forced --json` gives `ran: names taborder focus contrast keys reflow spacing obscured hover motion`; none of `taborder reflow spacing obscured hover motion` executed (the header comment at :55 says so), and `cellsTotal 2, cellsMeasured 2`.
- **Effect:** The report header reads "checks: … reflow spacing obscured hover motion" on a sheet, the JSON says they ran, and a budget on `reflow_failures` or `motion_not_reduced` passes at 0 for a check that did not run, which the suite elsewhere refuses to do.
- **Fix:** Compute `ran` from what the mode runs (`PAGE_ONLY = ['taborder','reflow','spacing','obscured','hover','motion']`, dropped in matrix mode) and list them under `notRun` with the reason. Regression test: a matrix run's `ran` excludes them.
- **Confidence:** confirmed

### JS-B-7 · medium · bug

- **Where:** `a11y_runtime.mjs:2714` (`forced_colors_lost: (f) => f.filter((x) => x.check === 'forced').length`), `:3252` (`finding('forced', 'forced-colors-not-emulated', '-', 'warning', …)`)
- **What:** The budget counter counts every `forced` finding, so the warning that says the check could not run counts as one lost ring.
- **Evidence:** The two lines above; no test names `not-emulated` or `forced_colors_lost` (grep of `tests/`).
- **Effect:** With `forced_colors_lost: 0` in the budget (the documented setting), a browser that cannot emulate forced colours fails the run as a breach, with a counter that says a ring was lost; the message says the check was "skipped rather than reported as a pass", and the exit code says the opposite.
- **Fix:** Count `x.rule === 'focus-ring-lost-in-forced-colors'` only. Regression test on the counters with a synthetic findings list.
- **Confidence:** confirmed (by reading)

### JS-B-8 · medium · bug

- **Where:** `skills/a11y-audit-runner/scripts/browser_common.mjs:748–752` (`runEach`: `spawnSync(process.execPath, …, { encoding, maxBuffer, env })`, no `timeout`, stdio piped), used by `a11y_runtime.mjs:3403` and `measure_vitals.mjs` `several()`
- **What:** A multi-page or multi-viewport run spawns each child with no time limit and captures its stderr, so one hung child (JS-B-1, JS-B-2) hangs the whole run with nothing on screen after `[i/n] url at size…`, and every other page's result is lost.
- **Evidence:** The spawn options above; `runEach` reads `proc.status`, `proc.error` and `proc.stderr` only after the child exits.
- **Effect:** `--urls sitemap.xml --viewports 390x844,1280x900` on a site with one stalling page never produces a report; CI's job times out and bills its minutes.
- **Fix:** `timeout: PER_RUN_MS` (say 15 minutes, overridable) with `killSignal: 'SIGKILL'`, treat `proc.error.code === 'ETIMEDOUT'` as exit 2 with the message "timed out after …", and pass the child's stderr through (`stdio: ['ignore', 'pipe', 'inherit']`) so the last progress line is visible. Regression test with a child script that sleeps.
- **Confidence:** confirmed (by reading; shared file, also JS-A's)

### JS-B-9 · medium · gap

- **Where:** `a11y_runtime.mjs:3002` (`viewport: opts.viewport` with no `isMobile`/`hasTouch`), against `critique_snapshots.mjs:323` (`isMobile: width < 768, hasTouch: width < 768`) and the promise at `a11y_runtime.mjs:103–104` and scripts.md ("a phone's menu and its target sizes (2.5.8) hidden at 1280x900")
- **What:** `--viewport 390x844` is a 390 px desktop window: `(hover: hover)` and `(pointer: fine)` still match, `100vh` is the desktop one, there is no touch, and a site that switches navigation or target sizes on those queries (the suite's own `hover` check and 2.5.8 depend on them) shows its desktop behaviour.
- **Evidence:** `grep isMobile skills/*/scripts/*.mjs` finds only the critique script.
- **Effect:** The phone pass audits a narrow desktop; `target size` findings and the `hover` check describe a page a phone user does not get, and the two scripts disagree about what 390 px means.
- **Fix:** Set `isMobile` and `hasTouch` when the width is under 768 (or add `--mobile`), say so in the report's `viewport` field, and document it in scripts.md. Note the `hover` check then needs `page.mouse` to still work (it does under `hasTouch`).
- **Confidence:** likely

### JS-B-10 · medium · bug

- **Where:** `measure_vitals.mjs:305` (the LCP observer takes the last entry), `:629–632` (`--interact-at` clicks while the page loads)
- **What:** The browser stops emitting `largest-contentful-paint` entries at the first input, so in an `--interact-at` run the reported LCP is the largest paint *before the click*, not the page's LCP, and nothing in the output says so.
- **Evidence:** The LCP API's defined behaviour (entries stop after user input: click, key or scroll); the report has no note for it, and `lcp_ms` is still compared with the budget at :979.
- **Effect:** `--interact-at 800` on a page whose hero paints at 1,900 ms reports an LCP of a few hundred ms and passes `lcp_ms: 2500` with a number that is not LCP.
- **Fix:** In an `--interact-at` run, report `lcp` as "up to the click at N ms" (a note, and `lcpTruncated: true` in the JSON), and do not compare it with the budget, or measure LCP in a separate run without the click.
- **Confidence:** likely

### JS-B-11 · medium · bug

- **Where:** `measure_vitals.mjs:541` (`target.waitFor`), `:544` (`pageClockOffset` with three `page.evaluate` round trips), `:547` (`wait = interactAt - onPage()`)
- **What:** Both the wait and the clock sync need the page's main thread. When the hydration long task the click is meant to land in starts before the sync completes, the sync is held until the task ends, `wait` is then negative, and the click lands on an idle page: fast, under the 16 ms `durationThreshold` (:366), so no event entry and INP is `n/a`.
- **Evidence:** The call order above; `tests/test_browser_runtime.py` `test_interact_at_clicks_while_the_page_hydrates` (`--interact-at 2500`, asserts `clickedAt <= 2800` and `stats.inp` not None) is the known flake.
- **Effect:** The one measurement `--interact-at` exists for is skipped on exactly the pages it targets, and the `late` note (:944) does not fire because `clickedAt` was read before the click.
- **Fix:** Take the clock offset right after `goto` resolves at `commit` (before the page's scripts run), and have `target.waitFor` race a deadline; record the time the click *dispatched* (after `mouse.click` returns) as well, and note when it is past `interactAt + 50`.
- **Confidence:** likely

### JS-B-12 · medium · gap

- **Where:** `a11y_runtime.mjs:1518` (the contrast loop walks `deep.texts()`, text nodes only), `:1692` (its fix text: "The five places teams fail are placeholder text (it is text, there is no exemption) …"), against `critique_snapshots.mjs:233` (samples `::placeholder` and control values)
- **What:** A placeholder and an input's value are not text nodes, so the a11y contrast check never measures them, while its own message names placeholder as the first failure.
- **Evidence:** The loop and the message; no `placeholder` in `tests/test_browser_runtime.py` or `test_runtime_wcag_checks.py`.
- **Effect:** `::placeholder { color: #aaa }` on white (2.3:1) passes the gate that says it is the most common failure.
- **Fix:** After the text loop, sample `input, textarea, select` as the critique script does (value colour, else `::placeholder` colour), through the same background walk. Regression test on a grey placeholder.
- **Confidence:** confirmed (by reading)

### JS-B-13 · medium · inconsistency

- **Where:** `a11y_runtime.mjs:690` (`AXE_SEVERITY = { critical: 'error', serious: 'error', moderate: 'warning', minor: 'warning' }`), `:709`
- **What:** A WCAG-tagged axe violation rated `moderate` or `minor` is a warning and never fails the run; scripts.md documents the best-practice demotion only, and the header says exit 1 means "violations found".
- **Evidence:** The map; e.g. axe's `no-autoplay-audio` (1.4.2) and `html-xml-lang-mismatch` (3.1.1) are `moderate`.
- **Effect:** A page that autoplays audio exits 0 with a warning; the budget key `axe_violations` still counts it, so the two gates disagree.
- **Fix:** Either fail on every WCAG-tagged violation whatever its impact (impact is axe's guess at severity, not conformance), or document the rule next to the best-practice one in scripts.md.
- **Confidence:** confirmed (by reading)

### JS-B-14 · low · bug

- **Where:** `measure_vitals.mjs:1096` (`several()`'s text report prints a reason only when `r.breaches.length`), `:1035` (a run with no LCP exits 1)
- **What:** A page that exits 1 for "no LCP was recorded" shows `—` and exit 1 in the table and no line under it.
- **Evidence:** The two branches; the child's stderr message is captured and discarded (`report` parsed, so `error` is null).
- **Effect:** The multi-page report fails without saying why for a blank page.
- **Fix:** Print a line when `r.exit === 1 && !r.breaches.length` ("no LCP was recorded").
- **Confidence:** confirmed (by reading)

### JS-B-15 · low · inconsistency

- **Where:** `measure_vitals.mjs:94` ("1 … a run failed to produce a metric") against `:1035` (exit 1 only when `stats.lcp == null`, every run)
- **What:** One run of five with no LCP passes on the median of the other four; the header says it exits 1.
- **Evidence:** `spread()` filters non-numbers; `stats.lcp` is null only when all runs lack it.
- **Effect:** The documented contract is stricter than the code; `rangePct` is computed over fewer runs than `--runs` without a note.
- **Fix:** Note the runs that lacked a metric (`n` is already in `spread`), and either fail or say so in the header.
- **Confidence:** confirmed (by reading)

### JS-B-16 · low · bug

- **Where:** `a11y_runtime.mjs:350` (`const globalRoot = npmGlobalRoot();` before the candidates are tested)
- **What:** Every run shells out to `npm root -g` (a 20 s timeout) even when axe is beside the script or on `NODE_PATH`, because the global root is pushed before the `existsSync` loop.
- **Evidence:** `time npm root -g` = 1.46 s on this machine; `loadPlaywright` only reaches `npmGlobalRoot()` when the import fails.
- **Effect:** 1.5 s added to every a11y run, per child in a `--urls` run, and a hang of up to 20 s where npm is slow.
- **Fix:** Test the local candidates first and ask npm only when none exists.
- **Confidence:** confirmed

### JS-B-17 · low · dead-code

- **Where:** `snapshot_matrix.mjs:75` (`createRequire` imported, never used: grep finds only the import), `a11y_runtime.mjs:913` (`opts` parameter of `analyseTabOrder` unused), `:534` (`let inner = null` overwritten in both branches), `:903` (an `eslint-disable` for a rule that does not fire)
- **What:** Leftovers.
- **Evidence:** ESLint's report and `grep -n createRequire` on the matrix script.
- **Effect:** None.
- **Fix:** Remove them.
- **Confidence:** confirmed

### JS-B-18 · low · bug

- **Where:** `snapshot_matrix.mjs:133` (`opts.dpr = Number(need(i, a))`, unvalidated; `--threshold` and `--pixel-threshold` at :128–129 are checked)
- **What:** `--dpr abc` reaches `deviceScaleFactor: NaN` and Playwright throws, so the run ends with a stack trace and exit 2 instead of a one-line argument error.
- **Evidence:** No check on `opts.dpr`; `a11y_runtime.mjs` and `measure_vitals.mjs` use `num()`.
- **Effect:** A worse message, and a `--dpr 0` that Playwright rejects late.
- **Fix:** Validate as a positive finite number.
- **Confidence:** confirmed (by reading)

### JS-B-19 · low · bug

- **Where:** `a11y_runtime.mjs:1951` (`waitForTimeout(220)` after each reflow resize), `:1778` and `:1865` (120 ms after Enter in the key map)
- **What:** Fixed short waits. `FREEZE_ANIMATIONS_CSS` finishes CSS transitions, but a debounced `resize` handler (250–300 ms is the common value) or a dialog opened by a JS timer or the Web Animations API (which the CSS freeze does not touch) is measured mid-change.
- **Evidence:** The literals; runtime-checks.md §9 itself says "Anything measured after a resize and before a settle is measuring a reflow in progress".
- **Effect:** A reflow finding on a layout that was still moving; `does-not-open-by-keyboard` on a dialog that opens at 200 ms (its `visible()` reads opacity 0 as hidden).
- **Fix:** Wait for two animation frames plus a quiet period (no resize/mutation for 100 ms, capped at 1 s) rather than a constant.
- **Confidence:** possible

### JS-B-20 · low · gap

- **Where:** `a11y_runtime.mjs:2551` (`duration: typeof timing.duration === 'number' ? … : 0`), `:2644–2647` (`if (!r.loops && r.duration < 100) return false;`)
- **What:** A scroll-driven animation (`animation-timeline: scroll()`, the parallax that is the classic vestibular trigger) has no time-based duration, reads as 0 ms and is dropped before the comparison.
- **Evidence:** The two lines; the spec §6 lists "motion a click or a hover starts" as unseen, not scroll-driven motion, which the check scrolls the page precisely to provoke.
- **Effect:** `motion-not-reduced` never fires on parallax.
- **Fix:** Treat an animation whose timeline is not a `DocumentTimeline` as moving for the run's length (or report it under its own rule).
- **Confidence:** possible

### JS-B-21 · low · bug

- **Where:** `a11y_runtime.mjs:2648` (`if (!n) return true;` in `motionFindings`)
- **What:** An animation that runs only under `prefers-reduced-motion: reduce` (a reduced variant with a new name on an element that had none before) is reported as "moves … with prefers-reduced-motion: reduce, as it does without it", which is false.
- **Evidence:** The line, and the message template at :2656.
- **Effect:** A misleading warning on the right implementation.
- **Fix:** Report such a case with its own wording, or skip it when its travel is under the threshold on its own.
- **Confidence:** possible

### JS-B-22 · low · gap

- **Where:** `critique_snapshots.mjs:290` (`page.screenshot({ fullPage: true })`), `:335` (a 300 ms settle, no scroll)
- **What:** The full-page capture is taken without ever scrolling the page, so `loading="lazy"` images and `IntersectionObserver` reveals below the fold are blank or still at `opacity: 0`; `a11y_runtime.mjs`'s `EXERCISE_FN` (:2579) scrolls a viewport at a time for this reason.
- **Evidence:** The two scripts' approaches; Playwright's full-page capture resizes the viewport for the shot, which starts reveals but does not wait for them or for lazy images.
- **Effect:** The squint, greyscale and 25 % views judge empty sections, which is the hierarchy question they exist to answer.
- **Fix:** Scroll to the end a viewport at a time, wait for `img.complete` on lazy images, then capture; or share `EXERCISE_FN`'s scroll loop.
- **Confidence:** possible

### JS-B-23 · low · bug

- **Where:** `a11y_runtime.mjs:1062` (`DIFF_FN = ({ aURL, bURL }) => new Promise(async (resolve) => { … })`)
- **What:** The one `no-async-promise-executor` ESLint error: a throw inside `load()` (a PNG that does not decode, a canvas over the size limit) rejects nothing and the promise never resolves, so `cmpPage.evaluate(DIFF_FN)` at :1197 waits forever.
- **Evidence:** The construction; no realistic trigger found (the inputs are Playwright's own PNGs of at least 2x2 px), so this is not the hang the owner saw.
- **Effect:** A latent infinite wait in the focus path.
- **Fix:** Make it a plain `async` function returning the result (no executor), so a throw rejects and `measureFocus`'s `catch` records it.
- **Confidence:** confirmed (by reading)

### JS-B-24 · low · risk

- **Where:** All five scripts' tail: `main().then((code) => process.exit(code))`
- **What:** Node documents that writes to a pipe are asynchronous on macOS and may be cut by `process.exit()`; a large `--json` piped to `jq` or to `runEach`'s parent could be truncated there.
- **Evidence:** Node's "A note on process I/O"; not reproduced on Windows (2 MB arrived intact both with `process.exit` and with `exitCode`).
- **Effect:** On macOS, a parse error in the parent of a `--urls` run or in a consumer; it would look like a flake.
- **Fix:** Set `process.exitCode = code` and return instead of calling `process.exit()` in the success path.
- **Confidence:** possible

Risks checked and clean: the scripts fetch nothing beyond the pages the user names (`--urls` reads a user-given http(s) URL; axe and Playwright come from disk; `--header` is routed to the page's origin only; `render_email.mjs` aborts every http(s) request and runs with JavaScript off). They write only `--report`, `--out` (the matrix's `current/` and `diff/`, the critique's PNGs and `contrast.md`, the email renders) and the baselines folder. No secret is echoed: `--header env:NAME` and `--steps` `env` values never appear in a message, the storage state is never printed. The JSON `target` carries the URL as given, query string included.

## The 390 px hang: candidates

Ranked; the first is reproduced, the rest are the remaining unbounded waits.

1. **`a11y_runtime.mjs:3024`, `await document.fonts.ready` in `page.evaluate`.** Reproduced (JS-B-1): a font request outstanding at that moment that never completes leaves the promise pending forever; `page.evaluate` has no timeout. The trigger has to start the load after the document's own fonts (which would otherwise hold `load` and make `goto` die at 45 s): a loader or component upgrading in a `load` handler, an icon font first used by late-rendered content. A 390 px layout plausibly requests a font the 1280 px one does not (a mobile navigation's icon face), or the same CDN stalled for that run. The symptom matches the owner's exactly: `browser:` and then nothing. Confirm on webawesome.com with `DEBUG=pw:api node a11y_runtime.mjs --url … --viewport 390x844`: the last API line will be the `evaluate` after `goto`.
2. **`a11y_runtime.mjs:1180` and `:1195`, the focus screenshots.** Reproduced (JS-B-2): 30 s per shot on the same stalled font, times two shots, times every stop, times two for `forced`, times each density; the errors are swallowed and the check passes empty. Not infinite, but a 40-stop page is 40 minutes, with the log stuck at `focus indicator on N element(s)…`.
3. **`a11y_runtime.mjs:632–636`, `injectAxe`'s per-frame `addScriptTag` and `evaluate`.** Unbounded, in a loop over frames the page adds (third-party embeds, consent managers). Tested and not a stall on this Chromium for a sandboxed `srcdoc` frame without `allow-scripts` (`frame.evaluate` returned in 3 ms), nor for a `loading="lazy"` frame; a frame stuck in a cross-process navigation remains the untested case.
4. **`a11y_runtime.mjs:1062`, `DIFF_FN`'s async executor** (JS-B-23): infinite if `load()` throws; no trigger found.
5. **The double-`requestAnimationFrame` waits** at `:1179`, `:1194`, `:1273`, `:2146`, `:2582`, `:2583`, `:3033`: unbounded if the renderer stops producing frames; they fired in 29 ms on the stalled-font page, so not this hang.
6. **`browser_common.mjs:751`, `runEach`'s `spawnSync` with no `timeout`** (JS-B-8): turns any of the above into a hang of the whole `--viewports`/`--urls` run with the child's progress hidden.

The structural fix is one helper, `bounded(promise, ms, what)`, around every `page.evaluate`/`frame.evaluate` that awaits page-controlled promises, a `timeout` on each screenshot, a per-child timeout in `runEach`, and a log line naming the step *before* it starts (the current log names a check only after the previous one finished, which is why the owner saw nothing).

## The known flakes: what the script shows

- **`test_runtime_urls.EachPageHasItsTypesBudget` (Windows, under load):** not a race in the script. `several()` runs the pages one after another by design (`measure_vitals.mjs:1051`), each child launching its own Chromium; under a 100 % CPU the sum passes the test's 600 s. Nothing to fix in the script beyond JS-B-8's timeout, which would at least end it.
- **`test_tbt_stops_at_tti` (Windows):** partly visible. TTI needs a 5 s quiet window that ends before the harvest (`if (e > now) break;` at :430), so the result depends on how late FCP and the fixture's long task land on a slow machine; with the task scheduled at 1,000 ms and FCP arriving later than that under load, the task is `before-fcp` and `inTbt` false, which is the assertion that fails. A fixture-timing race, not a script bug, but the script could report `fcp` and `now` next to `tti` to make such a failure readable.
- **`VitalsUnderCsp` (macOS):** not visible in the script. The collector is an init script, which CSP does not govern, and the shift is 200 ms after first paint with a 1,500 ms settle. JS-B-24 (an async pipe write cut by `process.exit()` on macOS) is the only macOS-specific mechanism found, and the JSON here is small, so it is a weak fit.
- **`test_interact_at_clicks_while_the_page_hydrates`:** visible, JS-B-11. The clock sync (:544) and `target.waitFor` (:541) both need the main thread the hydration task occupies; when the task starts first, the click is delayed past it, lands fast, produces no event entry and INP is `n/a`.
- **The vitals timing tests (`VitalsTiming`):** not visible. Both run `networkTtfb` and `pageClockOffset` on fake clocks with no browser; the only real-time element is a 60 s subprocess timeout for `node -e`, so a flake there is the machine, not the functions.

## Static-analysis candidates, resolved

- `a11y_runtime.mjs:534` (`inner` assigned, unused): harmless; the initial `null` is overwritten in both the `try` and the `catch`. Remove the initialiser (JS-B-17).
- `:903` (unused `eslint-disable no-await-in-loop`): harmless; delete the directive (JS-B-17).
- `:913` (`opts` unused in `analyseTabOrder`): harmless; drop the parameter at the one call site (:3149) (JS-B-17).
- `:1062` (async Promise executor in `DIFF_FN`): real latent bug, not the owner's hang (JS-B-23): a throw is lost and the evaluate never returns; no trigger found with Playwright's own PNGs.
- `:1179`, `:1194`, `:1273`, `:2146`, `:2582`, `:2583`, `:3033` (return values from executors): fine by design; each is `new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))`, where the arrow's return value is `requestAnimationFrame`'s handle, never read; `r` is called inside. Not meant to resolve the promise. Could be written with a block body to silence the rule.
- `:2987` (`axeVersion = '?'`) and `:2995` (`shadowRoots = null`) assigned, unused: fine by design; both are reassigned inside the `try` and read when the report is built after it; ESLint cannot see the exception path where the initial value is what the `finally`-less code would have reported. Keep.
- `snapshot_matrix.mjs:75` (`createRequire` unused): dead, confirmed by grep (JS-B-17).
- `:434` (executor return value): fine by design, the same rAF idiom.
- `measure_vitals.mjs:548` (executor return value): fine by design, `new Promise((r) => setTimeout(r, wait))`.

## What is covered well

The two things the owner would most expect to be wrong are right. The matrix comparator's antialiasing escape does not hide a shift: a 1 px move of a rule and a label mismatched 2.0 % of a 200x60 cell (threshold 0.2 %), 2 px 6.3 %, 3 px 6.9 %. `--json` through a pipe survives `process.exit()` on Windows at 2 MB. The exit-code contract is consistent across all five scripts (0 clean, 1 findings or breach, 2 the run itself), budget files are validated before a browser starts, `refuseOverwrite` keeps a report from replacing its inputs, the forced-colours pass verifies the media query instead of assuming it, the contrast overlay probe (PR #213) handles scroll containers, shadow roots and `pointer-events: none` scrims and puts every scroll and style back, TBT keeps an interaction's own work out, CLS follows the session-window definition, the TTFB comes from the network stack so throttling shows in it, and nothing is ever fetched from a CDN. The tests exercise the browser paths for real (six runtime test files, about 100 cases), which is why the remaining bugs are the kind a fixture never had: a frame with a focusable child, a faded ancestor, an icon-font button, a font that never arrives.

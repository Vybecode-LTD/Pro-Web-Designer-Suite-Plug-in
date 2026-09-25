---
name: perf-budget-gate
description: Derive, set and enforce web performance budgets, then fail the build when they break. Use for Core Web Vitals, LCP, CLS, INP, TBT and TTFB, "the site is slow", "why is my LCP four seconds", page weight and bundle size limits, image optimization and oversized hero images, font loading performance and layout shift from font swap, render-blocking CSS, third-party script weight, Lighthouse in CI, and performance regression testing against a committed baseline. Reach for it whenever anyone mentions performance budgets, page speed, load time, largest contentful paint, cumulative layout shift, interaction to next paint, lazy loading, preload, preconnect, fetchpriority, code splitting, critical CSS, srcset, AVIF or WebP, PageSpeed Insights, CrUX or field data — and any time a site is beautiful, fully tokenized, and still takes four seconds to show anything.
---

# Performance Budget Gate

The suite has a design gate and no performance gate. That asymmetry is exactly how a beautifully-tokenized site ships with a four-second LCP: **the thing that is measured is the thing that gets fixed.**

`audit_design.py` fails the build when the design regresses. This skill is its counterpart — it fails the build when *performance* regresses, against budgets agreed up front rather than opinions argued after the fact.

| | `audit_design.py` | `perf_audit.py` + `measure_vitals.mjs` |
|---|---|---|
| Asks | "is this code legal?" | "is this page within its budget?" |
| Enforces | nine laws, fixed | numbers **you derived**, per page type |
| Blind to | a 900 KB hero that uses every token correctly | a hardcoded colour in a 12 KB stylesheet |
| Fails when | someone writes `margin: 24px` | someone adds a dependency |

Run both. They fail for different reasons and both failures are actionable. They overlap in exactly one place and it is the right one: `transition: width` is a design violation (it animates a property nobody chose) *and* a performance violation (it relayouts every frame and shifts its siblings). Two independent reasons, same line.

---

## The budget-first principle

**A budget set after the fact is a negotiation. A budget set before is a constraint.**

The difference is not rhetorical. Once a feature exists and works, "it adds 180 KB" is weighed against shipping a thing that is finished, and the feature wins every time — not because anyone is wrong, but because the cost is abstract and the benefit is on screen. Set the number first and the same conversation happens while the design is still cheap to change.

Three rules follow, and they are the whole discipline:

1. **A number you cannot reconstruct will be argued away.** Every budget must trace back to a promise about a device and a network. `references/budgets.md` §1 has the arithmetic.
2. **A budget with no device and network attached is not a budget, it is a preference.** The same 2.5-second LCP target yields 250 KB on Slow 4G and 1.5 MB on Fast 4G. Say which one you meant.
3. **Raising a budget is a reviewed decision, not a line in the commit that needed the room.** `references/budgets.md` §7 is the five-question review and the log entry that makes it stick.

---

## Two layers, and which one comes first

| | **Layer 1 — static** | **Layer 2 — runtime** |
|---|---|---|
| Tool | `scripts/perf_audit.py` | `scripts/measure_vitals.mjs` |
| Reads | bytes on disk, markup, CSS, JS | a real browser's PerformanceObserver |
| Runtime | ~1 second | ~1 minute for 5 runs |
| Determinism | **total** — same input, same number, forever | variable; needs deliberate work to be non-flaky |
| Needs | Python 3 stdlib | Chromium, Playwright, a served build |
| Catches | un-preloaded font, lazy LCP image, 900 KB hero, bundle +40% | LCP 1.9s → 2.6s with no byte change |
| Misses | whether any of it mattered | which commit did it |
| Runs on | **every commit** | PR, and main after merge |

**Start with layer one. Add layer two deliberately.**

Most teams do the opposite: they put Lighthouse in CI on day one, get flaky results in the first week, add `continue-on-error: true`, and now own a job that measures nothing and blocks nothing. The static layer catches most real regressions, deterministically, for a second of CI time. Earn the trust there, then spend it.

The runtime layer is still necessary. A build can sit inside every byte budget for a year and drift from a 1.9-second LCP to a 3.1-second one because a third-party tag got slower, a font started blocking, or the LCP element moved to something that loads late. No amount of byte counting sees that.

---

## Workflow

### 1. Set the budget from a target, not a wish

Write one sentence with four decisions in it:

> "The hero renders in under 2.5 seconds for three quarters of our users on a mid-tier Android phone over a slow 4G connection."

Metric · target · percentile · **device and network**. The fourth is the one people skip, and it is the one that makes the arithmetic possible:

```
Slow 4G: 1.6 Mbps down = 204,800 B/s ≈ 200 KB/s;  RTT 150 ms

  DNS + TCP + TLS                  3 × 150 ms  =   450 ms
  request → first byte     150 ms + 200 ms svr =   350 ms
  ---------------------------------------------------------
  TTFB subtotal                                    800 ms   ← web.dev's "good" TTFB

  Target LCP                                      2500 ms
  − TTFB                                         −  800 ms
  − render, parse, decode on a 4×-slow CPU       −  300 ms
  − TCP slow-start tax on the first ~100 KB      −  150 ms
  =========================================================
  time for critical-path bytes                    1250 ms
  × 200 KB/s                                  =    250 KB    ← the critical path
  × 2.4                                       =    600 KB    ← total page weight
```

250 KB allocates to 25 KB HTML + 30 KB blocking CSS + 25 KB font + 150 KB LCP image + 20 KB slack. The full derivation, the per-category reasoning, the per-page-type overrides and what changes on 3G or desktop are in `references/budgets.md` §§1–3.

Write it into `perf-budget.json` **with the device and network in a comment**, because the first question about a number anyone dislikes is "says who".

### 2. Measure the current state

```bash
python -m scripts.perf_audit dist/ --src src/ --budget perf-budget.json
```

One second, and you have a weight ledger, the largest assets with their intrinsic dimensions, and every static risk. Then, on a served build:

```bash
python3 -m http.server 8080 --directory dist &
node scripts/measure_vitals.mjs http://127.0.0.1:8080/ --runs 5 --throttle slow4g
```

**Do not skip the LCP element line.** Half of all LCP work is spent optimising something that was never the largest paint.

### 3. Fix the biggest thing

Not the easiest thing, and not everything. Performance work has a brutally skewed payoff distribution: one 5 MB PNG outweighs every other finding on the page combined. The ledger sorts by size for exactly this reason.

`references/diagnosis.md` is a tree, one entry per symptom, each with **symptom → mechanism → how to confirm → fix**. The middle two matter most — performance work goes wrong when someone applies a fix to a mechanism that was not operating and then cannot tell whether it helped.

### 4. Install the gate with a baseline

```bash
python -m scripts.perf_audit dist/ --budget perf-budget.json \
  --write-baseline .perf-baseline.json
git add .perf-baseline.json
```

The baseline records today's findings **and today's byte totals**. Existing debt is frozen; new violations fail immediately; growth past `budget.growth` fails even while the absolute budget is still blown.

That last clause is what makes this usable on a legacy codebase. The gate can go on this afternoon on a site that is comprehensively over budget, be green on day one, and still catch a real regression on day two. A gate that fails on day one is a gate somebody deletes on day two.

### 5. Re-derive when the target changes

A budget is downstream of a promise. When the promise changes — a new market on worse connections, a decision to support a cheaper device class, a product move from content site to application — **run the arithmetic again from the new target.** Do not adjust the numbers until they feel right; that is how a budget stops meaning anything.

The trigger you will actually hit: **field p75 more than 1.5× your lab median.** That means the lab profile describes a page, device or network your users do not have. `references/ci-integration.md` §8.

---

## The Core Web Vitals, as of September 2026

Verified against web.dev before writing. **These are field metrics, assessed at the 75th percentile of real page loads, segmented across mobile and desktop.**

| Metric | Good | Needs improvement | Poor | Measures |
|---|---|---|---|---|
| **LCP** | ≤ 2.5 s | 2.5 – 4.0 s | > 4.0 s | When the largest element painted |
| **INP** | ≤ 200 ms | 200 – 500 ms | > 500 ms | Worst interaction's full latency, outliers trimmed |
| **CLS** | ≤ 0.1 | 0.1 – 0.25 | > 0.25 | Largest session window of unexpected layout shift |

INP replaced First Input Delay on **12 March 2024**. FID measured only the input *delay* of the *first* interaction; INP measures input delay + processing + presentation for essentially the worst one. A site could have a perfect FID and a poor INP without changing a line of code.

Two supporting metrics, in the budget file because they diagnose, not because they are CWV:

| Metric | Good | Poor | Why it is here |
|---|---|---|---|
| **TTFB** | ≤ 0.8 s | > 1.8 s | The floor under LCP. **Not a CWV** — you can miss it and still pass. |
| **TBT** | ≤ 200 ms | > 600 ms | The lab proxy for INP. There is no field TBT. |

**The honest statement, which everything here is downstream of:** p75 field data is the thing that actually matters. A CI number is a **regression detector against itself** on one machine with one throttle profile — enormously useful, and not a prediction of what your users experience. When lab and field disagree, the field is right. `references/budgets.md` §8.

---

## `scripts/perf_audit.py` — stdlib Python 3, no dependencies

The static layer, and deliberately `audit_design.py`'s sibling: same report shape, same severity model, same baseline philosophy, same comment pragmas, same exit codes.

| Category | What it catches |
|---|---|
| **B** Budget | per-type bytes, request counts, largest asset, third-party origins, growth delta per category |
| **L** LCP risk | lazy-loaded hero, missing `fetchpriority`, JS-discovered hero, CSS background hero, render-blocking CSS beyond the first, sync `<script>` in `<head>`, `@import`, fonts never preloaded, preload without `crossorigin`, third-party origins with no `preconnect` |
| **C** CLS risk | `<img>`/`<iframe>`/`<video>` without dimensions, `@font-face` with no `font-display` or no metric-matched fallback, transitions on layout properties, banners prepended to `<body>` |
| **T** Main thread | scripts without `defer`/`async` |
| **W** Weight | oversized images vs rendered size, poor format with no modern sibling, legacy font formats, unsubset fonts, bloated SVG, duplicated dependencies and duplicate versions, unused-looking CSS |

```bash
python -m scripts.perf_audit dist/                          # weigh and scan the build
python -m scripts.perf_audit dist/ --src src/               # also scan source, uncounted
python -m scripts.perf_audit dist/ --page-type dashboard    # per-page-type budget
python -m scripts.perf_audit dist/ --json                   # ledger + findings
python -m scripts.perf_audit dist/ --strict                 # warnings fail too
python -m scripts.perf_audit dist/ --write-baseline .perf-baseline.json
```

| Flag | Does |
|---|---|
| `--src DIR` | scan for markup/CSS/JS problems but **do not** count toward byte budgets (repeatable) |
| `--budget FILE` | default `perf-budget.json`; built-in defaults if missing |
| `--page-type NAME` | glob-matched against the `pages` map, deep-merged onto `defaults` |
| `--baseline FILE` | ignore recorded findings, compare byte totals (default `.perf-baseline.json`) |
| `--write-baseline FILE` | record findings **and** totals |
| `--category B\|L\|C\|T\|W` | narrow the report (repeatable) |
| `--json` `--strict` `--quiet` `--no-color` `--no-ledger` `--include-maps` | |

Exit `0` clean · `1` violations · `2` bad invocation.

**Byte accounting.** Text is budgeted on its **gzip -6 size**, computed with the stdlib, because raw bytes on disk are not what crosses the wire. Already-compressed binaries (images, woff2, video) are counted raw. Brotli ships 15–20% under gzip for text, so this over-counts on purpose: an over-count is a conversation, an under-count is a regression nobody sees.

**Alternate encodings of one image are counted once, at the largest variant.** Shipping `hero.avif`, `hero.webp` and `hero.jpg` is correct and exactly one is fetched. A `srcset` *width* ladder is not collapsed — the tool cannot know which rung a viewport picks, and it says so rather than guessing.

Escape hatches are comment pragmas, so every exception is visible in review. Tags are a category, a rule name, or `ALL`; everything after `--` is the reason:

```html
<!-- perf-audit-ignore-next-line: C -- dimensions come from the CMS, PERF-412 -->
```
```css
/* perf-audit-ignore-file: W -- vendor sheet, replaced in Q3 */
```

---

## `scripts/measure_vitals.mjs` — Node + Playwright, no other dependencies

The runtime layer. Real `PerformanceObserver` entries, N runs, median plus spread.

```bash
node scripts/measure_vitals.mjs http://127.0.0.1:8080/ --runs 7 --throttle slow4g
node scripts/measure_vitals.mjs http://127.0.0.1:8080/ --budget perf-budget.ci.json
node scripts/measure_vitals.mjs http://127.0.0.1:8080/ --interact "button.buy" --json
```

| Flag | Does |
|---|---|
| `--runs N` | iterations; the median is reported (default 5) |
| `--throttle NAME` | `slow4g` (default) · `fast4g` · `cpu4` · `off`, applied via CDP |
| `--budget FILE` | compares the median against `defaults.lab`; non-zero exit on breach |
| `--page-type NAME` | per-page-type `lab` override |
| `--interact SEL` | click it after load and measure **real INP** |
| `--warm` | measure the second load instead of a cold one |
| `--settle MS` · `--viewport WxH` · `--dpr N` · `--resources N` · `--json` · `--browser PATH` · `--quiet` | |

Exit `0` inside budget · `1` breach or no LCP recorded · `2` bad arguments or no browser.

Four things it does that most runtime checks do not:

- **It names the LCP element's CSS selector.** Enormously useful, rarely done, and the first thing you need. The three surprises it produces: the LCP is a block of *text*, not the image you assumed; it changes between runs because two candidates are nearly the same size; or it is a skeleton box and the real content paints later still.
- **It breaks LCP into the four sub-parts** — TTFB, resource load delay, resource load duration, element render delay — with the target share of each. The two phases that should be under 10% are where the bugs live: load duration is physics, load *delay* and render delay are latency you added.
- **It names the nodes in the largest CLS session window**, with the timestamp of each shift.
- **It refuses to invent an INP.** A page nobody touched has no interaction latency, so it prints `n/a` and says TBT is the proxy. It also reports total blocking time alongside TBT, because a long task that finishes before FCP contributes **zero** TBT while being the worst thing on the page.

**The browser is never downloaded.** It launches with an explicit `executablePath` (`--browser`, else `$PERF_CHROMIUM`, else the first that starts of `/opt/pw-browsers/chromium`, Playwright's own Chromium, an installed Chrome or Edge) and fails with instructions if none of them starts. Install the module with `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i -D playwright`.

**Serve the page over HTTP.** `file://` has no network stack — TTFB is ~0, resource priorities do not apply, throttling barely bites, and every number flatters you. The script warns and keeps going if you insist.

---

## What a failing run looks like

Static layer. The ledger comes first because the answer is usually in it:

```
Weight ledger   (budget: perf-budget.json)
             transfer     budget    used  requests
  total        7.72MB    600.0KB   1287%  10
  html           487B     25.0KB      2%  1
  css            661B     60.0KB      1%  4
  js             538B    170.0KB      0%  2
  image        7.67MB    300.0KB   2557%  2
  font         49.1KB    100.0KB     49%  1

  Largest assets
       5.30MB  image  images/card.png  1800x1200
       2.37MB  image  images/hero.jpg  2400x1350

index.html
     16  error  C img-no-dimensions   `<img>` has no width/height: hero.jpg.
     16  error  L lcp-lazy            Likely LCP image is `loading="lazy"`: hero.jpg.
<images>
      1  error  W oversized-image     images/hero.jpg is 2400x1350 intrinsic but renders
                                      at 720px wide (3.3x). 2.37MB where ~854.9KB would
                                      look identical.
```

Runtime layer, same page:

```
Metric      median      min       max    spread  rating
  LCP          312       284       420      44%  good
  CLS        0.269     0.269     0.269       0%  poor
  long tasks    1 task(s), longest 123ms, 73ms blocking in total

  LCP element   html > body > main.page > div.card:nth-of-type(1) > img

  LCP sub-parts                        target
    TTFB                       3ms     1%   ~40%
    resource load delay       14ms     4%   <10%
    resource load duration    50ms    16%   ~40%
    element render delay     245ms    79%   <10%     ← the bug

  Largest CLS window (worst run)
     0.18366  at   421ms  html > body > main.page
     0.08567  at   852ms  html > body > header.hero, html > body > main.page
```

Read it in this order, because that is the order of yield:

1. **The ledger's `used` column.** One number over 1000% is one file, and one file is an afternoon.
2. **The LCP element line.** It is frequently not what you assumed, and everything else is wasted until it is right.
3. **The sub-part with the wrong share.** 79% render delay is not a bytes problem; it is CSS, fonts or the main thread.
4. **The CLS window's nodes and timestamps.** A shift at 421 ms sourced at `main` means something above `main` grew.
5. **Then the individual findings**, which by now you already know the shape of.

---

## Routing

| Situation | Go to |
|---|---|
| Building or restyling the system itself | `web-design-studio` |
| An inherited codebase not yet on tokens | `design-token-migration` |
| Design file and code have drifted apart | `figma-variables-sync` |
| Every state × density × theme actually renders | `component-state-matrix` |
| Copy, offer and persuasion on a landing page | `landing-page-conversion` |
| Adversarial review before a client sees it | `design-critique-gate` |
| **The page is beautiful and slow** | **here** |

Within this skill:

| You want | Read |
|---|---|
| the token vocabulary | `references/token-contract.md` |
| how to derive a budget you can defend | `references/budgets.md` §1 |
| what each budget category is for | `references/budgets.md` §2 |
| per-page-type budgets | `references/budgets.md` §3 |
| artifact budget vs experience budget | `references/budgets.md` §4 |
| why third-party gets its own line | `references/budgets.md` §5 |
| the budget file schema | `references/budgets.md` §6 |
| raising a budget legitimately | `references/budgets.md` §7 |
| lab vs field, honestly | `references/budgets.md` §8 |
| the LCP tree and the four sub-parts | `references/diagnosis.md` §§2–4 |
| CLS sources ranked by frequency | `references/diagnosis.md` §5 |
| metric-matched font fallbacks, as real code | `references/diagnosis.md` §6 |
| critical CSS and why it might not be worth it | `references/diagnosis.md` §7 |
| INP, long tasks, hydration and yielding | `references/diagnosis.md` §8 |
| which code splits help and which just move the problem | `references/diagnosis.md` §9 |
| image format, sizing, srcset, the SVG trap | `references/diagnosis.md` §10 |
| third-party containment | `references/diagnosis.md` §11 |
| pre-commit and PR wiring | `references/ci-integration.md` §§2–3 |
| keeping runtime measurement non-flaky, and the headroom argument | `references/ci-integration.md` §4 |
| adopting the gate on a site that is already slow | `references/ci-integration.md` §5 |
| reporting a regression so it gets fixed | `references/ci-integration.md` §6 |
| one command alongside `audit_design.py` | `references/ci-integration.md` §7 |

Deliberately **not** duplicated here: `font-display` tradeoffs, preloading rules, subsetting and variable-font mechanics live in `web-design-studio/references/typography.md` §8; the compositor-only rule and the property substitution table live in `web-design-studio/references/motion-system.md` §5. This skill references them and goes where they stop — into the byte budget, the gate and the measurement.

---

## The three sentences to remember

1. **The thing that is measured is the thing that gets fixed** — a suite with a design gate and no performance gate ships beautiful, tokenized, four-second pages, and every one of them passed review.
2. **Derive the number or lose the argument** — a budget that traces back to a device, a network and a target survives contact with a deadline; one that sounded strict does not.
3. **Static first, runtime second** — the deterministic layer earns the trust that the noisy layer spends, and a gate nobody trusts is a gate somebody deletes.

# Setting a Budget You Can Defend

A budget that was picked because it sounded strict gets argued away the first time it blocks a launch. A budget that was *derived* from a promise survives, because arguing with it means arguing with the promise — and the promise is a product decision somebody already made.

So this file is mostly arithmetic. **Never write a number into `perf-budget.json` that you cannot reconstruct.**

---

## 1. The derivation: from a promise to a number

Start with a sentence in this shape:

> **"The hero renders in under 2.5 seconds for three quarters of our users on a mid-tier Android phone over a slow 4G connection."**

Four decisions are hiding in it, and all four have to be made explicitly.

| Decision | This example | How to make it for real |
|---|---|---|
| **Metric** | LCP | The one the user notices. LCP for content, INP for tools. |
| **Target** | 2.5s | The Core Web Vitals "good" threshold, unless you have a reason |
| **Percentile** | p75 | CWV is assessed at p75; an average hides the tail that churns |
| **Device + network** | mid-tier Android, Slow 4G | **Look at your analytics.** Guessing here invalidates everything downstream. |

### The reference environment

Lighthouse's mobile defaults, which are the closest thing the industry has to a shared yardstick:

```
Slow 4G   1.6 Mbps down  =  204,800 bytes/s  ≈  200 KB/s
          750 Kbps up
          150 ms RTT
CPU       4× slowdown relative to the machine running the test
```

Those figures are roughly the bottom quartile of 4G and the top quartile of 3G. If your analytics say your users are on desktop broadband, **use a different profile and say so in the budget file** — the arithmetic below is a method, not a constant.

### Working backwards to bytes

```
Promise: LCP ≤ 2500 ms, mid-tier Android, Slow 4G

  DNS lookup                       1 × 150 ms  =   150 ms
  TCP handshake                    1 × 150 ms  =   150 ms
  TLS 1.3 handshake                1 × 150 ms  =   150 ms
  request → first byte     150 ms + 200 ms svr =   350 ms
  ---------------------------------------------------------
  TTFB subtotal                                    800 ms

  Target LCP                                      2500 ms
  − TTFB                                         −  800 ms
  − render, parse, decode on a 4×-slow CPU       −  300 ms
  − TCP slow-start tax on the first ~100 KB      −  150 ms
  =========================================================
  time available for critical-path bytes          1250 ms
  × 200 KB/s                                  =    250 KB
```

**250 KB is the whole critical path** — everything that must arrive before the largest element can paint. Note what the arithmetic just told you for free: the 800 ms TTFB subtotal is exactly web.dev's "good" TTFB threshold. That is not a coincidence; the thresholds were derived the same way.

Allocate the 250 KB:

| On the critical path | Budget | Why that share |
|---|---|---|
| HTML document | 25 KB | Above this you are shipping data, not markup — move it to a fetch |
| Render-blocking CSS | 30 KB | Everything needed to lay out the first viewport, and nothing else |
| One preloaded font | 25 KB | A Latin-subset woff2; preloading a second makes both slower |
| The LCP image | 150 KB | An AVIF at 2× the rendered width lands here comfortably |
| Slack | 20 KB | Because the first number you are wrong about is not the last |

Then the **whole-page** budget, which is a different question: what else can load without hurting the user after the hero has painted?

```
total page weight = critical path × 2.4 ≈ 600 KB
```

2.4× is a convention, not a derivation, and it is the one number here you should feel free to argue with. It exists because deferred bytes are not free — they compete for the same connection, the same main thread and the same data plan — but they are much cheaper than critical-path bytes.

### The same method, four other promises

| Promise | Critical path | Total |
|---|---|---|
| LCP ≤ 2.5s, Slow 4G, mid-tier Android | 250 KB | 600 KB |
| LCP ≤ 2.5s, Fast 4G (9 Mbps, 40 ms RTT) | 1.5 MB | 3 MB |
| LCP ≤ 2.5s, 3G (400 Kbps, 400 ms RTT) | 40 KB | 100 KB |
| LCP ≤ 4.0s (the "poor" line), Slow 4G | 550 KB | 1.3 MB |
| LCP ≤ 2.5s, desktop cable (5 Mbps, 28 ms RTT) | 1.2 MB | 2.9 MB |

The spread is what makes the point. **A byte budget with no device and network attached is not a budget, it is a preference.** Write the profile into the budget file as a comment and into the README, because the first question anyone asks about a number they dislike is "says who".

---

## 2. The categories, and why each one exists separately

A single total is easy to agree to and impossible to act on: when it breaks, nobody knows whose problem it is. Splitting it assigns ownership.

| Category | Default | The reasoning |
|---|---|---|
| **total** | 600 KB | The derivation above. The only number a non-engineer needs. |
| **html** | 25 KB | Server-rendered markup compresses hard. A big HTML file is almost always inlined JSON that belongs in a fetch, or a component tree that should paginate. |
| **css** | 60 KB | Enough for a real design system. Past this you are shipping a framework for four components — confirm with DevTools Coverage before cutting. |
| **js** | 170 KB | The one that always breaks. See below. |
| **image** | 300 KB | Half the page. Images are the easiest category to halve and the one most likely to be handled by someone who is not an engineer. |
| **font** | 100 KB | Two subset woff2 faces. Three families is four decisions nobody will re-litigate. |
| **media** | 0 KB | Explicitly zero so that adding an autoplaying video is a **conversation**, not a commit. |
| **other** | 50 KB | JSON, manifests, icons. Kept small so it cannot become a hiding place. |

### Why the JS number is the contentious one

JavaScript is the only category that costs twice. An image costs its download and then a cheap decode on a dedicated thread. **JavaScript costs its download, and then parse, compile and execute on the one thread that also has to render your page** — and that second cost does not improve when the user gets a better connection.

As a rough shape on a mid-tier phone, budget roughly **one second of main-thread time per 100 KB of compressed JavaScript** that actually executes on load. That is why 170 KB is already generous, and why the `tbt_ms` budget usually fails before the `js` byte budget does. Keep both: bytes are what a bundler can enforce in CI, blocking time is what the user feels.

The corollary that saves teams the most time: **code-splitting only helps if the split chunk does not load on first paint.** Moving 80 KB into a second chunk that a `useEffect` immediately imports has moved the problem, not solved it — same bytes, same execution, one extra request. `references/diagnosis.md` §9 has the test for telling the two apart.

### Request count is a separate budget

At 150 ms RTT, HTTP/2 multiplexes freely over one connection, so a 60th request to an origin you are already talking to is nearly free. **A request to a NEW origin is not**: DNS + TCP + TLS is three round trips, 450 ms, before its first useful byte. That is why the request budget in the default file is loose (50) and the third-party *origin* budget is tight (3).

---

## 3. Per-page-type budgets

A marketing landing page and a data-heavy dashboard cannot share one number, and forcing them to produces the worst of both outcomes: the landing page gets a budget it can blow through unnoticed, and the dashboard team learns to ignore a permanently-red gate.

| Page type | Dominant constraint | What moves |
|---|---|---|
| Marketing landing | LCP; a hero image is the point | image budget up, js budget **down** — it is a page of text |
| Content / article | LCP and CLS; fonts and embeds | font budget up, third-party budget tight (embeds) |
| App dashboard | INP and TBT; the data arrives after paint | js budget up, LCP target relaxed, **tbt budget tightened** |
| Checkout / form | INP; every ms is money | js tight, third-party near zero, media zero |
| Auth / interstitial | TTFB; it is one screen | everything tight; there is nothing on the page |

In `perf-budget.json`, `pages` is a map of glob patterns over a page-type name you pass with `--page-type`. Entries deep-merge onto `defaults`, so an override names only what differs:

```jsonc
{
  "$schema": "perf-budget-gate/1",
  "defaults": { "bytes": { "total": 600000, "js": 170000 },
                "lab": { "lcp_ms": 2500, "cls": 0.1, "tbt_ms": 200 } },
  "pages": {
    "marketing/*":  { "bytes": { "image": 450000, "js": 90000 } },
    "dashboard/*":  { "bytes": { "js": 420000 },
                      "lab":   { "lcp_ms": 3000, "tbt_ms": 350 } },
    "checkout":     { "bytes": { "js": 120000 },
                      "third_party": { "origins": 1, "scripts": 1 } }
  }
}
```

**Three page types is usually right. Ten is a spreadsheet nobody maintains.** If a page needs its own budget because it is genuinely unlike everything else, that is a signal worth reading on its own.

---

## 4. Budget the artifact and the experience — you need both

These are two different kinds of number and conflating them is the most common way a performance programme quietly stops working.

| | **Artifact budget** | **Experience budget** |
|---|---|---|
| Example | `js ≤ 170 KB`, `hero.avif ≤ 150 KB` | `LCP ≤ 2.5s`, `CLS ≤ 0.1`, `INP ≤ 200ms` |
| Measured by | `perf_audit.py`, in about a second | `measure_vitals.mjs`, in about a minute |
| Determinism | **Total.** Same input, same number, forever. | Variable. Same input, a different number every run. |
| Fails when | someone adds a dependency | the same, *and* when the runner is busy |
| Good at | attributing a regression to a commit | telling you whether the user is having a bad time |
| Bad at | knowing whether any of it mattered | telling you *which commit* made it worse |

**The artifact budget is the one that blocks a merge.** It is deterministic, so a red build is always a real change and never a coin toss. A team trusts it, which means a team keeps it.

**The experience budget is the one that tells you the artifact budget is aimed at the wrong thing.** A build can stay inside every byte budget for a year and still drift from a 1.8s LCP to a 3.1s one because a third-party tag got slower, a font started blocking, or the LCP element moved to something that loads late. No amount of byte counting sees that.

Run both. Gate hard on the first, gate with headroom on the second.

---

## 5. Third-party weight, budgeted separately

Third-party scripts are almost always the real villain, and they need their own line for a reason that is organisational rather than technical: **first-party bytes have an owner and third-party bytes do not.** When the JS budget breaks, a named engineer broke it in a named commit. When a tag manager ships 40 KB more this month than last, nobody did anything and nobody will fix it.

Four arguments for a separate line item:

1. **You do not control the size between deploys.** A first-party bundle changes when someone changes it. A third-party script changes whenever its vendor feels like it — so it belongs in a budget that is *checked*, not one that is *reviewed at merge*.
2. **Cost is not bytes.** A 15 KB tag that runs 300 ms of work on the main thread and injects a banner costs you TBT, INP and CLS. Its byte size understates it by an order of magnitude.
3. **Each origin is 450 ms before a single useful byte** on a 150 ms RTT connection. Origins are the unit, not kilobytes.
4. **Aggregating it into "js" hides it.** If third-party weight is inside the JS budget, every third-party addition looks like an engineering failure, so engineering learns to raise the JS budget. Splitting the line means the conversation happens with the person who wanted the tag.

The static gate budgets **origins and script count**, because that is what it can see in markup. The runtime gate measures **bytes and main-thread time by origin**, because that needs a browser. Set both:

```jsonc
"third_party": { "origins": 3, "scripts": 3 }   // static, perf_audit.py
"lab": { "tbt_ms": 200 }                        // runtime, measure_vitals.mjs
```

The containment techniques — facades, `async` with a deferred bootstrap, moving a tag server-side, and when a partytown-style worker is worth it — are in `references/diagnosis.md` §11.

---

## 6. The budget file

```jsonc
{
  "$schema": "perf-budget-gate/1",     // required, exact
  "measure": "gzip",                   // "gzip" (default) or "raw"
  "first_party_origins": ["cdn.acme.com"],   // NOT counted as third-party

  "defaults": {
    "bytes":         { "total": 600000, "html": 25000, "css": 60000,
                       "js": 170000, "image": 300000, "font": 100000,
                       "media": 0, "other": 50000 },
    "requests":      { "total": 50, "css": 4, "js": 10, "image": 20, "font": 3 },
    "largest_asset": { "image": 150000, "js": 120000, "css": 40000, "font": 40000 },
    "third_party":   { "origins": 3, "scripts": 3 },
    "lab":           { "lcp_ms": 2500, "cls": 0.1, "tbt_ms": 200,
                       "inp_ms": 200, "ttfb_ms": 800, "fcp_ms": 1800 }
  },

  "growth": { "total_pct": 5, "js_pct": 5, "image_pct": 10 },

  "pages": { "dashboard/*": { "bytes": { "js": 420000 } } }
}
```

Notes that matter:

- **`measure: "gzip"`** budgets text on its gzip -6 size, computed by `perf_audit.py` with the stdlib, because raw bytes on disk are not what crosses the wire. Already-compressed binaries (images, woff2, video) are always counted raw. Brotli ships roughly 15–20% under gzip for text, so this **over-counts slightly on purpose** — an over-count is a conversation, an under-count is a regression nobody sees.
- **`largest_asset` is not redundant with `bytes`.** A total can be met by a hundred small files or blown by one enormous one, and only the second is fixable in an afternoon. The per-asset ceiling is what turns "the page is too big" into "this file is too big".
- **`growth` is percent-per-check against the committed baseline.** It is the check that catches the regression nobody meant to make. Absolute budgets tell you that you are over; growth tells you *which change* put you over.
- **Alternate image encodings of the same stem are counted once, at the largest variant.** Shipping `hero.avif`, `hero.webp` and `hero.jpg` is correct and exactly one is ever fetched. A `srcset` *width* ladder is not collapsed, because the tool cannot know which rung a viewport picks.

---

## 7. Raising a budget legitimately

Budgets do get raised. The failure mode is not that they change, it is that they change **silently, in the commit that needed the room**, with a message like "bump budget". Six months later nobody can reconstruct what the number meant and the budget has become decoration.

**The rule: a budget change is a separate commit, reviewed on its own, by a different person than the one who needed it.**

The review asks five questions, in order:

1. **What did we buy?** Name the user-visible capability. "The new charting library" is not an answer; "customers can compare two periods on one axis, which was the top support request" is.
2. **What did we try first?** Dynamic import behind the interaction, a lighter dependency, server-side rendering of the same output, doing it in CSS. At least one must have been attempted and the result stated.
3. **Which promise changes?** If the LCP target moves from 2.5s to 3.0s, **say so in the promise**, not just in the JSON. The derivation in §1 runs again from the new target.
4. **Who else pays?** A JS increase on a shared chunk is an increase on every route that loads it. Name them.
5. **When do we look again?** A budget raised "temporarily" with no date is raised permanently. Put an expiry in the commit message and a calendar entry on it.

Then record it. A five-line entry in `PERF-BUDGET-LOG.md` beside the JSON:

```
2026-03-14  js 170KB → 210KB  (dashboard/* only)
  Bought: period-comparison charting, top support request Q1.
  Tried: dynamic import (chart is above the fold, no help);
         lighter lib (no stacked axes).
  Promise unchanged: dashboard LCP target was already 3.0s.
  Also pays: nothing — dashboard/* chunk is not shared.
  Revisit: 2026-09-14, when the vendor's v4 tree-shakes.
```

That log is the single highest-leverage artefact in this whole skill, and it is a text file.

**One thing that is not a budget increase:** adopting the gate on a codebase that is already over. That is what `--write-baseline` is for. The debt is frozen and named; the budget is not touched.

---

## 8. Lab versus field, honestly

This is the part people get wrong in both directions, so here it is plainly.

**Core Web Vitals are field metrics assessed at the 75th percentile of real page loads, segmented by mobile and desktop.** The current thresholds, verified against web.dev:

| Metric | Good | Needs improvement | Poor | What it measures |
|---|---|---|---|---|
| **LCP** | ≤ 2.5 s | 2.5 – 4.0 s | > 4.0 s | Loading — when the largest element painted |
| **INP** | ≤ 200 ms | 200 – 500 ms | > 500 ms | Responsiveness — worst interaction, outliers trimmed |
| **CLS** | ≤ 0.1 | 0.1 – 0.25 | > 0.25 | Visual stability — largest session window of shift |

INP replaced First Input Delay as a Core Web Vital on **12 March 2024**. FID measured only the input delay of the *first* interaction; INP measures the full latency (input delay + processing + presentation) of essentially the worst one, which is why a site can have had a perfect FID and a poor INP without changing a line of code.

Two supporting metrics that are **not** Core Web Vitals but are in the budget file because they diagnose:

| Metric | Good | Poor | Why it is here |
|---|---|---|---|
| **TTFB** | ≤ 0.8 s | > 1.8 s | The floor under LCP. Not a CWV — you can miss it and still pass. |
| **TBT** | ≤ 200 ms | > 600 ms | The lab proxy for INP. Only exists in a lab; there is no field TBT. |

### What a CI Lighthouse or `measure_vitals` number is good for

**Regression detection against itself.** Yesterday's median LCP on this runner with this throttle profile was 1.9s; today's is 2.6s; something in this PR did that. That is enormously valuable and it is the entire job.

### What it is not good for

- **Predicting real-user experience.** A lab run is one device, one network shape, a cold cache, no extensions, no CPU contention, no ad blocker, one geography, and one point in the page's life. Your p75 user is none of those things.
- **A pass mark.** "Lighthouse says 98" is a statement about a simulation. A site can score 100 in CI and sit at p75 LCP of 4.2s in the field because real users are on a different continent, arrive via a redirect chain, and get the variant with the video.
- **Comparing to a competitor.** Their field data is public (CrUX); their lab conditions are not yours.

### The honest statement

> **p75 field data is the thing that actually matters. Everything in this skill is a proxy for it, chosen because proxies can fail a build and field data cannot.**

Field data arrives days after the deploy that caused it; a gate has to answer in ninety seconds. So: gate on the proxy, **verify against the field**, and when the two disagree, the field is right and your lab profile is wrong. Fix the profile.

Get field data from the Chrome UX Report (free, p75, 28-day rolling, origin and URL level for popular pages), or from your own RUM using the `web-vitals` library, which is the only way to get it for pages CrUX does not cover and the only way to segment it by anything you care about.

**Set up field measurement before you tune anything.** Otherwise you will spend a quarter optimising the page your lab profile happens to describe.

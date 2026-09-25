# Diagnosis

A number tells you that something is wrong. This file tells you what.

Every entry has the same four parts, because that is the order you actually need them in:

**Symptom** — what you observed · **Mechanism** — why the browser does that · **Confirm** — how to prove it before you spend a day on it · **Fix** — what to change.

The middle two matter most. Performance work goes wrong when someone applies a fix to a mechanism that was not operating, and then cannot tell whether it helped.

---

## 1. Before anything: measure the right page in the right state

Four mistakes that invalidate everything downstream:

| Mistake | Why it ruins the measurement |
|---|---|
| Unthrottled `localhost` | A machine nobody owns. Every byte free, every CPU cost 4× understated. |
| `file://` | No network stack — TTFB ≈ 0, no resource priorities, throttling barely applies. |
| A warm cache | The visit that matters is the first one. Measure warm separately, deliberately. |
| The page you built for | Measure the page that gets traffic, in the state users see it — logged in, with the banner, with the variant. |

`measure_vitals.mjs` defaults to a cold cache and Slow 4G with 4× CPU for exactly these reasons.

---

## 2. LCP: find the element first

**Nothing else in this section matters until you know which element is the LCP element.** Half of all LCP work is spent optimising something that was never the largest paint.

LCP candidates are: `<img>`, `<image>` inside `<svg>`, `<video>` (poster or first frame), any element with a CSS `background-image` set via `url()`, and any block-level element containing text.

```bash
node scripts/measure_vitals.mjs https://example.com/ --runs 5
#   LCP element   html > body > main > section.hero > img.hero__media
```

The three surprises that come out of this, in order of frequency:

- **It is a block of text, not the image you assumed.** Then fonts and render-blocking CSS are your problem, not bytes.
- **It changes between runs.** Two candidates are close in area; whichever loads second wins. Fix both or make one clearly largest.
- **It is something absurd** — a full-bleed background `<div>`, a cookie banner, an empty skeleton box. Then you are optimising the wrong thing and the real content is painting later still.

### The four sub-parts

Once you know the element, LCP decomposes into four phases that sum to the whole. `measure_vitals.mjs` prints them with the recommended share of the total:

| Phase | Target share | What it is |
|---|---|---|
| **Time to First Byte** | ~40% | User hits enter → first byte of the HTML arrives |
| **Resource load delay** | **< 10%** | TTFB → the LCP resource *starts* downloading |
| **Resource load duration** | ~40% | The download itself |
| **Element render delay** | **< 10%** | Download finishes → the pixels are on screen |

**The two 10% phases are where the bugs live.** Load duration is mostly physics — bytes over a pipe. Load *delay* and *render* delay are pure latency you added, and they are usually the fastest thing to fix. A profile showing 60% load delay means the browser sat there knowing nothing about your hero for most of a second.

---

## 3. Phase 1 — TTFB

**Symptom:** TTFB over 800 ms; LCP cannot go below it no matter what you do to the front end.

**Mechanism:** TTFB is DNS + TCP + TLS + request + *server think time* + first byte. On a 150 ms RTT connection the handshakes alone are 450 ms before your server has heard from anyone.

**Confirm:** `performance.getEntriesByType('navigation')[0]` — `domainLookupEnd - domainLookupStart`, `connectEnd - connectStart`, `responseStart - requestStart`. The last one is your server; the others are the network.

**Fix**, in order of yield:

| Cause | Fix |
|---|---|
| Redirect chain (`http→https→www`) | Each hop is a full round trip. Collapse to one; `curl -sIL` counts them. |
| No CDN / origin far from users | Serve the **HTML** from the edge, not just the assets. Usually the biggest win. |
| Rendering on every request | Cache the HTML. Stale-while-revalidate gives a fast byte and a fresh page. |
| Uncached DB work in the handler | Profile it. TTFB is a back-end metric wearing a front-end costume. |
| No early hints | `103 Early Hints` with `Link: rel=preload` starts fetches during server think time. |

**TTFB is not a Core Web Vital.** You can miss the 800 ms line and still pass CWV. But it is the floor under LCP, so look here first when LCP will not move.

---

## 4. Phases 2 and 3 — the resource

### 4.1 The LCP image is `loading="lazy"`

**Symptom:** enormous resource load delay; the hero starts downloading hundreds of milliseconds after everything else.

**Mechanism:** a lazy image is not requested until layout has run and the browser has decided it intersects the viewport. That puts the *entire* CSS pipeline in front of your largest paint. The browser's preload scanner found the URL in the first few kilobytes of HTML and was then told to ignore it.

**Confirm:** the `loading` attribute on the element `measure_vitals.mjs` named, or `perf_audit.py`'s `lcp-lazy` finding.

**Fix:** delete the attribute. Lazy-load what is *below* the fold. This is the single most common own-goal in web performance and it is one attribute.

### 4.2 The LCP image is discovered late

**Symptom:** load delay is most of LCP, and the attribute is not `lazy`.

**Mechanism:** the preload scanner reads raw HTML bytes as they arrive, before parsing, before CSS, before any script. It can only find URLs that are literally in the markup. Anything else is discovered at the end of a chain:

| Where the URL lives | When it is discovered |
|---|---|
| `<img src>` in the initial HTML | Immediately, by the preload scanner |
| `<img data-src>` + a lazy-load library | After the library downloads, parses, executes and observes |
| CSS `background-image` | After the stylesheet downloads, parses, and matches an element in layout |
| Injected by a framework after hydration | After the whole JS pipeline |
| Behind a client-side `fetch()` | After the JS pipeline *and* another round trip |

**Confirm:** search the HTML response (`curl`, not DevTools' Elements panel, which shows the post-JS DOM) for the image URL. If it is not in `curl` output, the preload scanner never saw it.

**Fix:** put a real `<img src>` in the server-rendered HTML. When that is genuinely impossible, `<link rel="preload" as="image" fetchpriority="high" href="…">` in `<head>` restores discoverability — but a preload is a patch over a markup problem, and it goes stale silently when the image changes.

### 4.3 `fetchpriority` and the queue

**Symptom:** the image is discovered immediately and *still* starts late.

**Mechanism:** discovery is not scheduling. Images default to **Low** priority until layout proves they are in the viewport, at which point they are re-prioritised — but by then stylesheets and scripts have taken the connection.

**Fix:** `<img fetchpriority="high">` on exactly one image per page. It typically buys 100–500 ms for one attribute. Putting it on five images is the same as putting it on none.

### 4.4 preload versus preconnect — they are not alternatives

| Hint | What it does | Use for | Cost of overuse |
|---|---|---|---|
| `preconnect` | DNS + TCP + TLS, **no resource** | A critical-path origin whose URLs you do not know yet | Each connection holds resources; past 4–6 it hurts |
| `dns-prefetch` | DNS only | Origins you will probably need later | Nearly free, nearly useless alone |
| `preload` | Fetches one resource early, high priority | What the scanner cannot find: a font or hero in CSS | Preload five fonts and all five are slower |
| `prefetch` | Fetches for the *next* navigation, idle priority | The likely next page | Wasted bandwidth on a bad guess |

**`crossorigin` is mandatory on font preloads, even same-origin.** Fonts are fetched in CORS mode; without it the preload lands in a different cache partition than the `@font-face` request, the file downloads **twice**, and the preload actively costs you bandwidth in the window you were protecting.

### 4.5 Render delay — the fourth phase

**Symptom:** the resource finished and nothing painted for another 400 ms. **Mechanism:** the element cannot paint until the render tree exists — all render-blocking CSS parsed, and for text the font resolved — or the main thread is busy and cannot reach a frame. **Fix:** §7 for CSS, §6 for fonts, §8 for the main thread.

---

## 5. CLS: the sources, ranked by how often they are the answer

CLS is not "how much moved". It is the **largest session window** of layout shift: a burst of shifts less than 1 s apart, capped at 5 s, and the biggest burst is the score. Each shift scores *impact fraction × distance fraction*. Shifts within 500 ms of a user input carry `hadRecentInput` and are excluded, because the user caused them.

That definition has a consequence people miss: **one shift that moves the whole page slightly can outscore twenty small ones**, because the impact fraction is the share of the viewport affected.

| # | Source | Mechanism | Fix |
|---|---|---|---|
| 1 | **Images with no dimensions** | Zero height reserved; everything below is laid out in the wrong place and shifted when the header arrives | `width` + `height` attributes carrying the **intrinsic** size, or `aspect-ratio` in CSS |
| 2 | **Web fonts swapping** | The fallback has a different x-height, ascent and descent, so the same text occupies a different number of lines and a different block height | Metric-matched fallback — §6 |
| 3 | **Ads, embeds, iframes** | Size themselves after load, from content you do not control | Reserve the box with `aspect-ratio` on a wrapper; use the vendor's stated max size |
| 4 | **Banners injected at the top of `<body>`** | Cookie bar, promo bar, A/B wrapper prepended after first paint pushes the entire page down — distance fraction near 1.0 | Render it in the initial HTML, or `position: fixed` so it is out of flow |
| 5 | **Animating layout properties** | Every frame of a `width`/`top`/`margin` transition relayouts and moves siblings | `transform` / `opacity` — see `web-design-studio/references/motion-system.md` §5 |
| 6 | **Content injected above the fold on scroll** | Infinite scroll prepending, "new posts" banners | Insert below the current scroll position, or reserve the space |
| 7 | **`@font-face` with no `font-display`** | Defaults to `auto` ≈ `block`: up to 3 s of invisible text, then a swap | `swap` plus a matched fallback, or `optional` |

**The attributes do not fix the rendered size.** `<img width="1600" height="900">` with `.hero { width: 100%; height: auto }` renders at 100% — modern browsers turn the attributes into an intrinsic `aspect-ratio` and your CSS still wins. There is no reason not to set them.

**Confirm with the shift sources, not by watching.** `measure_vitals.mjs` prints the nodes in the largest window:

```
  Largest CLS window (worst run)
     0.18366  at   421ms  html > body > main.page
     0.08567  at   852ms  html > body > header.hero, html > body > main.page
```

A shift at 421 ms whose source is `main` means something above `main` grew. A shift at 852 ms usually means a font or a late image.

---

## 6. Metric-matched font fallbacks — the real code

This is the CLS fix that is actually a fix rather than a workaround, and it is the one most often skipped because it needs numbers you have to measure.

**Mechanism:** `font-display: swap` renders immediately in a fallback and re-renders in the web font when it arrives. The reflow happens because the two faces have different metrics — `size-adjust` corrects average character width, and the three overrides correct the vertical box. Get all four right and the swap is invisible.

```css
@font-face {
  font-family: "Geist Sans";
  src: url("/fonts/geist-sans-var-latin.woff2") format("woff2-variations");
  font-weight: 400 700;
  font-display: swap;
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+2000-206F, U+20AC, U+2122;
}

/* The fallback, re-metricked to occupy the same space as Geist Sans.
   These four numbers are per PAIR and MUST be measured, not copied. */
@font-face {
  font-family: "Geist Sans Fallback";
  src: local("Arial"), local("Helvetica Neue"), local("Liberation Sans");
  size-adjust: 104.5%;
  ascent-override: 92%;
  descent-override: 24%;
  line-gap-override: 0%;
}

:root {
  --font-sans: "Geist Sans", "Geist Sans Fallback", ui-sans-serif, system-ui,
               -apple-system, "Segoe UI", Roboto, sans-serif;
}
```

Derived from the two fonts' `head` / `hhea` / `OS/2` tables:

```
size-adjust       = (web.xAvgCharWidth / web.unitsPerEm)
                  ÷ (fb.xAvgCharWidth  / fb.unitsPerEm)  × 100%
ascent-override   = web.ascender  / (web.unitsPerEm × size-adjust) × 100%
descent-override  = web.descender / (web.unitsPerEm × size-adjust) × 100%
line-gap-override = web.lineGap   / (web.unitsPerEm × size-adjust) × 100%
```

Measure with `fontkit`, `capsize` or `fontaine`; `next/font/local` computes them for you. **Do not copy the percentages above into another project** — they are Geist against Arial, and a wrong `size-adjust` *creates* the shift it was meant to remove.

**Confirm** by measuring CLS with the web font blocked and unblocked. If blocking the font changes CLS, the metrics are wrong.

The `font-display` tradeoff table, preloading rules, subsetting and variable-font mechanics are in `web-design-studio/references/typography.md` §8 and are not repeated here.

---

## 7. CSS delivery, and the honest tradeoffs of critical CSS

**Symptom:** high render delay; FCP and LCP both late; the waterfall shows a gap with nothing happening.

**Mechanism:** every `<link rel="stylesheet">` in `<head>` blocks rendering until it is downloaded, parsed and applied. The browser will not paint an unstyled page and is right not to. `@import` is worse: it is discovered only after the *importing* sheet has downloaded and parsed, which serialises two round trips that should have been one, and the preload scanner cannot see it at all.

**Confirm:** count the render-blocking stylesheets (`perf_audit.py` reports each one past the first) and look at the gap between `responseEnd` of the last stylesheet and FCP.

**Fix, in order:**

1. **Delete CSS you do not use.** Measure with DevTools' Coverage panel against a real user journey, not a heuristic. This is the only fix with no downside.
2. **Concatenate.** One stylesheet instead of four removes three places in the queue.
3. **Split by media.** `media="print"`, `media="(min-width: 60rem)"` — non-matching stylesheets still download but do **not** block rendering.
4. **Then, maybe, critical CSS.**

### The honest case against critical CSS

Inlining above-the-fold rules in `<head>` and loading the rest asynchronously is the classic advice and it genuinely works. It also costs more than people admit:

| Cost | Detail |
|---|---|
| **It is not cacheable** | Inlined CSS ships with every HTML response. On a repeat visit you pay for it again, where a cached stylesheet is free. |
| **"Above the fold" is not one thing** | Which rules are critical depends on viewport, logged-in state, variant and route. Tools extract for one of those. |
| **It goes stale silently** | Extraction runs at build time. A component changes, the critical set does not, and you get a flash of unstyled or mis-styled content that no test catches. |
| **It inflates the HTML budget** | 14 KB of inlined CSS is 14 KB of HTML on every page load, and the HTML is the most latency-sensitive response you have. |
| **It adds a build step to maintain** | Which someone will disable when it breaks a release. |

**When it is worth it:** a high-bounce landing page, first visits dominate, the design is stable, and you have measured that render delay is actually the problem. **When it is not:** an app where users navigate repeatedly, a design under active change, or any case where you have not yet deleted the unused CSS.

The async load pattern, if you do it:

```html
<style>/* critical rules, ≤ 14KB */</style>
<link rel="stylesheet" href="/app.css" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="/app.css"></noscript>
```

---

## 8. INP: long tasks, hydration, handlers, yielding

**INP** is the latency of essentially the worst interaction on the page, in three phases: **input delay** (waiting for the main thread), **processing duration** (your handlers running), and **presentation delay** (waiting for the next frame). Good is ≤ 200 ms at p75 in the field.

**TBT is the lab proxy**, not the metric: the sum of `(duration − 50 ms)` over long tasks after FCP. It has two honest limitations — it flags blocking nobody interacted during, and it misses responsiveness problems that only appear once the page is interactive. Note also that **a long task that finishes before FCP contributes zero TBT** while being the worst thing on the page; `measure_vitals.mjs` reports total blocking time alongside TBT for that reason.

| Phase | Symptom | Mechanism | Fix |
|---|---|---|---|
| **Input delay** | Click registers late; the page "feels stuck" | The main thread is mid-task and cannot be interrupted | Break up long tasks; defer work to after first interaction |
| **Processing** | The handler itself is slow | Synchronous work in the listener — layout reads, big loops, JSON parsing | Move work off the handler; do the minimum needed to respond |
| **Presentation** | Handler is fast, screen updates late | Too much layout/paint in the resulting frame, or a huge DOM | Reduce the DOM; `content-visibility: auto` for offscreen sections |

### The four usual causes

**Hydration.** The single biggest INP source in modern apps. The server sends HTML, the framework downloads a component tree and re-walks it to attach listeners. Until that finishes, the page looks ready and does nothing — the worst possible state, because users click. Fix by shipping less client JS: server components, islands, or progressive hydration that starts with what is in the viewport.

**One long task at startup.** A 400 ms bundle evaluation blocks every interaction in that window.

**A handler that does layout work.** Reading `offsetHeight` after writing a style forces a synchronous layout; in a loop over N elements that is N layouts.

**Third-party scripts.** They run on your main thread with your privileges. §11.

### Yielding

The technique that fixes "processing duration" is to hand the thread back so the browser can paint and handle input.

```js
// Modern, correct: yields and lets the scheduler prioritise.
async function yieldToMain() {
  if ('scheduler' in window && 'yield' in scheduler) return scheduler.yield();
  return new Promise((r) => setTimeout(r, 0));
}

button.addEventListener('click', async () => {
  showPendingState();        // 1. respond IMMEDIATELY — this is what INP measures
  await yieldToMain();       // 2. let the browser paint that response
  const rows = await parseLargeThing();   // 3. then do the expensive part
  await yieldToMain();
  render(rows);
});
```

Three rules that matter more than the API choice:

- **Respond before you work.** INP ends at the next paint after the interaction. A spinner painted in 30 ms is a 30 ms INP even if the real work takes two seconds.
- **`requestIdleCallback` is for work that can wait forever**, not for splitting a task you must finish.
- **`scheduler.postTask` with `priority: 'background'`** is the right tool for genuinely deferrable work; `scheduler.yield` keeps your place in the queue where `setTimeout(0)` goes to the back.

---

## 9. JS bundles: where the weight actually goes

**Confirm first, always.** Never guess at bundle composition — every bundler emits a stats file and every one has an analyzer. Thirty seconds of `--analyze` beats an afternoon of theory.

Where the weight usually is, in the order you will find it:

| Cause | Typical size | Fix |
|---|---|---|
| A date/locale library with all locales | 60–250 KB | Swap for `Intl`, or configure the locale plugin |
| A whole icon set for nine icons | 40–300 KB | Per-icon imports, or inline SVG |
| A chart/editor/map library on a page that may not show it | 100–500 KB | Dynamic import behind the interaction |
| A polyfill bundle for browsers you do not support | 30–80 KB | Raise the browserslist target and look at the diff |
| Two versions of the same package | 2× that package | `npm ls <pkg>`, then dedupe or add an override |
| A "utils" barrel file defeating tree-shaking | varies | Import from the module, not the barrel |
| Moment/lodash-style deep imports missed | 70 KB | `lodash-es` + named imports, or drop it |

### Which splits help and which just move the problem

**The test: does the split chunk load before the first paint?** If yes, you have changed nothing except adding a request.

| Split | Helps? | Why |
|---|---|---|
| Route-based, lazily loaded on navigation | **Yes** | The user pays only for the route they are on |
| Behind a real interaction (`onClick` → `import()`) | **Yes** | Most users never trigger it |
| Below-the-fold component with an IntersectionObserver | **Yes** | Deferred past the metric window |
| Vendor chunk split out of app code | **Sometimes** | Helps *caching* across deploys; helps first load not at all |
| Component split that a top-level `useEffect` immediately imports | **No** | Same bytes, same execution, one extra round trip |
| Splitting to get under a per-chunk size lint | **No** | The lint is measuring the wrong thing |

**Caching nuance:** a vendor chunk only helps if it actually stays stable. If your bundler's hashing changes the vendor hash whenever app code changes, you are re-downloading it every deploy for nothing. Check two consecutive builds.

---

## 10. Images: format, dimensions, and the SVG trap

Three levers, in descending order of yield. Apply them in this order; teams routinely spend a week on format and ship a 4000px-wide hero.

### 10.1 Dimensions — the biggest lever

**Bytes scale with the SQUARE of linear size.** A 3000px-wide image where 1000px would do is roughly nine times the pixels. A retina display consumes **2×** the CSS width; beyond that the detail is thrown away by the downscale before it reaches a subpixel.

Ship at 2× the largest rendered CSS width, then let `srcset`/`sizes` pick per viewport:

```html
<img src="/img/hero-800.jpg"
     srcset="/img/hero-400.jpg 400w, /img/hero-800.jpg 800w,
             /img/hero-1600.jpg 1600w, /img/hero-2400.jpg 2400w"
     sizes="(max-width: 48rem) 100vw, 720px"
     width="1600" height="900" alt="" fetchpriority="high">
```

**`sizes` is the part people get wrong.** It tells the browser how wide the image will be *before CSS has loaded*, so it must describe your layout in viewport terms. Get it wrong and the browser confidently picks the wrong rung. `sizes="100vw"` on an image that renders at 320px downloads four times the bytes it needs.

### 10.2 Format

| Format | vs JPEG at matched quality | Use for |
|---|---|---|
| **AVIF** | 40–60% smaller | Everything photographic. Slower to encode; that is a build-time cost. |
| **WebP** | 25–35% smaller | The fallback for AVIF. Universally supported. |
| **JPEG** | baseline | The final fallback. Progressive, quality 70–80. |
| **PNG** | often 5–20× a JPEG for a photo | Flat colour, sharp edges, real transparency. **Never a photograph.** |
| **SVG** | — | Flat vector shapes only |

```html
<picture>
  <source srcset="/img/hero.avif" type="image/avif">
  <source srcset="/img/hero.webp" type="image/webp">
  <img src="/img/hero.jpg" width="1600" height="900" alt="">
</picture>
```

### 10.3 When an SVG is bigger than a PNG

SVG is not automatically small. It is a text description of shapes, so its size scales with **shape complexity**, not with pixel dimensions.

| SVG is smaller | PNG/AVIF is smaller |
|---|---|
| Icons, logos, flat illustration | Anything auto-traced from a raster |
| Charts with tens of elements | Gradient meshes and blur filters |
| Anything that must scale or recolour | Photographic texture |
| | Detailed maps with thousands of paths |

A 200 KB SVG is a raster in disguise. Run everything through SVGO (it strips editor metadata and rounds path precision, routinely 40–70%), and if it is still large, it wanted to be an AVIF.

**Fonts:** subset to the ranges you render and declare `unicode-range`; ship woff2 only; prefer one variable file over three static weights. The reasoning is in `web-design-studio/references/typography.md` §8.

---

## 11. Third-party containment

**Symptom:** TBT and INP are bad, first-party JS is small, and the waterfall has origins nobody recognises.

**Mechanism:** a third-party script executes on your main thread with your privileges. It can inject DOM (CLS), run long tasks (INP), add origins (3 round trips each) and change size between your deploys without a commit.

**Confirm:** group resource timings by origin and sum transfer and duration. `measure_vitals.mjs --json` gives you the resource list; a two-line reduce gives you the table. Then, for main-thread cost, a DevTools performance profile grouped by URL.

**Fix, in escalating order of effort:**

| Technique | What it costs | When |
|---|---|---|
| **Delete it** | A conversation | Always try this first. Half of all tags are for a project that ended. |
| `async` + `defer` correctly | Nothing | `async` for anything with no dependents; never a sync script in `<head>` |
| **`preconnect`** to origins on the critical path | One connection slot | 3–4 maximum; `dns-prefetch` for the rest |
| **Facade** | A little UI work | A static thumbnail that loads the real embed on click. Video, chat widgets and maps are 300 KB–2 MB each; a facade is ~2 KB. The single highest-leverage third-party fix. |
| **Self-host** | A build step, and you own updates | Fonts, always. Analytics snippets, often. Removes the whole handshake. |
| **Load after interaction/idle** | Slightly later data | Analytics does not need to run before the hero paints. |
| **Move it server-side** | Real engineering | Server-side tagging: the tag runs on your server, the user's browser never sees it. |
| **Web worker isolation** | Significant complexity, real breakage risk | Partytown-style. Only for a tag you cannot delete, cannot defer and that provably dominates your main thread. |

**The organisational fix beats all of them.** Every third-party script needs a named owner and a review date. A tag with no owner is a tag that will still be there in three years, slower.

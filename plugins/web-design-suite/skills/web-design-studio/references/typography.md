# Typography

The type system is the part of a design system users actually read. Everything else is scaffolding around a column of text. This file is the reasoning behind the `--text-*`, `--leading-*`, `--tracking-*` and `--type-*` tokens in `assets/starter/styles/tokens.css` — which are ground truth — plus the arithmetic to regenerate them with `scripts/generate_type_scale.py`. Read it before you set a single `font-size`.

## 1. Modular scales

A modular scale is one base size multiplied and divided by a fixed ratio: `size(n) = base × ratio^n`, with `n = 0` at the base and negative below it. With base 16 and ratio 1.25: 16, 20, 25, 31.25, 39.06 upward; 12.8, 10.24 downward.

The point is not purity. The point is that **the eye reads ratio, not difference**. Two sizes 4px apart look like a mistake at 16px and identical at 60px. A ratio holds the *perceived* distance between adjacent levels constant all the way up, which is what makes a hierarchy legible as a hierarchy instead of as a pile of sizes.

| Ratio | Name | Feel | Use for |
|---|---|---|---|
| 1.067 | minor second | no separation | never alone; a *down* ratio only |
| 1.125 | major second | quiet, dense | admin UI, IDE-like tools, spreadsheets |
| 1.200 | minor third | calm, workmanlike | product UI, SaaS dashboards, docs |
| 1.250 | major third | clear, confident | general web product |
| 1.333 | perfect fourth | editorial | long-form publications, blogs |
| 1.414 | aug. fourth | dramatic | landing pages, heading-led brand sites |
| 1.500 | perfect fifth | loud | display-led marketing, event sites |
| 1.618 | golden | very loud | poster-like sites, one or two levels only |

Two rules that survive contact with real projects. **The more levels you need, the smaller the ratio** — six roles at 1.5 puts a 12px label and a 91px heading on one screen. And **the bigger the ratio, the fewer steps above the base you can afford**: past about four, a ratio ≥ 1.414 stops producing headings and starts producing billboards.

### Why this skill's tokens use a dual ratio

`tokens.css` runs **1.200 at and below body sizes, 1.250 above**. One ratio cannot serve both ends:

- Below the base, sizes sit in the 11–16px band where absolute differences are tiny and rendering is quantised by hinting. A wide ratio produces unusable sizes fast (16 ÷ 1.5 ÷ 1.5 = 7.1px). You need *precision*.
- Above the base, headings compete with images, cards and whitespace. A tight ratio produces an h2 and an h3 that read as the same thing in different weights, and structure stops being perceptible. You need *separation*.

The generator implements this as `--ratio` (down) and `--dual-ratio` (up):

```bash
python scripts/generate_type_scale.py --base 16 --ratio minor-third \
  --dual-ratio major-third --steps-down 3 --steps-up 7 --snap-px --preview
```

### Where the shipped tokens deviate from pure math

`tokens.css` is a hand-finished scale, not a raw one. Be honest about it:

| Deviation | Pure math | Shipped | Why |
|---|---|---|---|
| Sub-base steps | 13.33 / 11.11 / 9.26 | 14 / 12 / 11 | Sub-16px type must land on whole pixels; 9px is unusable at any ratio |
| `--text-lg` | 16 × 1.25 = 20 | 18 | A lead-paragraph role, not a rung of the heading chain |
| `--text-5xl/6xl` maxima | ~55 / ~69 | 72 / 110 | Hand-amplified for a marketing hero (§10) |

**An override is legitimate when you can say in one sentence what it buys you.** "It felt tight" is not that sentence. Override the ratio itself when the *content* changes shape: a docs site with six heading levels drops to 1.125–1.2 above base; a brand site amplifies the top two steps only and leaves the body end alone.

## 2. The scale is closed (Law 3)

There is no `--text-15px` and there will not be one. Add a 15px between `--text-sm` and `--text-base` and the scale stops functioning:

1. **Adjacent levels become indistinguishable.** 14 → 15 is a 7% step. The eye cannot resolve it as intentional, so it reads as inconsistency — the same feeling as a misaligned edge.
2. **Roles lose meaning.** `--text-sm` meant "secondary UI text". Once 15px exists nobody knows what 15px *means*, so the next person picks by eye and the one after picks a different 15.
3. **The set stops being auditable.** You can grep a closed scale for violations. You cannot grep an open one, because every value is defensible in isolation.
4. **Theming breaks.** Density modes and re-skins re-point a known set of tokens. Sizes invented at the call site are invisible to that mechanism.

The correct response to "I need 15px" is: use 14 or 16 and change weight or color instead (§11); or fix the *container*, since a card needing 15px usually has the wrong padding or measure; or, if a rung is genuinely missing, change the ratio and **regenerate the whole scale**, then re-audit. A scale is a system. You do not patch one rung.

## 3. Leading is a function of size

Line-height and size are inversely related. Large type already has a big vertical footprint; proportional leading pushes lines so far apart the reader loses the thread back to the left margin. Small type has short glyphs and long lines, and needs generous leading so the eye does not drop a row on the return sweep.

| Context | Leading | Token |
|---|---|---|
| Long-form article body | 1.65–1.75 | `--leading-relaxed` |
| UI body copy | 1.5–1.65 | `--leading-normal` |
| Subheads, buttons, UI labels | 1.25–1.35 | `--leading-snug` |
| Headings 30–50px | 1.1–1.2 | `--leading-tight` |
| Display / hero 60px+ | 1.0–1.1 | `--leading-tight` / `--leading-none` |
| Single-line numerals, initials | 1 | `--leading-none` |

The generator uses two curves, because leading depends on line count and measure as well as size — headings are one to three lines at a narrow measure, so they can be tighter than a size-only curve predicts:

```
running text   lh = 1.10 + 8.0 / size_px    clamped to [1.45, 1.75]
headings       lh = 0.98 + 7.0 / size_px    clamped to [1.00, 1.35]
```

A step counts as a heading when `size > base × 1.25`. Fed the shipped token sizes, these reproduce every `--type-*` pairing at and above the base exactly.

**The three sub-base exceptions.** At 11–14px the running-text curve returns 1.67–1.75, but `tokens.css` pairs `--type-ui` and `--type-label` with `--leading-snug`. Both are right: a *wrapping* caption at 12px wants ~1.7; a *single-line* label, button or badge wants 1.3, because its line-height **is** the control's height — 1.75 turns a 40px button into a 52px one. The generator flags every sub-base step with `[1-line: --leading-snug]` so the call is conscious.

**Leading interacts with measure.** The return sweep is the hard part of reading: the longer the jump from line end to next line start, the more vertical separation it needs to land on the right row. Under 45ch, subtract 0.05–0.1; over 75ch, add 0.1 *and fix the measure*. If you are pushing past 1.8 to rescue a wide column, the column is the problem.

**Never set `line-height` in px.** `24px` is 1.5 on `--text-base` and 0.86 on `--text-2xl`, where lines overlap. Unitless multiplies against each element's own size and inherits correctly; a px value inherits the computed px and silently breaks every descendant of a different size. Every `--leading-*` token is unitless for this reason.

## 4. Measure

Measure is the line length of running text. The readable band is **45–75 characters**, optimum 60–68. `--measure-prose` is `68ch`; `--measure-narrow` is `48ch`.

**Why `ch`, not `px`.** `1ch` is the advance width of `0` in the *current* font at the *current* size, so a width in `ch` holds its character count when the user raises their default font size (WCAG 1.4.4), when the font falls back to a wider face mid-load, and when the same container is reused at a different `--text-*` step. `max-inline-size: 640px` is a character count for exactly one font at one size; every other combination is luck. `ch` is approximate — `0` is not the average character width, and real counts run 10–20% above the `ch` number for most sans faces — but the band is wide, and approximately inside beats exactly outside.

| Too narrow (< 45ch) | Too wide (> 75ch) |
|---|---|
| Fragments mid-phrase, breaking syntactic units | The return sweep loses its row |
| Hyphenation and rivers; jagged rag | Reader re-reads or skips lines |
| Constant refixation; reading speed drops | Fatigue; the page reads as a wall, so nobody starts |

| Context | Target | Token |
|---|---|---|
| Article / body copy | 60–70ch | `--measure-prose` |
| Card body | 40–50ch | `--measure-narrow` |
| Caption, photo credit | 35–45ch | `--measure-narrow` |
| Form help text | 40–50ch | `--measure-narrow` |
| Sidebar / aside | 35–45ch | `--measure-narrow` |
| Tooltip | 30–40ch | `--measure-narrow` |
| Table cell | unconstrained | set column widths instead |

Measure is a *spacing* decision, which is why these tokens live in the spacing section of `tokens.css`, not the type section.

## 5. Optical tracking

Type designers fit spacing for one size, typically text sizes. Scale that fitting up and the gaps scale with it, so display type sets too loose; scale it down and gaps shrink below the point where the eye separates glyphs, so small type sets too tight. Tracking corrects for this and nothing else.

| Band | Tracking | Token |
|---|---|---|
| Display 44px+ | −0.03em | `--tracking-tighter` |
| Headings 22–35px | −0.015em | `--tracking-tight` |
| Body 14–20px | 0 | `--tracking-normal` |
| Small UI 11–13px | +0.02em | `--tracking-wide` |
| Uppercase runs, any size | +0.08em | `--tracking-caps` |

Uppercase gets its own rule because capitals are fitted to sit inside lowercase runs, not beside each other; an all-caps string at default tracking reads as a solid block. That is a *case* decision, not a size decision, so it composes on top — a 12px uppercase eyebrow takes `--tracking-caps`, not `--tracking-wide`.

### The heuristic, honestly

Tracking against size fits the family `ls = B / size_px + A`: steep correction at small sizes, asymptotic at display sizes. The constants quoted around the web are `ls ≈ 0.35 / size_px − 0.0055`. **Verify before trusting it.** Run it: +0.016em at 16px, +0.010em at 22px, +0.0025em at 44px, and it does not cross zero until ~64px. That is loose body, loose headings, and effectively no display correction — it disagrees with this skill's tokens at every heading size. It is calibrated for a face with far looser default fitting than a modern grotesque, and it is not usable here as written.

Refitting the same family to the token bands gives the default the generator ships:

```
ls_em ≈ 0.605 / size_px − 0.0378      clamped to [−0.04, +0.03]
```

This reproduces **every** band exactly: +0.017em @ 11px, +0.013 @ 12, +0.005 @ 14, 0 @ 16, −0.010 @ 22, −0.016 @ 28, −0.021 @ 35, −0.024 @ 44, −0.027 @ 56. Both models ship as `--tracking-model {studio,classic}` so you can see the disagreement yourself.

Treat either as a **starting point, not a truth.** A curve knows nothing about the face you actually loaded: generous sidebearings need less negative tracking at display sizes, a condensed face needs more. The curve gets you to the right token in one step; your eyes confirm it.

**Never letter-space lowercase running text.** Negative tracking closes the counters and destroys word-shape recognition, which is what reading speed depends on; positive tracking pulls words apart into letters. The generator enforces this by flooring running-text steps at 0.

## 6. Vertical rhythm and the heading-space rule

**Space above a heading is larger than space below it.** A heading belongs to what follows, not to what it follows. Symmetrical spacing leaves it floating between two blocks and the reader cannot tell which section it introduces. Proximity is a stronger grouping signal than size, weight or color, so symmetrical spacing actively fights the hierarchy the heading exists to create.

| Element | Space above | Space below | Ratio |
|---|---|---|---|
| `h2` (section) | `--space-subsection` (40→88px) | `--gap-related` (12px) | 3:1 → 7:1 |
| `h3` (subsection) | `--gap-distinct` (40px) | `--gap-related` (12px) | ~3:1 |
| `h4`–`h6` (minor) | `--gap-separate` (24px) | `--gap-related` (12px) | 2:1 |
| `p` → `p` | `--space-block` (24→48px) | — | — |

Aim for **at least 2:1**, and more as the heading grows.

The rhythm is layout.css's, shared by `.prose` and `.flow`:

<!-- snippet: layout.css#flow -->
```css
:is(.flow, .prose) {
  --flow-gap: var(--space-block);
}
:is(.flow, .prose) > * + * { margin-block-start: var(--flow-gap); }

/* A heading belongs to the thing it introduces: far from what came before,
   scaled to its rank, and close to what follows. Proximity does the work a
   horizontal rule would otherwise do. Above to below is at least 2:1 at
   every width: h2 40→88 : 12, h3 40 : 12, h4 24 : 12. */
:is(.flow, .prose) > * + h2 { margin-block-start: var(--space-subsection); }
:is(.flow, .prose) > * + h3 { margin-block-start: var(--gap-distinct); }
:is(.flow, .prose) > * + :is(h4, h5, h6) { margin-block-start: var(--gap-separate); }

/* Written after the heading rules, at equal specificity, so a heading that
   follows a heading takes this tight gap too: two stacked headings are a
   title and its subtitle, not two sections. */
:is(.flow, .prose) > :is(h1, h2, h3, h4, h5, h6) + * {
  margin-block-start: var(--gap-related);
}

/* An <hr> means "the subject changes": subsection weight on both sides. */
:is(.flow, .prose) > * + hr,
:is(.flow, .prose) > hr + * { margin-block-start: var(--space-subsection); }
```

The headings inside long-form text, beside `.prose` in layout.css (its one home):

```css
@layer layout {
  .prose > :is(h2, h3, h4) { color: var(--fg-strong); }
  .prose > h2 { font: var(--type-h2); letter-spacing: var(--tracking-tight); }
  .prose > h3 { font: var(--type-h3); letter-spacing: var(--tracking-tight); }
  .prose > h4 { font: var(--type-h4); }
}
```

Note what is **not** there: no `margin-block-end` anywhere, and no margin on the first child. `.prose` has zero outer margin in both block directions, so a parent places it with `gap` like any other child.

### Why this does not violate Law 2

Children here set `margin-block-start`, which looks like a Law 2 violation and needs a real justification, not a shrug. It holds because the rule is written **by the container, about its own descendants, in the container's own file**. `.prose` is a single owned context, not a component boundary:

- **The children are anonymous.** They come from Markdown, a CMS or an editor. They have no component identity and no stylesheet of their own, so there is no second owner to conflict with.
- **The gap is pair-dependent**, which is the part `gap` cannot express. Flex and grid `gap` is uniform; prose needs 12px *after* an `h2` and 88px *before* one. That relationship requires the sibling combinator.
- **Switching to `display: flex` to get `gap` costs more than it buys**: margin collapsing in nested lists, float-based figures, `text-wrap: pretty` across block boxes, and every editor plugin that assumes normal flow.
- **The boundary stays clean.** No `margin-block-end`, first child at zero ⇒ nothing escapes. The *component* still sets no outer margin; only its private internals do.

**This is the only place the trailing-margin idiom is acceptable.** The moment a child has its own component file — a `.card`, a `.btn`, a `.stat` — it is back under Law 2 and sets no outer margin at all. A stack of cards is spaced by the parent's `gap`, never by the card.

## 7. Font pairing

Two faces work together when they are clearly **different in skeleton** and clearly **compatible in proportion**. Two humanist sans faces give neither: the reader registers a mismatch without being able to name it. Check structure first — axis (vertical vs angled stress), terminals (sheared, horizontal, flared), aperture, and thick/thin contrast. **If two faces agree on three of those four, they are too close to pair.** Contrast in structure, not merely in style.

| Pairing | Display / headings | Body | Reads as |
|---|---|---|---|
| Geometric sans + humanist serif | Poppins, Futura, Geist | Source Serif, Charter | Modern brand, warm reading |
| Grotesque + mono | Inter, Geist | — (mono for data/code) | Precise, technical |
| Humanist serif + grotesque | Freight, Tiempos | Inter, Geist | Editorial, authoritative |
| One superfamily | Recursive, IBM Plex, Source | same family | Cohesive, cheapest to ship |

**A superfamily is the default answer.** Sans, serif and mono cuts from one family give contrast in structure with guaranteed matching metrics, one vendor, one licence, often one variable file. Reach for a second family when the brand needs a voice the superfamily cannot produce — not because two families look more designed.

**The ceiling is two families plus one mono.** Three families is almost always one family and two opinions. Each extra family costs a request, a CLS risk, a fallback-metrics problem and a decision the team re-litigates on every new component.

**Match x-height and cap-height.** Perceived size is driven by x-height, not em size, so two faces at the same `font-size` do not look the same size. Set them side by side and compare the lowercase `x`: if the body face runs smaller it will read weaker than its size suggests — nudge it up one *existing* step, or set the heading face down one, never invent an intermediate (Law 3). Compare cap-height too, because it governs alignment against icons, avatars and buttons; mismatched cap-heights show up as optical misalignment in every horizontal row. Check the mono separately — monospace faces usually run large, which is part of why `--type-code` uses `--text-sm` against 16px body.

## 8. Web font loading

Every web font is a race between the text and the file. You decide what the reader sees while it runs.

| `font-display` | Block | Swap | Use when |
|---|---|---|---|
| `swap` | ~0ms | infinite | Body and headings — readable immediately; the swap is the cost |
| `optional` | ~100ms | none | Anything you would rather drop than reflow |
| `fallback` | ~100ms | ~3s | Middle ground; rarely clearly right |
| `block` | ~3s | infinite | Icon fonts only, and you should not use an icon font |
| `auto` | UA default | — | Never; you have decided nothing |

Default to `swap` and kill the reflow with metric-matched fallbacks. `optional` is the strongest choice for content-heavy sites: zero layout shift, at the cost of some visitors never seeing the brand face on first load. That is a business decision, not a CSS one.

**Preload only the faces used above the fold** — usually one, the body weight of the sans. Preloading five makes all five slower. `crossorigin` is mandatory even same-origin, because fonts are fetched in CORS mode and without it the file downloads twice.

```html
<link rel="preload" href="/fonts/geist-sans-var-latin.woff2" as="font"
      type="font/woff2" crossorigin>
```

**Subset, and declare `unicode-range`** so the browser downloads only the ranges a page needs. Woff2 only; woff1, TTF and EOT are dead weight.

**Variable fonts.** One variable file usually beats three static weights on bytes and removes faux-bold risk entirely. Declare the axis range with `font-weight: 400 700`. The distinction that bites people:

- `font-weight: 600` is the high-level property. It inherits, animates, composes with `font-synthesis`, and maps to `wght` automatically. **Use this.**
- `font-variation-settings: "wght" 600` is the low-level escape hatch and **does not compose**: setting it replaces *all* axis values, so a child that sets `"opsz" 32` silently resets `wght` to the file default. It also does not interact with `font-weight`, and the low-level one wins.

Use `font-variation-settings` only for axes with no high-level property (`GRAD`, custom axes), and set every axis you care about in that one declaration.

```css
/* Wrong: the child resets weight to the file default. example: wrong */
.card        { font-variation-settings: "wght" 600; }
.card__title { font-variation-settings: "opsz" 32; }
```

```css
/* Right: high-level for wght, low-level only for what has no property. */
.card        { font-weight: var(--weight-semibold); }
.card__title { font-variation-settings: "opsz" 32; }
```

**Self-host.** A third-party font CDN costs a DNS lookup, a TCP handshake and a TLS negotiation before the first byte; cross-site cache partitioning killed the shared-cache argument years ago; and you inherit someone else's uptime and privacy posture for a file that never changes. Serve the woff2 from your own origin behind `Cache-Control: max-age=31536000, immutable`.

### Eliminating CLS from metric mismatch

The swap reflows because the fallback has different x-height, ascent and descent, so the same text occupies a different number of lines and a different block height. Declare a *re-metricked* fallback and slot it between the web font and the generic stack:

```css
@font-face {
  font-family: "Geist Sans";
  src: url("/fonts/geist-sans-var-latin.woff2") format("woff2-variations");
  font-weight: 400 700;
  font-display: swap;
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+2000-206F, U+20AC, U+2122;
}

/* The fallback, re-metricked to occupy the same space as Geist Sans.
   These four numbers are per-pair and MUST be measured, not guessed. */
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

Measure with `fontkit`, `capsize` or `fontaine`; `next/font/local` computes them for you. **Do not copy the percentages above into another project** — they are specific to Geist against Arial, and a wrong `size-adjust` creates the shift it was meant to remove. Verify with a Performance-panel layout-shift recording on a throttled connection, not by eye.

## 9. OpenType features worth turning on

**Tabular numerals are non-negotiable in data.** Proportional figures have per-digit widths, so a column jitters and cannot be scanned. Any number that sits in a column, updates in place, or is compared to another number gets them.

```css
.table__cell, .stat__value, .timer, .price {
  font-variant-numeric: tabular-nums lining-nums;
  font-feature-settings: "tnum" 1, "lnum" 1;   /* legacy engines only */
}
```

Prefer `font-variant-numeric` over `font-feature-settings`. The former composes — `tabular-nums` and `slashed-zero` can be set in different rules and both apply. The latter replaces the *entire* feature list per declaration, so a later rule setting `"ss01" 1` silently turns `tnum` off. Same trap as `font-variation-settings` (§8). Also worth knowing: `oldstyle-nums` for serif running prose, `slashed-zero` for IDs and codes read aloud or transcribed, `diagonal-fractions` for recipes and specs.

**Ligatures.** Leave standard ligatures on in headings and body — they exist to fix the `fi`/`fl` collision and their absence is visible. `discretionary-ligatures` is a display-only flourish; a `ct` swash in a button label is noise. For code, default to **off**: coding ligatures (`=>` → `⇒`) help readers who know them, mislead readers who do not, and break character alignment in diffs. Let developers opt in in their own editor.

```css
@layer base {
  code, pre, .code {
    font: var(--type-code);
    font-variant-ligatures: none;
    font-variant-numeric: tabular-nums slashed-zero;
  }
}
```

**`text-rendering: optimizeLegibility` is cargo cult.** It is an SVG property that browsers map to "enable kerning and standard ligatures" — already on by default everywhere current — with a history of pathological layout cost on long documents and dropped glyphs on some Android builds. Do not ship it; use `font-kerning: normal` and `font-variant-ligatures` if you need explicit control. `geometricPrecision` has one real use: text inside SVG or animated transforms, where hinted rounding causes visible jitter while scaling.

## 10. Fluid type

Two anchors, a straight line between them, flat outside them:

```
anchors (vw₁, s₁) and (vw₂, s₂), all px

  m = (s₂ − s₁) / (vw₂ − vw₁)     px of size per px of viewport
  c = s₁ − m · vw₁                 px of size at viewport 0
  size(vw) = m · vw + c

CSS renders m as a vw unit (m × 100) and c in rem (c ÷ 16):
  clamp(s₁rem, c_rem + (m×100)vw, s₂rem)
```

Worked, for a display step running 44px at 380px wide to 72px at 1440px:

```
m = (72 − 44) / (1440 − 380) = 0.026415   → 2.642vw
c = 44 − 0.026415 × 380 = 33.962px        → 2.1226rem

--text-5xl: clamp(2.75rem, 2.1226rem + 2.642vw, 4.5rem);
```

`generate_type_scale.py --fluid 380 1440` emits exactly this with the algebra in a comment beside it. **The intercept must be in `rem`, not `px`:** a pure-`vw` middle term ignores the user's font-size preference entirely and fails WCAG 1.4.4.

**The shipped tokens hold to this.** Every fluid step in tokens.css, spacing and type, is solved for 380→1440: put its `c` and `m` back into `size(vw)` and it reaches its minimum at 380px and its maximum at 1440px. The suite's tests solve each one on every change, because a clamp whose intercept is a little low still looks plausible, and meets its bounds 20px late. One anchor pair per file: two pairs is how a system drifts.

**Fluid is right for** display and hero type (110px is right on a 27" monitor and absurd on a 390px phone — this is the whole use case), section headings that would otherwise need two breakpoints, and page-level gutters and section rhythm.

**Fluid is wrong for body copy.** 16px is the minimum comfortable reading size on a phone and still correct on a desktop, because reading distance grows with screen size roughly in step. What should change with viewport is the *measure*, not the size. Fluid body also re-wraps every line continuously during resize, which looks unstable and defeats `text-wrap: balance`. It is equally wrong for **UI labels, buttons, inputs and table text**, which are sized against touch targets (`--tap-min`), icon sizes and control heights — all fixed; a fluid label desynchronises from the 44px target it sits inside. And it is wrong **inside any resizable panel**, because `vw` tracks the viewport, not the container: a fluid heading in a split-pane editor is sized by the browser window. Use container queries there.

Rule: **fluid above `--text-3xl`, fixed at and below it.**

## 11. Hierarchy without size

Size is the most expensive hierarchy tool — it consumes vertical space, forces reflow decisions, and a scale has only so many rungs. Four other axes are free:

| Axis | Tokens | Strength | Notes |
|---|---|---|---|
| Space | `--gap-*` ladder | Strongest | Proximity beats every other grouping cue |
| Weight | `--weight-regular` → `--weight-bold` | Strong | Two steps to register (400→600, not 400→500) |
| Color | `--fg-strong` / `--fg-default` / `--fg-muted` | Strong | Must pass contrast; never the only signal |
| Case | uppercase + `--tracking-caps` | Medium | Eyebrows and section labels; never body |
| Tracking | `--tracking-*` | Weak | Supports other axes; too subtle to carry a level |

**A hierarchy level must differ from its neighbours on at least two axes.** One axis is ambiguous: a heading that is only *bigger* reads as emphasis rather than structure, and disappears entirely for anyone who has overridden your font sizes. Two survive both. Working combinations:

- Size + weight — `--text-2xl` at `--weight-semibold` over `--text-base` at 400.
- Weight + color — `--weight-semibold` + `--fg-strong` over 400 + `--fg-muted`, with **no size change**. This is how you build a card title that does not tower over its own body.
- Case + tracking + color — an eyebrow at `--text-xs`, uppercase, `--tracking-caps`, `--fg-muted`. *Smaller* than the body and unmistakably a different level.

This is why `--type-*` roles are composite `font` shorthands: each bundles size, weight, leading and family, so a level can never be defined by one axis by accident.

## 12. Accessibility

| Requirement | What it means for type | WCAG |
|---|---|---|
| Body ≥ 16px | `--text-base` is the floor for reading copy; sub-16px forces mobile zoom and triggers iOS input auto-zoom | practice |
| Resize to 200% | All content and function available with text at 200% — achieved by sizing in `rem`/`ch`, never `px` | 1.4.4 AA |
| Reflow at 320px | No horizontal scroll at 320 CSS px (= 1280px at 400% zoom): single column, `max-inline-size` in `ch` | 1.4.10 AA |
| Text-spacing overrides | Content survives user-applied line-height 1.5×, paragraph spacing 2×, letter-spacing 0.12em, word-spacing 0.16em | 1.4.12 AA |
| Never disable user font size | No `user-scalable=no`, no `maximum-scale=1`, no `px` root font size | 1.4.4 AA |
| Avoid text in images | Image text does not scale, reflow, restyle, translate or get read aloud — use SVG text or real text over the image | 1.4.5 AA |

**Pass 1.4.12 by construction.** It is the criterion that catches fixed-height components: a user stylesheet forcing `line-height: 1.5` on a button whose height you fixed at 40px clips the label. Give controls `min-block-size`, never `block-size`; let padding and line-height determine height; never combine a fixed height with `overflow: hidden` on text. `--leading-normal` is already 1.6, so body copy passes unchanged — it is the *components* that fail this.

**Heading level and visual size are separate decisions.** Heading elements carry document structure for screen readers, which navigate by level.

- **Fine:** an `<h3>` styled with `--type-h2` because it is visually prominent. Structure intact, appearance adjusted.
- **Not fine:** skipping `<h2>` to `<h4>` because h4 "looked right" — that tells a screen reader a level is missing.
- **Not fine:** a `<div class="heading">`; it has no level and never appears in the heading list.
- **Not fine:** an `<h2>` used because you wanted big text in a card. Use a `<p>` with `--type-h2` if it is not a section heading.

```css
/* <h3 class="section__title">Pricing</h3> — structure from the tag,
   appearance from the role token. */
.section__title { font: var(--type-h2); letter-spacing: var(--tracking-tight); }
```

## 13. Anti-patterns

| Anti-pattern | Why it fails | Instead |
|---|---|---|
| Justified text on the web | No line-breaking or hyphenation engine worth the name; rivers and 3-space gaps under ~80ch | `text-align: start` + `text-wrap: pretty` |
| All-caps body copy | Removes the ascender/descender word shapes fluent readers rely on; measurably slower | Sentence case; caps for eyebrows only |
| Body copy under 16px | Forces pinch-zoom; triggers iOS input auto-zoom; fails anyone over 40 | `--text-base` minimum |
| `line-height` in px | Does not scale with inherited size; overlapping lines on larger descendants | Unitless `--leading-*` |
| Letter-spacing on lowercase body | Breaks word-shape recognition in both directions | `--tracking-normal` |
| More than 3 weights in one product | Each is a file, a CLS risk and a recurring decision | Three of the four `--weight-*` tokens, at most |
| `font-size` on the element | Invisible to theming, density and audit; this is how a 15px appears | Compose a `--type-*` role |
| `font-size: 15px` "just once" | Opens the closed scale (§2) | An existing rung, or weight/color (§11) |
| Faux bold with no bold face | The engine algorithmically smears the regular | Ship the weight, or `font-synthesis: none` to expose the gap |
| `text-transform: uppercase` alone | Capitals are fitted for use inside lowercase; they crowd | Always pair with `--tracking-caps` |
| Fluid body copy | Re-wraps on every resize; dilutes the user's zoom | Fixed size, fluid measure (§10) |
| Symmetrical heading spacing | Heading floats; hierarchy stops reading | Above ≥ 2× below (§6) |
| `text-rendering: optimizeLegibility` | Enables what is already on; costs layout; drops glyphs on some Android | `font-kerning` / `font-variant-ligatures` |

## 14. Worked example: one token file, two products

Both import the **same** `tokens.css`. Nothing in the type scale changes. What changes is the **density dial** and **which roles get used**.

| Slot | Marketing (`data-density="spacious"`) | Dashboard (`data-density="compact"`) |
|---|---|---|
| Top level | `--type-display` — 700, 56→110px | `--type-h3` — 600, 28px |
| Secondary | `--type-lead` — 400, 18px, 1.6 | `--type-h4` — 600, 22px |
| Dominant body | `--type-body` — 16px | `--type-ui` — 500, 14px, 1.3 |
| Small text | eyebrow: `--type-label` + caps | table header: `--type-label` + caps |
| Measure | `--measure-prose` (68ch) | none — column widths instead |
| Numerals | default | `tabular-nums` throughout |
| `--density` | 1.125 — every gap and pad grows | 0.875 — everything tightens |

```css
@layer components {
  /* Marketing */
  .hero__title {
    --hero-title-measure: 18ch;       /* Tier 3: a display measure is much shorter */
    font: var(--type-display);
    letter-spacing: var(--tracking-tighter);
    max-inline-size: var(--hero-title-measure);
    text-wrap: balance;
  }
  .hero__sub {
    font: var(--type-lead);
    color: var(--fg-muted);
    max-inline-size: var(--measure-narrow);
  }
  .eyebrow, .table__head {
    font: var(--type-label);
    text-transform: uppercase;
    letter-spacing: var(--tracking-caps);
    color: var(--fg-muted);
  }

  /* Dashboard */
  .table__cell {
    font: var(--type-ui);
    font-variant-numeric: tabular-nums lining-nums;
    padding: var(--pad-block-sm) var(--pad-inline-sm);
  }
  .stat__value {
    font: var(--type-h2);
    font-variant-numeric: tabular-nums;
    letter-spacing: var(--tracking-tight);
  }
}
```

**Density did not change a single font size.** `--density` multiplies spacing only (Law 7). A compact dashboard gets tighter by removing *air*, not by shrinking text — which is exactly right: 14px UI text at 0.875 density is still 14px and still legible, while 14px text in a 14px-padded cell is a wall. Reaching for a smaller `--text-*` step is the wrong lever, and reaching below `--text-sm` for anything but metadata is a bug.

## 15. Audit before it ships (Law 9)

- [ ] No `font-size` literal outside `tokens.css` — `grep -rn "font-size:\s*[0-9]" src/`
- [ ] Every text element composes a `--type-*` role, not loose properties.
- [ ] No size between two rungs. `line-height` unitless everywhere — `grep -rn "line-height:.*px" src/`
- [ ] Body ≥ 16px; nothing under 11px exists at all.
- [ ] Every running-text container has a 45–75ch measure.
- [ ] Space above each heading ≥ 2× the space below.
- [ ] No component sets outer margin; `.prose` is the only owl, with no `margin-block-end` and no margin on its first child.
- [ ] Uppercase runs carry `--tracking-caps`; lowercase body carries 0.
- [ ] Fluid only above `--text-3xl`; every clamp middle term has a `rem` intercept.
- [ ] Numeric columns use `tabular-nums`.
- [ ] Fallback `@font-face` has *measured* overrides; CLS verified on a throttled connection, not by eye.
- [ ] At most 2 families + 1 mono; at most 3 weights.
- [ ] Heading levels sequential in the DOM regardless of visual size.
- [ ] Passes at 200% zoom; reflows at 320 CSS px; survives the 1.4.12 text-spacing bookmarklet with no clipping.
- [ ] `--density` toggled to `compact` and `spacious`: nothing overlaps, nothing clips, no text size changed.

Regenerate with `--format css|json|ts|tailwind`; `--preview` prints the table first. The script's leading and tracking heuristics are the ones in §3 and §5, with the same constants. **If you change one, change the other** — a reference that disagrees with the generator is worse than none, because someone will believe it.

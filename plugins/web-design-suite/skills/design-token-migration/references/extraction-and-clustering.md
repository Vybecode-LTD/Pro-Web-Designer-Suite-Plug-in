# Extraction and Clustering

How to find every hardcoded value in a codebase you did not write, and how to work out which of them are the same decision.

This is the method behind `scripts/extract_literals.py` and `scripts/cluster_values.py`. Read it before you defend a clustering result to a designer, because you will have to, and "the script said so" is not a defence.

## Contents

1. [Why extraction is harder than grep](#1-why-extraction-is-harder-than-grep)
2. [Where literals hide, per source shape](#2-where-literals-hide-per-source-shape)
3. [What must never be counted](#3-what-must-never-be-counted)
4. [Classifying a literal by kind](#4-classifying-a-literal-by-kind)
5. [Clustering spacing](#5-clustering-spacing)
6. [Clustering color](#6-clustering-color)
7. [Clustering type](#7-clustering-type)
8. [Clustering shadows](#8-clustering-shadows)
9. [Clustering durations, easings and z-index](#9-clustering-durations-easings-and-z-index)
10. [The hard cases](#10-the-hard-cases)
11. [The consolidate-vs-separate decision rule](#11-the-consolidate-vs-separate-decision-rule)
12. [The report format](#12-the-report-format)

---

## 1. Why extraction is harder than grep

`grep -r '[0-9]\+px'` gets you a number. It is the wrong number, in four directions at once:

| Failure | Example | Consequence |
|---|---|---|
| Counts prose | `/* 13px grid, see ADR-4 */` | Estimate inflated; a codemod built on it corrupts comments |
| Counts data | `url(hero-13px-grid.png)`, `content: "12px"` | Same, plus a broken image path if anything replaces it |
| Misses context | `1px` in `border-radius` vs in `gap` | One migration turns your corners into your padding |
| Misses whole dialects | `style={{marginTop: 13}}`, `` styled.div`padding: 13px` ``, `p-[13px]` | In a modern React app this is most of them |

The unit of extraction is not a *string*. It is a **(property, value, position, file-role) tuple**, because every downstream decision depends on the property. `13px` as a `gap` is a proximity decision and maps to the ladder. `13px` as a `border-radius` maps to the radius scale. `13px` in `font-size` maps to a type role. Three different answers, one string.

---

## 2. Where literals hide, per source shape

### Plain CSS, SCSS, LESS, PostCSS

Scan declarations, not lines. A declaration is `prop : value` terminated by `;` or `}` at brace depth ≥ 1 and paren depth 0. Track the selector stack so you know whether you are inside `@media`, and track the block offset so you can later ask "what else does this rule set?" — which is what makes the `font:` shorthand rewrite safe.

Also capture **preprocessor variable declarations**: `$brand: #2f6df6`, `@line: #e5e5e5`. These are not tokens, however much they look like them. A SCSS variable is compile-time text substitution with no runtime identity: it cannot be re-pointed by a theme, cannot be read by JS, cannot be overridden per-subtree, and does not appear in the browser at all. Treat it as a literal with a name attached — because that is exactly what it is — and migrate it to a custom property.

Capture `darken()` / `lighten()` / `mix()` calls separately, as kind `color-function`. They are not values; they are values the compiler has not computed yet. `darken($brand, 8%)` is a ramp step nobody wrote down.

### CSS Modules

Byte-identical to CSS. The only difference is that `.module.css` marks the file as a **component file**, where Laws 2, 4 and 6 apply and where a Tier-1 token is a violation rather than a style. That flag has to ride along on every record, because it changes what the proposal is allowed to suggest.

### styled-components and Emotion

Find the tagged template — `` styled.div` ``, `` styled(Foo).attrs({...})` ``, `` css` ``, `` createGlobalStyle` ``, `` keyframes` `` — then scan its body as CSS, at the right offset so line numbers still point at real lines.

Blank out `${...}` interpolations first. They are JavaScript, not CSS, and a scanner that reads `${(p) => p.pad}px` as a declaration invents a property called `p`. Blanking (replacing with spaces) rather than deleting keeps every offset true.

An interpolation that *holds* a literal — `` background: ${tones.error}; `` with `tones.error = '#d64545'` elsewhere — is found by the JS-string sweep instead, and correctly reported as a color constant in JavaScript rather than a CSS value.

### JSX inline styles

`style={{ … }}`, brace-matched, parsed as an object literal. Three value shapes, three behaviours:

```jsx
// example: illustration — the three value shapes the census reads
style={{ marginTop: 13 }}            // bare number: React appends px → "13px"
style={{ padding: '11px 15px' }}     // string: parse as a CSS value, both slots
style={{ zIndex: 10 }}               // React does NOT append px here
```

The unitless set matters: `z-index`, `opacity`, `flex`, `order`, `line-height`, `font-weight`, `column-count`, `grid-row`, `aspect-ratio` and friends take bare numbers that are not lengths. Appending `px` to those produces a phantom spacing value and an estimate nobody can reproduce.

Keys are camelCase and must be kebab-cased before the property lookup. Spreads and computed keys are skipped: they are not literals, and guessing at them is how a codemod corrupts JSX.

### Tailwind arbitrary values

`p-[13px]`, `text-[#3a3a3a]`, `duration-[350ms]`, `max-w-[1140px]`. Sweep `className=` attributes *and* bare strings, because `clsx('px-[13px]', cond && 'mt-[7px]')` and `cva({ variants: … })` keep their classes in ordinary string literals.

Underscores are Tailwind's space escape: `shadow-[0_1px_3px_rgba(0,0,0,0.08)]` is a four-slot shadow. Convert `_` to a space before parsing.

Skip the prefixes that are not design values: `grid-cols-[…]`, `aspect-[…]`, `content-[…]`, `data-[…]`, `aria-[…]`, `supports-[…]`. A grid track list is layout structure, not a token.

### Hex colors in JS strings

```js
const HEADER_BG = '#f5f5f4';
const tones = { error: '#d64545' };
```

Report them, but as a separate context. They cannot be codemodded into `var()` — a color in JS is a color dark mode cannot re-point, and fixing it means moving the decision into CSS, not rewriting the string. Skip anything on a line mentioning `href`, `hash`, `sha`, `commit` or `id=`: those `#` are fragments, not colors.

---

## 3. What must never be counted

| Source | Why |
|---|---|
| Comments | Prose. Counting them inflates the estimate and a codemod built on it rewrites documentation |
| Quoted strings | `content: "12px"` is a label. `font-family: "Segoe UI"` is a name |
| `url(...)` bodies | Filenames. `hero-13px-grid.png` contains `13px` and no decision |
| `tokens.css` / `theme.css` | The destination. Literals there are the point |
| Vendor / third-party stylesheets | You layer them; you do not migrate them. See `framework-migrations.md` §6 |
| Generated files | `@generated`, `DO NOT EDIT` — audited against their source, not by hand |
| `node_modules`, `dist`, `build`, `.next`, `coverage` | Not source |

The blanking technique matters: replace comment and string bodies with **spaces**, preserving every newline and every byte offset. Stripping them shifts offsets, and every record in the census carries a `file:line` that a human is going to open. One wrong line number and nobody trusts the inventory, and an untrusted inventory does not get funded.

---

## 4. Classifying a literal by kind

Property first, value shape second. The property is authoritative because the same string means different things in different slots.

| Kind | Decided by | Maps onto |
|---|---|---|
| `length` | property ∈ spacing/size set | The closed 4px scale → proximity ladder or inset roles |
| `radius` | property ∈ radius set | `--radius-*` |
| `border-width` | property ∈ border-width set, or a length slot in a `border` shorthand | `--stroke-*` |
| `font-size` | `font-size`, or `text-[…]` with a length | `--type-*` (whole-declaration rewrite) |
| `line-height` | `line-height` with a bare ratio | Deleted — the `--type-*` role carries it |
| `tracking` | `letter-spacing` | `--tracking-*` |
| `color` | property ∈ color set, or a hex/`rgb()` slot anywhere | Ramp step → Tier-2 role |
| `shadow` | `box-shadow`, `text-shadow` | `--elevation-*` |
| `duration` / `easing` | property ∈ motion set | `--dur-*` / `--ease-*`, preferably a `--motion-*` pair |
| `z-index` | `z-index` | `--z-*` |
| `color-function` | `darken()`, `lighten()`, `mix()` | A ramp step, by hand |

**Shorthand slots get the property they actually set.** `padding: 9px 17px` is block padding and inline padding — two different decisions written on one line. Filing both as "padding" throws away the distinction the inset vocabulary is built on, and produces a mapping that turns a page gutter into a card inset. The slot count decides the pattern (1 → all, 2 → block/inline, 3 → block/inline/block, 4 → block/inline/block/inline), and the count includes `0` and `auto`, which is the bug most implementations have.

---

## 5. Clustering spacing

**Normalize to px.** `rem × 16`, `pt × 4/3`. Deliberately exclude `em`: an em value is a *ratio to the current font size*, so it tracks type rather than bypassing the scale. Snapping it to a px step silently breaks that relationship.

**Snap to the nearest step within a tolerance band.**

```
scale:      0  1  2  4  8  12  16  20  24  32  40  48  64  80  96  128  160  192
tolerance:  3px (default) — tighten to 2 on a deliberate codebase, loosen to 4 on an eyeballed one
```

Anything further than the tolerance from every step is **not snapped**. It goes into the reconciliation report with its two neighbours named. This is the single most important rule in the whole method: a migration that snaps everything has decided, silently, on behalf of a designer, and the first thing anyone notices is the one place it was wrong.

**Ties are broken by frequency, then downward.**

`14px` is exactly 2px from both 12 and 16. Which one it belongs to is not a geometry question — it is an archaeology question. If the codebase contains forty `12px` values and two `16px`, the `14px` belongs with the crowd, because the crowd is the decision and the 14 is the Thursday.

Only when the crowd is silent does the fallback apply: **snap down.** Collapsing 2px of space is a visual nudge; expanding it can push a fixed-width control into a wrap or a scroll. Space is cheaper to remove than to add.

**Flag anything moving more than 2px.** Two pixels is roughly where a change stops being invisible and starts being a diff someone notices in a screenshot. Those rows get their own section in the report, their own commit, and their own before/after shots.

**Then map the step to a role, per property class.** This is where most of the value is, and where the scale-only approach stops being enough:

| Class | 4 | 8 | 12 | 16 | 24 | 32 | 40 |
|---|---|---|---|---|---|---|---|
| gap / margin | `--gap-fused` | `--gap-tight` | `--gap-related` | `--gap-grouped` | `--gap-separate` | — | `--gap-distinct` |
| padding-inline | — | `--pad-inline-xs` | `--pad-inline-sm` | `--pad-inline-md` | `--pad-card` | `--pad-card-lg` | — |
| padding-block | `--pad-block-xs` | `--pad-block-sm` | `--pad-block-md` | `--pad-well` | `--pad-card` | `--pad-card-lg` | — |
| padding (all) | — | — | — | `--pad-well` | `--pad-card` | `--pad-card-lg` | — |

A value that lands on the scale but has **no role in its class** — 20px as a gap, 64px as inline padding — is reported, not forced. Either it moves to a rung that means something, or somebody adds a Tier-2 role. Tier-2 roles are cheap and are meant to be added. What is not acceptable is a component reading `--space-5` directly, which is Law 6, and which is what makes "more air in cards" a grep job a year later.

**Section-scale values (≥ 48px) get a different recommendation.** They are almost always page rhythm, and page rhythm is fluid: `--space-section`, `--space-subsection`, `--space-block`. A frozen 74px is cramped at 1440px and a scroll tax at 390px.

---

## 6. Clustering color

### The metric

Euclidean distance in **OKLab** — ΔE<sub>ok</sub>. Not hex distance (meaningless), not HSL distance (its lightness is a lie), not CIELAB (better, but its blues are visibly wrong and it is not what the rest of this suite computes in).

The threshold is **0.025**, and here is the calibration it comes from, measured on real sRGB values:

| Pair | ΔE<sub>ok</sub> | Verdict |
|---|---|---|
| one 8-bit code value at mid-gray | 0.0035 | the floor of what is even representable |
| `#333333` vs `#343434` | 0.0039 | one decision, typed twice — **merge** |
| `#e6e6e6` vs `#ececec` | 0.0181 | both are "the rule color" — **merge** |
| `#333333` vs `#3a3a3a` | 0.0274 | the same ink on two Thursdays — merges via the chain below |
| `#808080` vs `#858585` | 0.0168 | **merge** |
| `#2f6df6` vs `#2558c8` | 0.0876 | brand and brand-hover: **two decisions** |
| `#d64545` vs `#922222` | 0.1630 | **separate**, obviously |

0.025 is about seven sRGB code values at mid-gray — below what anyone distinguishes without an eyedropper, and far below what survives a JPEG screenshot or a different monitor. Above it you start merging things a designer chose on purpose.

### The algorithm: single linkage, capped

Single linkage is the right shape for this problem: near-duplicates arrive as *chains* (`#333` → `#343434` → `#3a3a3a`, each link under threshold, the ends 0.027 apart) and collapsing chains is the entire job.

It is also single linkage's famous failure mode. So the chain is capped: **a merge is refused when it would make the cluster's widest pair exceed 1.5 × tolerance.** Without the cap, one codebase's worth of near-whites merges into a single "color" that is `#e5e5e5` at one end and `#ffffff` at the other.

### Three guards that matter more than the threshold

**1. Pure white and pure black never absorb a neighbour.** `#ffffff` vs `#fafaf9` measures 0.0152 — well inside the threshold — and merging them is wrong, because they are `--bg-surface` and `--bg-canvas`: the card and the page it sits on. That distinction is what makes cards read as cards. White and black are structural anchors and every design system re-points them independently.

**2. A tint is not a gray.** Near white, OKLab compresses hard: `#eef2ff` (a blue info tint) and `#e6e6e6` (a rule) are only 0.041 apart, and a chain through `#ececec` will happily join them. Refuse any merge where one member is achromatic (C < 0.005) and the other is a tint (C ≥ 0.015). Chroma is the design intent there and ΔE is not allowed to overrule it.

**3. Two chromatic colors more than 30° apart in hue never merge.** `#eef2ff` and `#fdecea` are 0.031 apart in ΔE and 114° apart in hue. One means information, the other means error. A metric that merges them has lost the only thing that mattered.

**Alpha buckets are separate clusters.** A translucent fill is an interaction overlay, not a palette entry: `--bg-hover` and `--bg-active` already compose over any surface. A translucent color inside a `box-shadow` belongs to an `--elevation-*` role. Neither becomes a ramp step.

### Mapping a cluster to a token

1. Compute the frequency-weighted centroid in sRGB, convert to OKLab.
2. Find the nearest ramp step by ΔE across the neutral, accent and status ramps — with the same tint guard, so a chromatic source may not land on a near-achromatic step. `#fff8e1` measures marginally closer to `--neutral-50` than to `--warning-100`, and letting ΔE decide would quietly turn a notice background into the page canvas.
3. Pick the **Tier-2 role from the step and the property class**, not from the step alone.

| Ramp step | as `color` | as `background` | as `border-color` |
|---|---|---|---|
| neutral-0 | `--fg-on-accent` | `--bg-surface` | — |
| neutral-50 | `--fg-on-inverse` | `--bg-canvas` | — |
| neutral-100/200 | — | `--bg-sunken` | `--border-subtle` |
| neutral-300 | `--fg-disabled` | `--bg-disabled` | `--border-default` |
| neutral-500 | `--fg-subtle` | — | `--border-strong` |
| neutral-600/700 | `--fg-muted` | — | — |
| neutral-800/900 | `--fg-default` | `--bg-inverse` | — |
| neutral-950 | `--fg-strong` | `--bg-inverse` | — |
| accent ≤ 100 | *(too light for text)* | `--bg-selected` | *(too light for a line)* |
| accent 400–600 | — | `--bg-accent` | `--border-accent` |
| accent ≥ 600 | `--fg-accent` | `--bg-accent-hover` | `--border-focus` |
| status 500 | — | `--bg-<status>` | — |
| status 700 | `--fg-<status>` | — | — |

The step guards on the accent row are not pedantry. `--bg-accent` **is** accent-600; pointing a pale `#eef2ff` badge fill at it turns a tint into a saturated button, and that is the single most visible way an automated color migration goes wrong.

### Contrast is measured, not assumed

Every proposed foreground role is measured against **the surface it actually lands on** — `--fg-on-accent` against `--bg-accent`, `--fg-subtle` against `--bg-sunken`, everything else against `--bg-canvas`. Scoring white-on-accent against the page canvas manufactures a failure for the one pairing that was never in question, and a report that cries wolf gets skimmed.

Report before and after. A role that *loses* contrast relative to the original is not automatically wrong — the generated ramp is perceptually even and the original was not — but it is never allowed to pass silently.

### Deriving the ramps from the codebase

**Accent seed:** the most-used chromatic cluster (C ≥ 0.04), preferring one that is not sitting on a status hue. This matters more than it sounds: a token file whose accent is visibly *their* blue gets adopted, and one whose accent came from a style guide gets ignored.

**Neutral hue:** the circular mean of the grays, weighted by count × chroma, restricted to 0.001 ≤ C ≤ 0.012. Chroma weighting is essential — a hue angle read off a color with C = 0.001 is numerical noise and would otherwise outvote a real one. Below an evidence floor, keep the house default (75°, warm graphite). A codebase whose grays are `#333` and `#666` has no neutral temperature to preserve, and inventing one is worse than defaulting.

Everything else — the L curve, the chroma falloff, the hue drift — comes from the studio's tuned tables, unchanged. Those are the house style and the migration does not get a vote.

---

## 7. Clustering type

Snap to the type scale — 11, 12, 14, 16, 18, 22, 28, 35, 44 px — with the same tolerance mechanism and **one inverted rule: ties snap up.**

`15px` is equidistant from 14 and 16. It becomes 16 (`--type-body`), not 14 (`--type-ui`), even when 14px is the commoner size. Text does not shrink to settle a tie; 16px is the floor for reading copy and the reading experience wins over the tiebreak. Frequency settles a spacing tie (the crowd is the decision), never a type one.

The replacement is a **whole-declaration rewrite**, not a value swap:

```css
/* example: illustration — before and after, side by side */
/* before */                      /* after */
font-size: 15px;                  font: var(--type-body);
```

because a `--type-*` role carries size, leading, weight and family as one shorthand. Half a role is how a 35px heading ends up at body leading, which is the most common typographic bug on the shipped web.

This creates one hazard the codemod must handle: the `font` shorthand **resets** every font property it does not name. When the same rule already declares `font-weight`, `font-family`, `font-style` or `line-height`, the rewrite is skipped and reported. Those siblings have to be deleted by hand first — the role already carries them — and a script that deletes lines is a script nobody approves.

`line-height` gets the same answer for the same reason: once the sibling `font-size` is a `--type-*` role, the `line-height` declaration is a second source of truth for one value and must go. It is always reported, never codemodded.

`11px` snaps to `--text-2xs`, which has **no** `--type-*` role — deliberately. It exists as a primitive for dense table meta and legal text. If the text is neither of those, it belongs at `--type-label`.

---

## 8. Clustering shadows

Shadows cluster by **structural signature**, not by value:

```
(layer count, max blur, max |y-offset|)
```

Alpha is excluded on purpose. Two shadows with the same geometry and alphas of 0.07 and 0.08 are one elevation decision and one eyeballed adjustment at 3pm. Geometry is what a viewer reads as height.

Parse the numbers **positionally** — x, y, blur, spread — after removing the color function. The trap: `0 12px 28px rgba(0,0,0,.18)` leads with a *unitless* zero, and a regex that insists on `px` reads the blur as the y-offset and files a modal shadow as a card. That bug is invisible in testing and obvious in production.

Map max blur to an elevation role:

| Max blur | Role |
|---|---|
| ≤ 4px | `--elevation-card` |
| ≤ 12px | `--elevation-raised` |
| ≤ 28px | `--elevation-overlay` |
| > 28px | `--elevation-modal` |

Always flag the conversion. The contract's elevations are two-layer pairs — a tight contact shadow plus a wider ambient one — and a single-layer original will read slightly flatter after the swap. That is an improvement, but it is a visible one and the designer gets to see it before it ships.

A `0 0 0 3px rgba(...)` with no blur is a **focus ring**, not an elevation. It belongs to `--shadow-focus`, and the geometric classifier will get it wrong, so check for it.

---

## 9. Clustering durations, easings and z-index

**Durations** round to the five steps — 80, 140, 220, 320, 480ms — with a generous tolerance (60ms by default), because nobody has ever chosen 250ms over 220ms for a reason.

But the token they map to depends on the shape of the declaration:

```css
/* example: illustration — each line reads before → after */
/* A complete transition collapses to the Tier-2 PAIR */
transition: opacity 250ms ease-out;   →   transition: opacity var(--motion-enter);

/* A standalone duration property has no easing to pair with */
transition-duration: 250ms;           →   transition-duration: var(--dur-base);
```

The pair matters because a duration and an easing living in separate tokens drift apart inside a quarter — someone tunes one and not the other, and then two components that should feel identical do not. Always mark the pair conversion for review: enter and exit are deliberately asymmetric (things arrive slower than they leave), and the script can only see the number.

Split per comma layer. `transition: a 180ms ease, b 180ms ease` is two transitions, and replacing across the comma produces one broken one.

**Easings** map by control-point distance to the four named curves. `cubic-bezier(0.4, 0, 0.2, 1)` — Material's standard curve, which is in every codebase — lands on `--ease-in-out` at a distance of 0.29. Report the distance; anything over ~0.3 is a curve somebody chose and deserves a look.

**Z-index is order, not magnitude.** `9999` never meant "very high" — it meant "higher than the last person's 999". Rank the distinct values, assign rungs by magnitude band (0–49 → `--z-raised`, 50–149 → `--z-sticky`, … ≥ 550 → `--z-tooltip`), then force strict monotonicity so no two values swap places. Mark **every** z-index mapping for review without exception: stacking contexts are invisible in the source, and the only thing the numbers encoded was relative order.

---

## 10. The hard cases

### Values that legitimately differ

A `1px` border and a `1px` gap are the same number and different decisions. The border is `--stroke-default`; the gap is `--space-px`. Property class separates them and is why the census records the property rather than the string.

The same applies to `2px`: `--stroke-thick` in a focus ring, `--radius-xs` on a chip, `--space-0-5` as an icon/label optical gap. Three tokens, one number, and any tool that keys on the value alone gets all three wrong.

### The same intent at two densities

An admin table with `padding: 6px 8px` and a marketing card with `padding: 8px 12px` may be the same decision at two densities. The contract's answer is `--density` (0.875 / 1 / 1.125) — one dial on a subtree, not a second set of styles.

Detect it by pattern, not by value: when a directory's spacing values are consistently ~0.875× another directory's, you are looking at a density variant. Migrate both to the same roles and set `data-density="compact"` on the dense subtree. If you migrate them to different tokens you have hardcoded the density and switching it later reveals every value you missed.

### One-off marketing pages

A landing page built in a week and never revisited will have values nothing else shares — `47px` headings, `74px` section gaps. The instinct is to widen the scale to absorb them. Do not.

Three legitimate options, in order:

1. **Snap them.** A one-off page is exactly where a 3px move costs nothing, because no other page is aligned to it.
2. **Fluid page rhythm.** `74px` is a section gap; `--space-section` is what it wanted to be, and it will be correct at both 390px and 1440px, which `74px` is not.
3. **Leave it out of the migration entirely**, behind the baseline, and note it. A page nobody will edit again does not need to be on the system; it needs to be *frozen* on the system's gate so it does not get worse.

What is never an option is `--space-18-5`.

### Vendor and third-party CSS

Never migrate it. It has an upstream, and every value you change is a value that comes back on the next `npm update`, in a merge conflict, in a file nobody owns.

Exclude it from the census by default so the estimate is honest. Run once with `--include-vendor` to see the true total — useful when arguing for *replacing* a dependency — and never again. The containment strategy is in `framework-migrations.md` §6: you layer it, you do not fight it.

### Values that exist only to cancel other values

```css
/* example: before — what the census finds */
.card { padding: 16px; }
.card__media { margin: -16px -16px 16px; }   /* bleed to the edge */
```

That `-16px` is not a spacing decision; it is a *relationship* to the padding. It must become `calc(var(--pad-well) * -1)` when the padding became `var(--pad-well)` (16px on the starter scale) — `calc(… * -1)` is also the only form Law 2 permits — and it must point at the **same token** the padding uses, or the next time the card's padding changes the bleed breaks. Never let a negative cancel resolve to a different token from the value it cancels. On its own, `16px` in a margin clusters to a gap token (`--gap-grouped`), so the codemod pairs each negative margin with the padding of its parent rule: the rule it is nested in, the left side of a descendant or child selector (`.panel > .bleed`), or a BEM element's block (`.card__media` in `.card`). A padding of the same size there, on the same side (`margin-right` cancels the right padding), decides the token, if it is set in one block of the file (the last declaration there winning). A padding set in two blocks (another `@media`, an `@layer`, or the rule written twice) depends on which one wins the cascade, so the margin keeps its gap token. A selector list (`.a, .panel`) counts as each of its members, on either side: every member must find the same token. A negative margin with no such padding is a spacing value of its own, and keeps its gap token; check those by eye.

### Values inside `calc()`

`calc(100% - 13px)` contains a spacing decision that survives every migration, because grep cannot see inside parentheses and most codemods do not recurse. Flatten the math expression into its operands and treat each one on its own. `100%` is relational and stays; `13px` is a decision and goes.

---

## 11. The consolidate-vs-separate decision rule

Apply in order and stop at the first line that answers. It resolves nearly every real argument in a Phase 3 review.

| # | Test | If yes |
|---|---|---|
| 1 | Do the two values appear in **different property classes** (a border and a gap; a fill and an ink)? | **Separate.** They are different decisions that share a number |
| 2 | Is the difference below the perceptual floor — < 2px, or ΔE < 0.005? | **Consolidate.** Nobody can see it, including whoever typed it |
| 3 | Do they sit on **different sides of a semantic boundary** — surface vs canvas, info tint vs error tint, brand vs brand-hover? | **Separate**, regardless of how close they measure |
| 4 | Does one appear ≥ 10× more often than the other? | **Consolidate** into the frequent one. The rare one is the accident |
| 5 | Do they always appear in the **same component**, in a deliberate relationship (a card's padding and its media bleed)? | **Consolidate**, and express the relationship with `calc()` rather than two tokens |
| 6 | Does consolidating change a **measured contrast ratio** across 4.5:1 or 3:1? | **Separate**, and escalate. Accessibility is not a tiebreak |
| 7 | Still undecided? | **Consolidate**, and put it in the report. A wrong consolidation is one line to revert; a duplicated token is forever, because nobody ever deletes one |

Rule 7 is doing real work. The asymmetry is the point: over-consolidation is visible, cheap and reversible, while under-consolidation is invisible and permanent. A system with two tokens doing one job has already started dying, and nobody will ever be the person who deletes one.

---

## 12. The report format

The reconciliation report is the deliverable of Phases 1–3. Not the token file — the report. Three sections, in this order, because this is the order a reviewer needs them:

**1. The arithmetic.** One table: mechanically replaceable / needs eyes on a diff / needs a design decision, as occurrences and as a share of the total. The middle row is the honest part of any migration estimate, and the third row is the only one with a person's name on it.

**2. What moved and what it cost.** Every replacement that shifts a value more than 2px, with its delta and its occurrence count. Every foreground role with measured before/after contrast against its real surface. These are the rows that need screenshots and the rows that need sign-off, and they are usually fewer than thirty.

**3. Values with no home.** Every unmappable value, with: where it is, why it does not map, and **a specific recommendation**. Not "review this" — "this is a section gap; use `--space-section`, which is fluid, rather than freezing 74px that is cramped at 1440 and a scroll tax at 390."

A reconciliation report without recommendations is a list of problems, and a list of problems handed to a busy team is a migration that stalls in Phase 3. The recommendation is the entire difference between a report that gets acted on and one that gets bookmarked.

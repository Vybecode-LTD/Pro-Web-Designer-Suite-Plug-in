# Layout & Composition

Layout is where a design system either holds or quietly dissolves. Colour and type survive a sloppy team because a wrong hex is visibly wrong; a wrong `margin-bottom` is invisible in isolation and only reads as "this site feels off" after four hundred of them. This file is the structural half of the system: the closed set of layout primitives every page is composed from, the rules for when layout responds to its container versus the viewport, and the ownership rule that keeps spacing decisions in ten places instead of four hundred.

Ground truth is `assets/starter/styles/tokens.css`. The implementation is `assets/starter/styles/layout.css` — every code block below is quoted from it, not invented for the doc.

Laws that bite hardest here: **2** parents own the gaps (this file is essentially an extended proof of Law 2) · **1** tokens or nothing · **4** one home per component's styles (the primitives' home is `layout.css`; a `display: grid` in a component file is a smell) · **5** layers, not specificity · **7** density is a dial.

## Contents

1. [The primitive model](#1-the-primitive-model) — [why primitives beat bespoke CSS](#11-why-primitives-beat-bespoke-layout-css) · [the closed set](#12-the-closed-set)
2. [The eleven primitives](#2-the-eleven-primitives) — [Stack](#21-stack) · [Flow](#22-flow-the-owl) · [Cluster](#23-cluster) · [Row](#24-row) · [Split](#25-split) · [Sidebar](#26-with-sidebar) · [Switcher](#27-switcher) · [Grid](#28-grid) · [Cover](#29-cover) · [Frame](#210-frame) · [Center](#211-center) · [Reel](#212-reel) · [Imposter](#213-imposter)
3. [Intrinsic vs extrinsic layout](#3-intrinsic-vs-extrinsic-layout)
4. [The grid system](#4-the-grid-system) — [12-column vs content-driven](#41-12-column-vs-content-driven) · [the minmax(0,1fr) fix](#42-the-minmax01fr-fix) · [the full-bleed breakout recipe](#43-the-full-bleed-breakout-recipe) · [subgrid](#44-subgrid)
5. [Responsive strategy](#5-responsive-strategy)
6. [Page-level composition](#6-page-level-composition) — [the skeleton](#61-the-canonical-skeleton) · [rhythm](#62-rhythm) · [the section-boundary rule](#63-the-section-boundary-rule)
7. [Alignment](#7-alignment)
8. [Sizing](#8-sizing)
9. [Whitespace as structure](#9-whitespace-as-structure)
10. [Anti-patterns](#10-anti-patterns)
11. [Audit](#11-audit-law-9)

---

## 1. The primitive model

A layout primitive is a named, parameterised arrangement of children that carries no content opinions and no visual style. It answers one question — *how do these boxes relate in space* — and nothing else. `.stack` does not know it contains a form. `.grid` does not know it contains cards.

The claim this file defends: **every layout in a real product is a composition of about eleven primitives, and writing bespoke layout CSS in a component file is almost always a mistake.**

### 1.1 Why primitives beat bespoke layout CSS

Consider a 400-component codebase that spaces things ad hoc. Each component makes an independent spacing decision, so the system contains ~400 decisions. Now product asks for "a bit more air between cards on marketing pages, not in the app." There is no such thing as "between cards" to change — there are 40 different rules that happen to produce a similar gap, written by six people over two years, half of them as `margin-bottom` on the child and half as `padding-bottom` on the parent. The change is a week of grep and a regression.

With primitives, the same codebase contains **one** decision per primitive per context. "Between cards" is `--grid-gap` on `.grid`, re-pointed by a modifier or by density. The change is one line.

The concrete wins, in the order they pay off:

| Win | Mechanism |
|---|---|
| **Spacing decisions collapse** from O(components) to O(primitives) | A component composes; it does not decide |
| **Diffs become readable** | `<div class="stack stack--separate">` states intent; `margin-top: 22px` states a number |
| **Theming and density work** (Law 7) | `--density` re-points Tier-2 tokens; primitives read Tier-2, so a whole subtree recomposes with one attribute. Bespoke values are invisible to that mechanism |
| **Nesting stops surprising people** | Primitives compose predictably because none of them sets outer margin on itself |
| **Review gets fast** | "Which primitive is this?" is answerable in three seconds. "Is `margin-top: 22px` correct here?" is not answerable at all |
| **New people are productive in a day** | Eleven names is a learnable vocabulary. A house style spread over 400 files is not |

The cost is real and worth naming: an extra wrapper element now and then, and an up-front hour learning names. Both are cheap. What is *not* cheap is the failure mode this prevents — spacing entropy, where every screen is 95% right and no screen is right.

**When to break the model.** A genuinely novel arrangement — an editorial collage, a seat map, a timeline — goes through the Law 8 gate in `references/pattern-invention.md`. If it survives and will be used more than twice, it becomes primitive number twelve and lives in `layout.css`. If it will be used once, it lives in that one component's file, is named for what it is, and is documented as a one-off. What it never does is quietly reinvent Stack with different numbers.

### 1.2 The closed set

| Primitive | Question it answers | Reach for it when |
|---|---|---|
| **Stack** | How do these sit one above another? | Any vertical sequence. The default |
| **Flow** | Same, but the container must stay a block container | Prose, CMS/MDX output, per-pair gaps |
| **Cluster** | How does this wrapping group of small things sit? | Tags, chips, button groups, meta rows |
| **Row** | How do these sit in one line that must not wrap? | Toolbars, list-row internals, field + button |
| **Split** | Two panes at a ratio, stacking when narrow | Copy beside image, form beside summary |
| **Sidebar** | Content plus a rail that gives up when cramped | Docs nav, filter rail, article + aside |
| **Switcher** | N equal columns, stacked below a threshold | Pricing tiers, 3-up features |
| **Grid** | An unknown number of equal cells | Card grids, galleries, logo walls |
| **Cover** | Fill at least this much height, centre the point | Heroes, empty states, full-screen prompts |
| **Frame** | Constrain unpredictable media to a ratio | Any image or video you did not author |
| **Center** | Constrain and gutter a column | Every page-level content column |
| **Reel** | Overflow horizontally, honestly | Related items, media strips, mobile carousels |
| **Imposter** | Put this on top of that | Modals, scrims, badges. **Overlay only** |

Thirteen names for eleven concepts (Flow is Stack's block-container variant; Row is Cluster that refuses to wrap). Nothing else is needed, and adding a fourteenth without the Law 8 gate is how the set stops being closed.

---

## 2. The eleven primitives

Every primitive follows the same contract:

- It declares **Tier-3 custom properties on itself**, each defaulting to a **Tier-2 token**.
- It is tuned by re-pointing that property at a *different Tier-2 token*, via a modifier class or inline — never at a raw value.
- It sets **no outer margin on itself** and no visual style (colour, border, shadow). Those belong to the component.

```css
.stack { --stack-gap: var(--gap-grouped); gap: var(--stack-gap); }
.stack--separate { --stack-gap: var(--gap-separate); }
```

```html
<!-- correct: a socket re-pointed at another token -->
<div class="stack" style="--stack-gap: var(--gap-separate)">
<!-- wrong: the socket is not a licence to invent values (Laws 1, 3) -->
<div class="stack" style="--stack-gap: 18px">
```

### 2.1 Stack

Vertical rhythm. The default answer to "these go one above another", and the reason nobody in the codebase should ever type `margin-bottom`.

```css
.stack {
  --stack-gap: var(--gap-grouped);
  display: flex;
  flex-direction: column;
  gap: var(--stack-gap);
}
.stack > .stack__push-end { margin-block-start: auto; }
```

**Props** `--stack-gap`. **Modifiers** `--fused` `--tight` `--related` `--separate` `--distinct` `--prose` — the proximity ladder from tokens.css, one modifier per rung. Pick by *meaning*: `--tight` is "label and its input", not "8px". `--fill` gives the stack `block-size: 100%` so `.stack__push-end` can pin a card footer to the floor.

**Why gap and not margin.** `gap` is a property of the *container*, so the container owns every boundary (Law 2) and the value appears once. Margins additionally collapse, which means the space between two stacked cards is `max(a, b)` rather than a designed value, and which breaks the instant someone adds `overflow: hidden`.

**`margin-block-start: auto` is not a Law 2 violation.** `auto` is an alignment keyword, not a length off the scale. No spacing decision is being taken in a child's stylesheet.

### 2.2 Flow (the owl)

Stack for containers that must stay block containers.

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

**Use Flow, not Stack, when any of these holds:**

1. **The container holds prose.** `display: flex` turns every bare text node into an anonymous flex item, so `text <a>link</a> text` fragments into three stacked blocks. Flex and grid also kill float-based pull quotes and disable margin collapsing that editorial layouts sometimes want.
2. **Boundary values differ by sibling pair.** `gap` is one value for every boundary. Prose needs `h2 + p` tighter than `p + p` — the heading belongs to what follows it, and that proximity is what replaces a horizontal rule.
3. **The children come from a renderer you do not control** (CMS, MDX), so you cannot guarantee they are element children — see 1.

Block-level `gap` is specified and shipping, but is not baseline across the browsers this starter supports. Until it is, prose uses the owl.

**Law 2 is intact.** The margin is written in the *parent's* rule (`.flow > * + *`). Ownership is about which rule makes the decision, not which box carries the pixels. A child's own stylesheet still never sets an outer margin.

### 2.3 Cluster

A wrapping horizontal group.

```css
.cluster {
  --cluster-gap: var(--gap-related);
  --cluster-align: center;
  --cluster-justify: flex-start;
  display: flex; flex-wrap: wrap;
  gap: var(--cluster-gap);
  align-items: var(--cluster-align);
  justify-content: var(--cluster-justify);
}
```

**Props** `--cluster-gap` `--cluster-align` `--cluster-justify`. **Modifiers** `--fused` `--tight` `--grouped` `--center` `--end` `--between` `--baseline` `--start`.

`gap` is not optional here; it is the whole point. With margins, a wrapped row gains a phantom leading margin on its first item and the rows sit at different distances from each other than the items do. `gap` applies only *between*, in both axes, and wrapping stays invisible.

**Reach for it instead of writing new CSS** for: tag lists, chip rows, button groups, article meta ("by X · 4 min · Design"), footer link sets, breadcrumb trails. The item count is unknown at design time and no breakpoint needs to know it.

### 2.4 Row

A horizontal line that must *not* wrap.

```css
.row {
  --row-gap: var(--gap-related);
  --row-align: center;
  display: flex; flex-wrap: nowrap;
  align-items: var(--row-align);
  gap: var(--row-gap);
}
.row > * { min-inline-size: 0; }
```

Distinct from Cluster because "never wrap" is a design decision: a toolbar that silently becomes two rows at 340px is usually a bug you want to see rather than absorb.

`min-inline-size: 0` is the flexbox overflow fix (§8). Without it, a child containing a long word, a `<pre>` or a table refuses to shrink below its min-content size and blows the row out of its parent — and `text-overflow: ellipsis` on a descendant silently does nothing.

**Modifiers** `--baseline` `--start` `--stretch` `--between` `--equal` (`flex: 1 1 0` on children: equal columns regardless of text length) `--fill-first` / `--fill-last` (input + button).

### 2.5 Split

Two panes at a fixed ratio that stack intrinsically.

```css
.split {
  --split-gap: var(--gap-separate);
  --split-threshold: var(--width-form);
  --split-a: 1; --split-b: 1;
  display: flex; flex-wrap: wrap; gap: var(--split-gap);
}
.split > :first-child { flex: var(--split-a) 1 calc((var(--split-threshold) - 100%) * 999); }
.split > :last-child  { flex: var(--split-b) 1 calc((var(--split-threshold) - 100%) * 999); }
```

**The mechanism, because it looks like a trick and is not.** `100%` in a flex item's basis resolves against the *container's* inline size.

- Container **narrower** than the threshold → `(threshold − 100%)` is positive, `× 999` makes it enormous, each pane demands more than the full width, and they wrap to one per line.
- Container **at or wider** than the threshold → the expression is negative. A negative `flex-basis` is invalid and clamps to `0`, so both panes have zero basis and divide all the space by their `flex-grow` ratio, `--split-a : --split-b`.

This yields asymmetric two-column layouts with **no media query and no container query**: the same markup is correct in a hero, inside a sidebar, and inside a modal.

**Modifiers** `--1-2` `--2-1` `--1-3` `--3-1` `--center` `--stretch` `--loose`. **Threshold default** `--width-form` (28rem) — below one form-width per pane, two columns stop being usable for anything but decoration.

### 2.6 with-sidebar

Content plus a rail that wraps at a *content-based* threshold, not a breakpoint.

```css
.with-sidebar {
  --with-sidebar-gap: var(--gap-separate);
  --with-sidebar-rail: calc(var(--width-content) / 4);
  --with-sidebar-content-min: 60%;
  display: flex; flex-wrap: wrap; gap: var(--with-sidebar-gap);
}
.with-sidebar > .with-sidebar__rail { flex-basis: var(--with-sidebar-rail); flex-grow: 1; min-inline-size: 0; }
.with-sidebar > .with-sidebar__main { flex-basis: 0; flex-grow: 999; min-inline-size: var(--with-sidebar-content-min); }
```

The rail asks for its natural width. The main pane asks for everything else (`flex-basis: 0` + a grow factor large enough to dominate). The wrap is triggered by `min-inline-size` on the main pane: the instant main would be squeezed below 60% of the container, flexbox cannot satisfy both on one line and wraps them. **That is a content threshold, not a viewport threshold**, which is why the same rail works in a page and inside another sidebar.

**Rail width is derived, not invented**: `calc(var(--width-content) / 4)` = 288px at the default 72rem. There is no `--width-rail` token, and adding one would be a fifth width to keep in sync. Deriving it means re-pointing `--width-content` moves every rail in the product in proportion. Modifiers `--narrow-rail` (`/6`) and `--wide-rail` (`/3`) use the same arithmetic.

The `60%` is a **ratio, not a scale value** — one of the licensed non-token values (§8). It is the answer to "how much of the container does the reading column need to stay a reading column", which has no meaningful expression in rem.

**Sticky rail gotcha.** A stretched flex item is already as tall as its row, so `position: sticky` on it has nowhere to move and silently does nothing. This is the commonest "sticky doesn't work" bug in flex layouts. `.with-sidebar--sticky-rail` sets `align-self: start` first.

### 2.7 Switcher

N equal columns that flip to stacked below an intrinsic threshold.

```css
.switcher {
  --switcher-gap: var(--gap-grouped);
  --switcher-threshold: var(--width-form);
  display: flex; flex-wrap: wrap; gap: var(--switcher-gap);
}
.switcher > * {
  flex-grow: 1;
  flex-basis: calc((var(--switcher-threshold) - 100%) * 999);
  min-inline-size: 0;
}
.switcher > :nth-last-child(n + 5),
.switcher > :nth-last-child(n + 5) ~ * { flex-basis: 100%; }
```

Same clamp mechanism as Split, but every child shares one basis so the columns stay equal. It switches **all at once** — three columns become three rows, never two-plus-one. That is the difference from Grid, and it is the right behaviour for peer content (three pricing tiers are equals; an orphaned third tier on its own row reads as an afterthought).

**The quantity guard is not decoration.** Past the cap, equal columns are unreadably narrow at *any* container width, so they are forced full-width. `:nth-last-child(n + 5)` counts from the end and is CSS's way of asking "are there at least 5 children?". The default cap is 4; modifiers `.switcher--max-3` (right for cards with headings and body copy) and `.switcher--max-2` tighten it.

The cap is a **class, not a custom property**, and cannot be one: selectors are matched before the cascade resolves variables, so `:nth-last-child(n + var(--x))` is not expressible. This is the same limitation as query preludes (§3), with the same workaround — a small set of named options rather than an open parameter.

**Switcher vs Grid.** Switcher when the count is known and small and the items are peers. Grid when the count is unknown or large and a ragged last row is fine.

### 2.8 Grid

```css
.grid {
  --grid-gap: var(--gap-grouped);
  --grid-min: var(--measure-narrow);
  display: grid;
  gap: var(--grid-gap);
  grid-template-columns: repeat(auto-fit, minmax(min(var(--grid-min), 100%), 1fr));
}
.grid > * { min-inline-size: 0; }
```

Column *count* is derived from available width, so seven items lay out sensibly with no special case.

**`min(var(--grid-min), 100%)` is the fix everybody forgets.** A bare `minmax(18rem, 1fr)` **overflows** any container narrower than 18rem, because 18rem is a hard floor that grid will honour past the container edge. Wrapping the floor in `min(…, 100%)` clamps it. This single call is the difference between a grid that works inside a sidebar and one that produces horizontal scroll on a 320px phone.

**`auto-fit` vs `auto-fill`.** `auto-fit` collapses empty tracks, so two items in a four-track row stretch to fill. `auto-fill` keeps them, so two items stay their natural size and hug the start. Use `auto-fill` (`.grid--fill`) for logo walls and avatar rows where stretching one logo to 600px would be absurd; `auto-fit` everywhere else.

**Track floors** are derived from the content column for the same reason rails are: `--min-xs` `/6` · `--min-sm` `/4` · `--min-md` `/3` · `--min-lg` `/2`.

### 2.9 Cover

```css
.cover {
  --cover-min: 100svh;
  --cover-pad: var(--space-subsection);
  --cover-gap: var(--gap-separate);
  display: flex; flex-direction: column;
  min-block-size: var(--cover-min);
  padding-block: var(--cover-pad);
  gap: var(--cover-gap);
}
.cover > .cover__center { margin-block: auto; }
```

`margin-block: auto` on the centre child is what makes the header and footer slots *optional*: with neither, the child is centred in the box; with one, it is centred in what remains. No `justify-content` variant achieves that without knowing how many children exist.

**`min-block-size`, never `block-size`.** A fixed height is a promise you cannot keep the moment the copy is translated into German (§10).

**Modifiers** `--below-header` (`calc(100svh - var(--header-block-size))`), `--partial` (deliberately shorter than a screen, which *signals* scrolling — a full-bleed 100svh hero actively hides the fact that the page continues), `--live` (`100dvh`, for fixed overlays only), `--flush`.

### 2.10 Frame

```css
.frame {
  --frame-ratio: 16 / 9;
  --frame-fit: cover;
  --frame-position: 50% 50%;
  aspect-ratio: var(--frame-ratio);
  overflow: hidden; display: block;
}
.frame > :is(img, video, canvas, svg, iframe, picture),
.frame > picture > img {
  inline-size: 100%; block-size: 100%;
  object-fit: var(--frame-fit); object-position: var(--frame-position);
}
```

Two jobs: stop the page reflowing when an image loads (the CLS fix), and make a row of thumbnails agree when the source assets do not.

`object-fit: cover` crops; `object-position` decides what survives. Faces sit near the top of portraits, so `.frame--portrait` ships `50% 25%`. `.frame--contain` is for logos — never crop a mark.

`<picture>` is a wrapper, not a replaced element, so `object-fit` does nothing on it — the inner `<img>` needs the rule too. Missing that is why art-directed images letterbox inside an otherwise correct frame.

### 2.11 Center

```css
.center {
  --center-max: var(--width-content);
  --center-gutter: var(--gutter-page);
  box-sizing: border-box;
  max-inline-size: calc(var(--center-max) + var(--center-gutter) * 2);
  margin-inline: auto;
  padding-inline: var(--center-gutter);
}
```

**The one place `margin-inline: auto` is allowed to live.** Scattered `margin: 0 auto` is an anti-pattern precisely because it is the same layout decision taken 40 times in 40 files; here it is taken once.

**Note the arithmetic.** With `box-sizing: border-box`, `max-inline-size: var(--width-content)` plus `padding-inline` yields a *content* column of `--width-content − 2 × gutter` — narrower than the token promises, and the reason a "1152px" layout measures 1104px in DevTools. Adding the gutters back makes `--width-content` mean what its name says.

**Modifiers** `--prose` (`--measure-prose`) `--narrow` `--form` `--wide` `--flush`, plus `--intrinsic`, which centres children *by their own width* (flex column + `align-items: center`). Use `--intrinsic` for a CTA stack under a heading: the text stays left-aligned and readable while the block sits on the page's centre line.

### 2.12 Reel

A horizontal scroller — for collections where "see the rest" beats "see everything".

```css
.reel {
  --reel-gap: var(--gap-grouped);
  --reel-item: calc(var(--width-content) / 4);
  display: flex; gap: var(--reel-gap);
  overflow-x: auto;
  overscroll-behavior-inline: contain;
  scroll-snap-type: inline proximity;
  scroll-padding-inline: var(--gutter-page);
}
.reel > * { flex: 0 0 var(--reel-item); scroll-snap-align: start; }
```

Honest about its overflow, which is what makes it better than a carousel: the scrollbar and the clipped next item both tell the user there is more.

- `overscroll-behavior-inline: contain` — stop a horizontal flick triggering browser back-navigation.
- `proximity`, not `mandatory` — mandatory snapping fights fast flicks and can strand people between items. `.reel--snap-strict` when the design genuinely requires one-item-at-a-time.
- **A11y contract:** a scroll container that is not focusable traps keyboard users. `tabindex="0"` plus an accessible name (`role="region" aria-label="…"`) makes it keyboard-scrollable.
- A flex container *does* honour `padding-inline-end` at the scroll end, unlike a block container where the last child's margin is dropped. This is why the trailing gutter works here.

`.reel--peek` (`min(80%, …)`) leaves the next item deliberately half-visible on phones so the affordance is unmistakable.

### 2.13 Imposter

```css
.imposter {
  --imposter-margin: var(--pad-card);
  position: absolute;
  inset-block-start: 50%; inset-inline-start: 50%;
  translate: -50% -50%;
  max-inline-size: calc(100% - var(--imposter-margin) * 2);
  max-block-size: calc(100% - var(--imposter-margin) * 2);
  overflow: auto;
  z-index: var(--z-raised);
}
```

The only primitive that uses absolute positioning, and that is the point: **absolute positioning is for overlay, never for layout** (§10).

The two `max-*-size` clamps and `overflow: auto` are how a modal stays usable on a 667px-tall phone instead of having its confirm button rendered off-screen. Both are routinely omitted. Pair with `.imposter-anchor` (`position: relative`) — never rely on an accidental positioned ancestor.

---

## 3. Intrinsic vs extrinsic layout

**Extrinsic**: the layout asks how wide the *viewport* is (`@media`). **Intrinsic**: the layout asks how much room *it* has, or how big its *content* is (`flex-wrap`, `minmax`, `min()`/`max()`/`clamp()`, `@container`).

**The rule, in order of preference:**

1. **Can the layout solve it with no query at all?** `flex-wrap`, `auto-fit minmax`, the Split/Switcher basis clamp, Sidebar's `min-inline-size`. Prefer this always. It is cheapest, has zero containment side effects, and is correct in every context including ones that did not exist when you wrote it.
2. **Does the component need a different *arrangement* based on its own width?** Use `@container`. Stacked-to-side-by-side media object; a stat that grows its numeral; a nav item that reveals its label.
3. **Is it genuinely a page-level, viewport-level decision?** Use `@media`. Page gutters, the nav's drawer/bar switch, print, `prefers-reduced-motion`.

Rule of thumb: **if a component would answer the question differently inside a sidebar than on a full-width page, the question is intrinsic and a media query will get it wrong.**

### Container queries, with the gotchas

<!-- snippet: layout.css#media-object -->
```css
.region {
  container-type: inline-size;
  container-name: region;
}

/* Example contract, and the pattern to copy: a media object that is stacked
   while its CONTAINER is narrow and horizontal once there is room —
   regardless of viewport width, so it is correct in a page, a sidebar and a
   modal with no extra rules. */
.media-object {
  --media-object-gap: var(--gap-grouped);
  --media-object-rail: calc(var(--width-content) / 6);
  display: grid;
  gap: var(--media-object-gap);
  grid-template-columns: 1fr;
}
@container region (inline-size >= 30rem) {   /* --bp-sm */
  .media-object { grid-template-columns: var(--media-object-rail) 1fr; }
}
```

Six things that break, in the order people hit them:

1. **An element cannot query itself.** You always need a wrapper. This is why `.region` is its own class rather than folded into `.card`.
2. **`container-type: inline-size` applies inline-size and style containment, and makes the element a new formatting context.** It no longer applies layout containment: the CSS Working Group dropped that in 2024, and browsers followed. Inline-size containment means the element's inline size is computed *without looking at its contents*, so it can no longer be sized *by* them. Do not put it on a float, on an inline-block meant to hug its text, or on an item in an `auto` / `min-content` grid track — it will collapse or stretch unexpectedly.
3. **`container-type: size` contains both axes**, so the element's height stops coming from its children and it collapses to zero unless you give it an explicit `block-size`. This is why `inline-size` is almost always right; reserve `size` for something already fixed-height, like a full-screen panel.
4. **A container is a new formatting context.** Margins stop collapsing through it: a child's top margin stays inside the container instead of pushing the container down, so a parent margin and a child margin that used to merge now add up. Floats inside it stay inside it. (A `position: fixed` descendant is placed against the viewport, as anywhere else. Older advice to move fixed modals out of containers dates from when containers applied layout containment.)
5. **`contain: style` scopes CSS counters and quotes.** An ordered list numbered with counters restarts inside the container.
6. **`display: contents` elements cannot be containers.** `container-type` on them has no effect — silently.

**Query preludes cannot read custom properties.** `@media (min-width: var(--bp-md))` does not work and never will: conditional rules are evaluated before the cascade resolves variables. This is the single licensed raw-value exception in `layout.css`; every prelude writes the literal with its token in a comment, and changing a breakpoint means grepping for the old literal. State this out loud in review so nobody "fixes" it.

---

## 4. The grid system

### 4.1 12-column vs content-driven

A 12-column grid is a *print* inheritance: it exists because a fixed-width page can be divided ahead of time. The web has no fixed width, so for most product UI the 12-column grid is ceremony — you end up writing `col-span-4` three times to say "three equal cards", which `auto-fit minmax` says once and says better at every width.

| Use 12-column when | Use content-driven when |
|---|---|
| Editorial layouts need *positions*: an offset pull quote, an asymmetric 7/5 feature, a figure that starts at column 3 | A row of equal cards |
| A design partner is genuinely delivering on a 12-col grid and alignment across unrelated sections matters | The item count is unknown at design time |
| Elements in different sections must align to the same vertical lines | The layout should reflow rather than reposition |

`layout.css` ships both. Default to content-driven; `--grid-columns` exists so the 12-column option is honest when you need it.

```css
.grid--12 { grid-template-columns: repeat(var(--grid-columns), minmax(0, 1fr)); }
.grid--12 > * { grid-column: 1 / -1; }             /* mobile-first: full width */

@media (min-width: 48rem) {   /* --bp-md */
  .grid--12 > * { grid-column: span var(--span, var(--grid-columns)); }
}
```

Children set `--span` per instance. They never write `grid-column` themselves — that is a layout decision leaking into a component (Law 4).

### 4.2 The minmax(0,1fr) fix

**`1fr` means `minmax(auto, 1fr)`, and `auto` as a *minimum* resolves to min-content.** So a single long word, a `<pre>`, a `<table>` or an un-wrapped URL in one column expands that column past its share, and the grid stops being a grid. It is the most-reported "my grid overflows" bug in existence and the fix is one word:

```css
grid-template-columns: repeat(var(--grid-columns), minmax(0, 1fr));
```

The same automatic-minimum rule applies to flex items, where the fix is `min-inline-size: 0` on the child. `layout.css` applies one or the other in every primitive that can hit it: `.row > *`, `.grid > *`, `.split > *`, `.switcher > *`, `.with-sidebar__rail`.

### 4.3 The full-bleed breakout recipe

The most useful thing in this file. Five named lines produce three addressable widths, and a child opts into one with a single declaration — no negative margins, no `100vw`, no `overflow-x` casualties.

<!-- snippet: layout.css#page-grid -->
```css
.page-grid {
  --page-gutter:  var(--gutter-page);
  --page-content: var(--width-content);
  --page-wide:    var(--width-wide);

  display: grid;
  column-gap: var(--space-0);
  grid-template-columns:
    [full-start] minmax(var(--page-gutter), 1fr)
    [wide-start] minmax(var(--space-0), calc((var(--page-wide) - var(--page-content)) / 2))
    [content-start] min(100% - (var(--page-gutter) * 2), var(--page-content)) [content-end]
    minmax(var(--space-0), calc((var(--page-wide) - var(--page-content)) / 2)) [wide-end]
    minmax(var(--page-gutter), 1fr) [full-end];
}

/* Default: everything sits in the content column. Opt out explicitly. */
.page-grid > * { grid-column: content; }
.page-grid > .bleed-wide { grid-column: wide; }
.page-grid > .bleed-full { grid-column: full; }
```

```html
<main class="page-grid sections">
  <section>…constrained…</section>
  <section class="bleed-full">
    <!-- full-bleed background, content back in the column -->
    <div class="page-grid"><div>…constrained again…</div></div>
  </section>
  <figure class="bleed-wide">…wider than text, not edge-to-edge…</figure>
</main>
```

Track by track:

| # | Track | Job |
|---|---|---|
| 1 | `minmax(gutter, 1fr)` | Outer channel. Never narrower than the gutter; absorbs all slack on wide screens |
| 2 | `minmax(0, (wide − content)/2)` | The "wide" shoulder. Min of `0` means it collapses entirely on small screens |
| 3 | `min(100% − 2·gutter, --width-content)` | The content column. The first half keeps gutters on phones; the second caps it on desktop |
| 4, 5 | mirrors of 2, 1 | |

Why `min()` inside the track rather than a media query: the column is *capped* by `--width-content` and *floored* by the available width minus gutters, in one declaration, at every width. There is no breakpoint at which it changes behaviour; it is the same rule everywhere.

**Why not negative margins.** `margin-inline: calc(50% - 50vw)` fights `overflow-x`, silently breaks inside any `overflow: hidden` ancestor, and — because `100vw` includes the scrollbar gutter on desktop Windows and Linux — produces horizontal scroll on exactly the machines your designers do not use. Nothing ever leaves `.page-grid`, so none of that can happen.

**`column-gap` must stay `0`.** The tracks already encode the spacing. `row-gap` is where section rhythm lives (§6.3).

A third convenience: `.bleed-prose` sits in the content column but clamps itself to `--measure-prose`, so an article body needs no extra wrapper.

### 4.4 Subgrid

Without subgrid, three cards in a row lay out independently: a two-line title in card 2 shoves its body copy down, and the row's internal edges stop agreeing. Subgrid makes each card share the *parent's* row tracks, so titles, bodies and footers align across the row whatever the content.

```css
@supports (grid-template-rows: subgrid) {
  .grid--rows-aligned > * {
    --card-rows: 3;
    display: grid;
    grid-template-rows: subgrid;
    grid-row: span var(--card-rows);
  }
}
```

**Contract.** The card must have exactly `--card-rows` top-level children (default 3: header, body, footer). It takes the parent grid's `row-gap` as its internal gap unless it sets a `row-gap` of its own, which a subgrid may do. If the shared alignment itself is not what you want, do not fight it: use `.stack--fill` inside a normal grid and accept the misalignment, or wrap.

**Support.** All current evergreen browsers. Firefox shipped it in 2019 and Safari in 2022 (16); Chrome was last, with 117 in September 2023. The `@supports` guard leaves older engines with independent cards, which degrades to "slightly uneven", never "broken" — the right shape for a progressive enhancement.

---

## 5. Responsive strategy

**Mobile-first, and mean it.** Write the narrow layout as the unconditional rule and add capability with `min-width`. Not because phones matter more, but because the narrow layout is the *simpler* one — a single column with no decisions in it — and additive CSS is easier to reason about than subtractive. A `max-width` query is an admission that the base rule was written for a screen you happened to have.

**Breakpoints are a last resort, not a first move.** In order:

1. Can the content wrap or reflow on its own? (`flex-wrap`, `auto-fit`) → no query.
2. Can a threshold express it? (Split/Switcher basis, Sidebar's `min-inline-size`) → no query.
3. Can `clamp()` / `min()` / `max()` express it? → no query.
4. Does the *component* need a different arrangement at its own width? → `@container`.
5. Only now: `@media`.

**Let the content pick the breakpoint.** The correct breakpoint is the width at which *this layout* stops working — found by dragging the browser until it looks wrong, then reading the number. It is almost never 768px. If a three-up row breaks at 812px, either use an intrinsic threshold (preferred, because then there is no number) or add a one-off `@media (min-width: 52rem)` *at the page level*. What you must not do is round 812 to 768 and ship a layout that is broken for 44px.

**How many breakpoints.** Fewer than you think. `tokens.css` ships five; a typical project uses **two or three** of them.

| Token | Value | What it is for |
|---|---|---|
| `--bp-sm` | 30rem / 480px | Rarely a layout breakpoint. Mostly intrinsic thresholds and container queries |
| `--bp-md` | 48rem / 768px | **The one that earns its keep.** Single column → multi-column; drawer nav → bar nav |
| `--bp-lg` | 64rem / 1024px | Persistent sidebars and three-pane app shells appear |
| `--bp-xl` | 80rem / 1280px | Usually unnecessary: `--width-content` has already capped the column |
| `--bp-2xl` | 96rem / 1536px | Only for genuinely wide-screen layouts (dashboards, data tables) |

If a project has seven breakpoints, it does not have a responsive strategy; it has seven bugs that were each patched where they were found.

**Layout breakpoints vs component breakpoints.**

| | Layout breakpoint | Component breakpoint |
|---|---|---|
| Asks about | The viewport | The component's own container |
| Written as | `@media` | `@container` |
| Lives in | `layout.css` / the page shell | The component's own file |
| Count | 2–3 for the whole project | As many as components need — they do not interact |
| Fails when | A component is reused in a narrower context | Almost never |

A component breakpoint written as a media query is a latent bug: it is correct until the day someone drops the card into a sidebar, and then it is wrong in a way that is expensive to find. That is the meaning of the anti-pattern "one-off media queries inside components" (§10).

---

## 6. Page-level composition

### 6.1 The canonical skeleton

```html
<body class="page-shell">
  <a class="skip-link" href="#main">Skip to content</a>

  <header class="site-header">
    <nav aria-label="Main">…</nav>
  </header>

  <main id="main" class="page-grid sections">
    <section aria-labelledby="hero-h">
      <h1 id="hero-h">…</h1>
    </section>
    <section aria-labelledby="features-h">…</section>
  </main>

  <footer class="site-footer bleed-full">
    <nav aria-label="Footer">…</nav>
  </footer>
</body>
```

```css
:where(.page-shell) {
  --header-block-size: calc(var(--tap-min) + var(--pad-block-md) * 2);
  min-block-size: 100svb;
  display: grid;
  grid-template-rows: auto 1fr auto;   /* footer on the floor of short pages */
}
:where(.page-shell) :target {
  scroll-margin-block-start: calc(var(--header-block-size) + var(--space-block));
}
```

Non-negotiables:

- **Skip link first in the DOM**, positioned off-screen and revealed on `:focus-visible`. Never `display: none` — that removes it from the tab order, which is the one thing it exists for.
- **One `<main>`**, with `id="main"` matching the skip link.
- **Every `<nav>` gets a distinct `aria-label`** ("Main", "Footer", "Breadcrumb", "On this page"). Two unlabelled navs are indistinguishable in a screen reader's landmark list.
- **Sections are labelled** by their heading via `aria-labelledby`; a `<section>` without an accessible name is not announced as a region and may as well be a `<div>`.
- **`--header-block-size` is derived** from `--tap-min` + padding, so it cannot drift from the real header component. It feeds `scroll-margin` (so anchors do not land under the header) and `.cover--below-header`.
- **`min-block-size: 100svb`**, and `grid-template-rows: auto 1fr auto` so the footer sits on the floor of a short page without `position: absolute`.

### 6.2 Rhythm

Three tokens make the whole page's vertical music, and they are hierarchical by design:

| Token | Value | Boundary it marks |
|---|---|---|
| `--space-section` | fluid 64 → 144px | Between top-level page sections |
| `--space-subsection` | fluid 40 → 88px | Between groups inside one long section |
| `--space-block` | fluid 24 → 48px | Between prose blocks — paragraph, list, figure |

All three are fluid because a 96px section gap is a scroll tax on a 390px phone and a 48px one looks unfinished on a 27" display. The *ratios* between them are what the reader perceives as structure: roughly 3 : 2 : 1 at the small end, holding as the page grows. Three levels is the whole ladder. A fourth would be indistinguishable from its neighbours and would immediately be picked by feel instead of by meaning.

Below `--space-block`, you are inside a component, and the proximity ladder (`--gap-fused` … `--gap-distinct`) takes over.

### 6.3 The section-boundary rule

Who owns the space between two sections? Law 2 says the parent — but a parent's `gap` cannot be painted, and a section with a background *must* carry its colour through the boundary. Working it out properly:

> **The boundary between two sections is owned by the parent as `row-gap` — unless a section paints a background, in which case that section owns the boundary as `padding-block`.**

A page is therefore in exactly one of two modes, and **you never mix them on one shell.** Mixing is the single commonest cause of "why is there 200px of space here".

<!-- snippet: layout.css#sections -->
```css
.sections {
  --sections-gap: var(--space-section);
  row-gap: var(--sections-gap);
}
.sections--banded { --sections-gap: var(--space-0); }

.band {
  --band-pad-block: var(--space-subsection);
  padding-block: var(--band-pad-block);
}
.band--tight { --band-pad-block: var(--space-block); }
.band--loose { --band-pad-block: var(--space-section); }
.band--flush { --band-pad-block: var(--space-0); }   /* edge-to-edge media */
.band--sunken { background: var(--bg-sunken); }     /* paint lives here, not in style="" */
```

| Mode | Parent | Child | Boundary measures |
|---|---|---|---|
| **Gap mode** (`.sections`) — no section paints a background | `row-gap: var(--space-section)` | nothing | `--space-section` |
| **Band mode** (`.sections--banded`) — any section paints a background | `row-gap: 0` | every child is `.band`, `padding-block: var(--space-subsection)` | 2 × `--space-subsection` |

Two consequences worth stating, because both look like bugs until you see the reasoning:

1. **In band mode, a section with no background still gets `.band`.** A transparent band keeps the rhythm uniform and keeps the rule one rule instead of a special case per section.
2. **A seam between two bands measures 2 × `--space-subsection` (80 → 176px), slightly more than `--space-section`.** That is correct, not a rounding error: a colour change is itself a boundary marker, and two large painted regions need more air between their *contents* than two invisible ones, because each one's content also has to clear its own painted edge.

**Padding is not a Law 2 violation.** Law 2 governs *outer* margin — space a child claims in its parent's flow. Padding is inside the child's own box; it is the child describing its own inset, which is exactly the kind of decision a child is allowed to make.

**Full-bleed background with constrained content** is the composition of §4.3 and this rule:

```html
<main class="page-grid sections--banded">
  <section class="band band--sunken bleed-full">
    <div class="page-grid"><div class="stack">…content, back in the column…</div></div>
  </section>
</main>
```

The outer `.band` paints and pays for the boundary; the nested `.page-grid` puts the content back on the content column. No negative margins, no `100vw`, no `overflow-x: hidden` on `<body>` to hide the damage.

---

## 7. Alignment

**Mathematical alignment is what the box model does. Optical alignment is what the eye reads.** They disagree, and when they do the eye wins.

**Icons.** A 24px icon box beside 16px text is mathematically centred and optically low, because the glyph inside the icon box rarely fills it and type has more mass above its baseline than below. Fix the *asset* — correct the SVG's `viewBox` so the mark fills its box consistently across the set — not the layout. Only when the asset cannot be fixed, use `.u-optical-up` (`--space-px`). If you need more than `--space-0-5` of nudge, the asset is wrong.

**Hanging punctuation.** A pull quote that opens with `"` is optically indented by the quote mark's width, so its first line appears to start right of the paragraphs below it. Pull the mark into the margin (`.u-hang-punct`, `calc(var(--space-0-5) * -1)`) so the *letters* align. Same for bulleted lists set flush and for a leading `—`.

**Button label centring with a trailing icon.** `justify-content: center` on a button containing `label + icon` centres the *pair*, so the label reads as shifted left. Three honest options, in order: give the button `display: grid; grid-template-columns: 1fr auto 1fr` and let the label sit in the centre track; or accept the pair-centring and keep it consistent across every button (consistency beats correctness here, because a mix is what actually looks broken); or add `padding-inline-end` reduced by the icon's width via the button's Tier-3 var. Never a magic `margin-left: -4px`.

**Baseline alignment across columns.** Text in two columns of different sizes aligns on its *boxes* by default, so a 35px heading and a 16px paragraph starting on the same row do not share a baseline. `align-items: baseline` on the row fixes it (`.row--baseline`, `.cluster--baseline`). Use it wherever text of mixed sizes sits on one line: a title with a trailing badge, a metric with its unit, a label with its value.

**The edge rule.** *Every edge in a layout must align to a shared vertical line, or be deliberately and visibly different.* Near-alignment — 2px, 6px off — is the single most reliable way to make a professional layout read as amateur, because the eye detects the mismatch without being able to name it.

**How to check it, in 60 seconds:**

1. Take a screenshot and draw vertical rules down every left edge on the page. Count the distinct lines. A well-built page has **two or three** (page gutter, content edge, and maybe an indented rail). Five or more means something is off-grid.
2. In DevTools, add `outline: 1px solid red` to `*` (never `border` — it changes layout). Misalignments become obvious instantly.
3. Enable the grid overlay on `.page-grid` and confirm every section's content starts on `content-start`.
4. The usual culprits, in order: a component with its own `padding-inline` inside an already-guttered `.center`; an icon with asymmetric internal padding; a card with `border` on some variants and not others (1px per side, so a bordered card's content sits 1px in).

---

## 8. Sizing

**`min()` / `max()` / `clamp()` over media queries for widths.** `min(100%, var(--measure-prose))` is "as wide as available, capped at the measure" — the full responsive behaviour of a text column, as one declaration, with no breakpoint at which it changes character. `clamp()` is the same idea with a floor.

**Percentage widths are usually wrong.** `width: 33.333%` means "a third of whatever my parent happens to be", which is a statement about an ancestor rather than about this element. It does not account for gaps (so `3 × 33.333% + 2 × gap` overflows), it does not respond to content, and it breaks the moment the component moves. Use `1fr`, `flex-grow`, or `minmax()` — all of which reason about *available* space after gaps are paid.

Percentages remain correct for **ratios and thresholds**: `min-inline-size: 60%` as a wrap threshold, `max-inline-size: 100%` as a clamp, `min(80%, …)` as a peek. That is a different use — not "be this wide", but "relate to the container this way".

**`min-width: 0` on flex and grid children.** The automatic minimum size of a flex item and of a grid item in an `auto`-minimum track is its **min-content** size. So a long word, a `<pre>`, a `<table>` or an un-wrapped URL refuses to shrink and overflows the parent — and `text-overflow: ellipsis` on a descendant silently does nothing, because the ancestor never got narrow. Fixes: `min-inline-size: 0` on the flex child (`.row > *`, `.grid > *`, `.split > *`), `minmax(0, 1fr)` in grid templates, and `.u-wrap-anywhere` for content that genuinely contains hashes and URLs.

**`aspect-ratio` over padding-top hacks.** `aspect-ratio: 16 / 9` with `inline-size: 100%` reserves the box before the asset loads and needs no wrapper. The old `padding-top: 56.25%` trick required a wrapper plus an absolutely positioned child, which is three elements and a magic number to express one ratio. Note that `aspect-ratio` yields to an explicit size in both axes, and that a child taller than the ratio will overflow unless the frame sets `overflow: hidden` — `.frame` does.

**`dvh` / `svh` / `lvh` — the mobile viewport problem.** On mobile, browser chrome hides on scroll, so "the viewport" has three sizes:

| Unit | Means | Use for |
|---|---|---|
| `lvh` / `lvb` | **L**argest — chrome hidden. **This is what `vh` equals.** | Almost nothing |
| `svh` / `svb` | **S**mallest — chrome visible | **Default choice.** Content is always fully visible; never cut off on load |
| `dvh` / `dvb` | **D**ynamic — resizes live as chrome hides | Fixed overlays and full-screen modals only |

`100vh` is a bug on mobile: it equals `lvh`, so a "full-screen" hero is taller than the visible screen on first paint and its bottom content — usually the CTA — is below the fold. `100dvh` is not the fix for page content either: it *reflows the page mid-scroll*, which is a worse experience than a slightly short hero. `100svh` is the default; `.cover--live` opts into `dvh` where live resizing is actually wanted.

Prefer the logical forms (`svb`, `dvb`) in block-axis properties so vertical writing modes do not break.

---

## 9. Whitespace as structure

Whitespace is not what is left over. It is the primary carrier of grouping, and on a well-built page it does the job that borders and boxes do on a badly-built one.

**Macro whitespace** — `--space-section`, `--space-subsection`, page gutters — sets the page's confidence and pace. It is what makes a layout read as premium or as cramped, and it is the first thing sacrificed under content pressure and the first thing to restore.

**Micro whitespace** — the proximity ladder, `--pad-card`, line-height, tracking — sets legibility and component quality. It is what makes a card feel considered rather than assembled.

**The rule: space communicates grouping.** Gestalt proximity is not a metaphor here; it is the mechanism. Things closer together are read as one thing, *before* the reader processes any content. That is why `tokens.css` names the ladder by relationship rather than by size — `--gap-related`, `--gap-separate`, `--gap-distinct` — and why picking a gap means answering "how strongly do these belong together?", not "how many pixels looks right?".

The corollary is the one people get wrong: **a heading belongs to the content that follows it, not the content above it.** `--space-subsection` above, `--gap-related` below. Get this backwards and the page reads as a list of headings with orphaned paragraphs.

### The diagnostic for "this feels cramped / sloppy"

Nine times in ten it is not the *amount* of space. It is **inconsistent gaps at the same hierarchy level** — two things that are peers, separated by different amounts. The eye reads the difference as meaning, finds no meaning, and registers it as noise.

How to find it:

1. Screenshot the section. List every vertical gap in it with a measuring tool.
2. Group the gaps by what they separate — *peers* (two cards, two form fields, two list items) versus *levels* (a heading and its body).
3. **Every gap within one group must be identical.** Two card gaps of 16px and 20px on the same page is the bug, regardless of which is "right".
4. Find the offender. It is almost always one of: a component setting its own `margin-bottom` (Law 2 violation — the smoking gun); a last-child margin that a sibling's margin is collapsing with; a `<br>` or empty `<p>` from a CMS; a gap on the parent *plus* padding on one child.
5. Fix it by deleting, not by adding. Remove the child's margin and let the parent's `gap` govern. If the result is now uniformly too tight, re-point the parent's Tier-3 var one rung up the ladder.

Second-commonest cause: **more than three distinct gap values in one section.** If a section uses five, two of them are the same decision expressed twice. Collapse them.

Third: **space that does not match the DOM's grouping.** Two fields are `--gap-related` apart but live in different fieldsets, while two fields in the same fieldset are `--gap-separate` apart. The visual grouping and the semantic grouping must agree, or sighted users and screen reader users get different documents.

---

## 10. Anti-patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| **Nested flex soup** — `display: flex` five levels deep, each with its own alignment | Nobody can predict where space comes from; changing one gap has effects three levels away; min-content overflow bugs multiply | Compose named primitives. If you cannot name each level (`stack > split > cluster`), the structure is wrong |
| **Fixed heights** (`height: 420px` on a card) | Breaks on translation (German is ~35% longer), on user font-size, on a two-line title. Content overflows or gets clipped | `min-block-size`, `aspect-ratio` for media, `.stack--fill` + `.stack__push-end` to align footers, subgrid to align internals |
| **`margin: 0 auto` scattered** | The same layout decision taken in 40 files; nobody knows which wrapper is the constraining one | `.center`, once |
| **Absolute positioning for layout** | Removes the element from flow, so nothing below it knows it exists; overlaps at other sizes; breaks reflow, zoom and reading order | Flow layout. Absolute is for **overlay only** (`.imposter`). If you reached for it to "just move this up a bit", the parent's gap is wrong |
| **`vh` on mobile** | `100vh` = `lvh` = the chrome-hidden viewport, so the bottom of a "full-screen" hero is below the fold on load | `100svh` by default; `100dvh` only for fixed overlays |
| **Negative margins as a layout tool** | Invisible to the layout algorithm; fights `overflow`; overlaps unpredictably; makes full-bleed break inside `overflow: hidden` ancestors | The `.page-grid` named-line breakout. Negative values are licensed only for sub-2px optical corrections (`.u-hang-punct`) |
| **Magic numbers to "fix" alignment** (`margin-top: -3px`) | Treats the symptom. The 3px comes from a line-height, an icon viewBox or a border, and will change | Find the source. Fix the asset, the `--leading-*`, or the padding. If it is genuinely optical, use the named `.u-optical-*` utility so it is greppable |
| **One-off media queries inside components** | Encodes a viewport assumption into something reusable. Correct until the card lands in a sidebar, then wrong and expensive to find | `@container`, or an intrinsic threshold. Media queries live in the page shell |
| **`gap` on the parent *and* margin on the child** | The two add. The seam is 1.5× everywhere and nobody knows which to remove | Delete the child's margin. Always. Law 2 |
| **`overflow-x: hidden` on `<body>`** | Hides the symptom of a layout that overflows, and silently kills `position: sticky` for every descendant | Find the overflow (usually a missing `min-inline-size: 0` or a `100vw`). Fix the cause |
| **`width: 100vw` for full-bleed** | `vw` includes the scrollbar gutter on desktop Windows/Linux, so it is ~15px too wide and produces horizontal scroll | `.bleed-full` in `.page-grid` |
| **A twelfth primitive invented in a component file** | The set stops being closed; the next person invents a thirteenth | Law 8 gate. If it passes and recurs, it moves to `layout.css` |

---

## 11. Audit (Law 9)

Run before any layout work ships.

**Tokens and structure**

- [ ] `grep -nE '[0-9]+(px|rem|em)' layout.css` returns **only** `@media` / `@container` preludes.
- [ ] Every `var(--…)` resolves to a token in `tokens.css` or a Tier-3 var declared in the same file.
- [ ] Every Tier-3 default is a **Tier-2** token — no `var(--space-6)` in a primitive (that skips a tier).
- [ ] No component file contains `display: grid`, `display: flex`, or a `margin-block` / `margin-top` on itself.
- [ ] No `!important`, no ID selectors, no selector that wins by depth. Order in `@layer layout` decides (Law 5).

**Law 2**

- [ ] No child sets outer margin for spacing. Auto margins for alignment and owl rules written in the parent are the only exceptions.
- [ ] Every `gap` value comes from the proximity ladder, chosen by relationship.
- [ ] Exactly one of gap mode / band mode per page shell.

**Responsive**

- [ ] Every breakpoint literal has its `--bp-*` token named in a comment.
- [ ] No `@media` inside a component file.
- [ ] Every component correct at 320px, 768px, 1440px **and inside a 288px rail**.
- [ ] Test at 200% browser zoom and at 320px width simultaneously — the WCAG 1.4.10 reflow condition. No horizontal scroll.

**Overflow**

- [ ] `min-inline-size: 0` or `minmax(0, 1fr)` present on every flex/grid child that can hold long content.
- [ ] Paste a 60-character unbroken string into every text slot. Nothing overflows.
- [ ] No `overflow-x: hidden` on `html` or `body`.

**Alignment and rhythm**

- [ ] Count distinct left edges on a screenshot: 2–3 expected.
- [ ] Count distinct gap values per section: ≤ 3, and all peer gaps identical.
- [ ] Headings sit closer to what follows than to what precedes.

**Content stress**

- [ ] Every string doubled in length; every string emptied. Layout holds both.
- [ ] `--density: 0.875` and `1.125` on `<body>`: nothing collides, nothing overflows.
- [ ] Images disabled: `.frame` still reserves its box; CLS stays at 0.

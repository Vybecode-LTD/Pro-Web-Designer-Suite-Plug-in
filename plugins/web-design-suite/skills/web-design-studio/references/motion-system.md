# Motion System

Motion is the only part of an interface that happens *to* the user rather than *for* them. They cannot skim it, skip it, or read it at their own pace. That asymmetry is why this file is mostly a set of constraints: every 100ms you spend is 100ms of someone's attention you took without asking.

Ground truth is section 8 of `assets/starter/styles/tokens.css` — `--dur-*`, `--ease-*`, `--motion-*`. Law 1 applies without exception: **a `transition` or `animation` declaration containing a literal duration or a literal `cubic-bezier()` is a bug.** The reduced-motion block in `tokens.css` works by re-pointing `--dur-*`; a hard-coded `300ms` is invisible to it and will keep animating for a user who asked it to stop. That is not a style violation, it is an accessibility defect.

## Contents

1. [Motion has jobs, not vibes](#1-motion-has-jobs-not-vibes)
2. [Duration](#2-duration-is-a-function-of-distance-and-size)
3. [Easing](#3-easing-semantics)
4. [Choreography](#4-choreography)
5. [Performance](#5-performance)
6. [Scroll-driven animation](#6-scroll-driven-animation)
7. [Micro-interaction catalog](#7-micro-interaction-catalog)
8. [Reduced motion](#8-reduced-motion)
9. [Anti-patterns](#9-anti-patterns)
10. [Ship checklist](#10-ship-checklist)

---

## 1. Motion has jobs, not vibes

There are exactly four legitimate jobs. **Every animation in a build must name one in a comment, or be deleted.** This is the whole governance mechanism; without it a codebase accumulates motion the way a desk accumulates cables.

| Job | What it answers for the user | Typical patterns |
|---|---|---|
| **1. Causality / origin** | "Where did this come from, and what did I do to cause it?" | Menu scaling out of its trigger, toast sliding from the edge it lives on, a row expanding from the chevron that was clicked |
| **2. Spatial continuity** | "Is this the same object I was just looking at, or a new one?" | Shared-element transition from card to detail page, list reorder, tab panel sliding in the direction of travel |
| **3. Attention direction** | "Something changed that you did not cause — look here" | A newly inserted row flashing its background, an error field shaking once, a badge count incrementing |
| **4. Brand personality** | "This product has a temperament" | Hero reveal, logo lockup, a signature overshoot on the primary CTA |

Two rules that follow:

- **Jobs 1–3 are functional and survive scrutiny. Job 4 is discretionary and must be rationed.** Personality motion belongs on first-impression surfaces (hero, marketing sections, onboarding, empty states) and nowhere a person goes fifty times a day. A spring on the "Save" button is charming on Monday and grating by Thursday.
- **An animation with no job is not neutral, it is cost.** It costs main-thread time, it costs the user's latency budget, and it costs the next engineer the ten minutes needed to work out whether it is load-bearing.

```css
/* job: causality — the menu grows from the button that opened it */
.menu { transition: opacity var(--motion-enter), transform var(--motion-enter); }
```

**The test for job 2.** If an element is present before and after a state change and the user needs to know it is the same element, it must move continuously. If it is genuinely a different thing, it should cross-fade or replace, not slide. Sliding two unrelated things past each other is a lie about their relationship.

---

## 2. Duration is a function of distance and size

The eye tracks a moving object at a roughly constant angular velocity. Therefore **duration scales with the distance travelled**, not with importance, and not with how much the animation cost to build. A 4px toggle knob and a full-height drawer should not share a duration.

The numbers that hold up in practice:

- **Under ~100ms** reads as instantaneous — no motion is perceived, only a state change. Correct for binary swaps where the *fact* matters and the *transit* does not.
- **200–300ms is the sweet spot for most UI.** Below ~150ms the eye cannot resolve the path, so the continuity information in job 2 is lost — you paid for an animation and delivered a jump cut. Above ~350ms the user has already decided what they want next and is waiting on you. Two of the five tokens (`--dur-base` 220ms, `--dur-slow` 320ms) live in this band on purpose.
- **Exit is faster than enter, by roughly 30–50%.** Entering, the user needs to *read* a new thing: the motion is informative and they are receiving. Leaving, they have already made their decision and the object is dead to them — every remaining frame is latency. Hence `--motion-enter` is `--dur-base` (220ms) and `--motion-exit` is `--dur-fast` (140ms). This is also why the pair exists as two role tokens rather than one: symmetric enter/exit is the single most common motion mistake.
- **Large surfaces need longer than small ones**, even at the same distance, because a big object sweeping the viewport at small-object speed reads as violent. A full-screen sheet at 140ms feels like a glitch; at 320ms it feels like a sheet.
- **Nothing in a UI exceeds 500ms.** `--dur-slower` (480ms) is the ceiling and is reserved for route transitions and large first-paint reveals — things that happen once per navigation, not once per click.

### Element × distance → token

| Element | Travel | Enter token | Exit token | Why |
|---|---|---|---|---|
| Checkbox tick, toggle knob, radio dot | 0–8px | `--motion-instant` | `--motion-instant` | The state is the message; transit carries no information |
| Hover background, focus ring, icon color | none (no travel) | `--motion-hover` | `--motion-hover` | Must feel attached to the cursor; >200ms and the button feels sticky |
| Button press depress | 1–2px | `--motion-instant` | `--motion-hover` | Down must be immediate; release can relax |
| Tooltip, popover | 4–8px | `--motion-enter` | `--motion-exit` | Small, near its trigger |
| Dropdown / select menu | 8–16px | `--motion-enter` | `--motion-exit` | Origin matters (job 1); scale from the trigger edge |
| Toast / snackbar | 16–24px | `--motion-enter` | `--motion-exit` | Enters from the edge it docks to |
| Tab panel swap | cross-fade or one panel width | `--dur-base` | — | Cross-fade for unrelated panels; slide only if the tabs are ordered |
| Accordion / disclosure | content height | `--motion-expand` | `--motion-expand` | Symmetric here: the user is inspecting, not dismissing |
| Modal dialog | 8–16px + scale | `--motion-enter` | `--motion-exit` | Scrim fades at the same duration, never longer |
| Drawer / side sheet | 280–400px | `--dur-slow` | `--dur-base` | Large surface, long travel |
| Bottom sheet (mobile) | 50–90vh | `--dur-slow` | `--dur-base` | Same, plus the thumb expects gravity — `--ease-out` in, `--ease-in` out |
| Page / route transition | full viewport | `--dur-slower` | `--dur-base` | Once per navigation; must not delay content (§9) |
| List item enter (staggered) | 8–16px | `--motion-enter` per item | — | See stagger, §4 |
| Skeleton shimmer, spinner | looping | `--motion-loop` | — | Loops need constant velocity, not easing. `--dur-loop` (900ms) stays out of the reduced-motion block: a spinner that stops reads as a hung page |

**Travel distance is a spacing decision.** A menu that slides in from 8px should reference the spacing scale, not the number 8. The starter's `tokens.css` declares three travel roles, Tier 2:

```css
/* tokens.css, Tier 2 */
--motion-travel-xs: var(--space-1);   /*  4px — hover lift, press nudge    */
--motion-travel-sm: var(--space-2);   /*  8px — tooltip, menu, popover     */
--motion-travel-md: var(--space-4);   /* 16px — card, sheet, toast         */
```

Never write `translateY(8px)`. The day the brand asks for "more movement" you want one line to change, not forty.

---

## 3. Easing semantics

Easing is the difference between an object and a rectangle whose coordinates changed. Get it right and you can shorten every duration by ~20% without anyone noticing the difference — which is the cheapest performance win in the whole system.

### The rule, and why

| Situation | Token | Physical story |
|---|---|---|
| Something **arriving** (enter, expand open, appear) | `--ease-out` | It came from somewhere off-stage where it was already moving. It arrives fast and decelerates into place, like a hand setting something down. |
| Something **leaving** (exit, collapse, dismiss) | `--ease-in` | It accelerates away and is gone. The user has stopped caring; do not make them watch it decelerate politely. |
| Something **moving within view** (reorder, reposition, expand where both ends are visible) | `--ease-in-out` | A real object at rest must accelerate and must decelerate. Both ends are on screen, so both ends are observed. |
| **Continuous** (spinner, progress, shimmer, marquee) | `--ease-linear` | A constant-velocity loop. Any easing on a loop produces a visible pulse at the seam. |
| **Playful emphasis** (job 4 only) | `--ease-spring` | Overshoots ~10% and settles. Rationed. |

The mnemonic: **ease-out for things you are receiving, ease-in for things you are discarding.** If both ends of the motion are visible, you are neither receiving nor discarding — use `--ease-in-out`.

### Reading a cubic-bezier

`cubic-bezier(x1, y1, x2, y2)` defines two control points, P1 and P2, on a curve from (0,0) to (1,1). **x is time, y is progress.** The curve is pulled toward each control point without reaching it.

- **y1 high relative to x1** → the curve leaves fast. Most of the distance is covered in the first slice of time. That *is* an ease-out.
- **y1 = 0 with x1 large** → the curve is flat at the start: nothing happens for a while. That is an ease-in.
- **y > 1** → overshoot. The element passes its target and comes back.
- **y < 0** → anticipation. The element pulls backwards before moving forward. Almost always wrong in UI; it delays the response to an input the user already gave.
- **x outside 0–1 is invalid** and the whole declaration is dropped. y is unbounded.

Measured behaviour of the shipped tokens — this is what the abstraction actually does:

| Token | Progress at 10% of time | 25% | 50% | 75% | Peak |
|---|---|---|---|---|---|
| `--ease-out` `(0.22, 1, 0.36, 1)` | 40% | **77%** | 96% | 99.7% | 1.00 |
| `--ease-in` `(0.64, 0, 0.78, 0)` | 0% | 0.3% | 3.9% | 24% | 1.00 |
| `--ease-in-out` `(0.65, 0, 0.35, 1)` | 0.9% | 7% | **50%** | 93% | 1.00 |
| `--ease-spring` `(0.34, 1.56, 0.64, 1)` | 40% | 82% | 109% | 106% | **1.098** |
| `ease` (browser default) `(0.25, 0.1, 0.25, 1)` | 9.5% | 41% | 80% | 96% | 1.00 |

`--ease-out` covering 77% of the distance in the first quarter of the time is the entire reason a 220ms enter feels instant: perceptually it *is* over at ~60ms, and the remaining 160ms is a settle the user reads as weight rather than delay.

### Why the browser's `ease` is wrong for almost everything

`ease` is a gentle ease-in-out. It spends its first 10% of time covering 9.5% of the distance — it hesitates. Three consequences:

1. **On enter it feels unresponsive.** The user clicked; the first thing they perceive is nothing happening. Compare `--ease-out`'s 40%.
2. **On exit it wastes the tail.** 20% of the time is spent creeping the last 4%.
3. **It is symmetric**, and almost no UI motion is symmetric — enter and exit have different jobs (§2).

`ease` is the default because CSS needed one, not because it is right. `transition: opacity 200ms` silently selects it. Always name the easing.

### Authoring a new curve deliberately

You should need this rarely. When you do:

1. Decide the story. "Arrives with weight" → strong ease-out. "Snaps then settles" → mild overshoot.
2. Set **P1 (x1, y1) = the departure**. For an ease-out, keep x1 small (0.1–0.3) and y1 near or at 1.
3. Set **P2 (x2, y2) = the arrival**. Keep y2 = 1 and use x2 to control the length of the settle: larger x2 (0.6–0.9) = shorter tail, snappier; smaller x2 (0.2–0.4) = long luxurious glide.
4. Sanity-check the progress at 25% and 50% before committing. If progress at 50% is below 50% on an "arriving" curve, you have accidentally written an ease-in.
5. Add it to `tokens.css` as a named Tier 1 `--ease-*` with a one-line comment stating its job. Never inline it.

### Springs, and `linear()`

A bezier has no physics: it cannot express "this was moving when it was interrupted", and it cannot overshoot more than once. A **spring** (mass, stiffness, damping) can, and it is what makes a drag-release feel like the object has inertia.

**Use a spring when the motion is interruptible and driven by continuous input** — drag-to-dismiss, pull-to-refresh, a sheet the thumb is holding, a canvas element being flung. The animation must be able to retarget mid-flight from its current velocity, which a bezier fundamentally cannot do. In those cases a physics library (Motion, `react-spring`, Framer) earns its ~15–30kB.

**Do not add the dependency for a decorative bounce.** `--ease-spring` covers that, at zero cost.

For non-interruptible springs, CSS's `linear()` expresses a real spring curve natively — it takes an arbitrary number of progress stops and interpolates linearly between them, approximating any curve including ones that overshoot:

```css
/* A real spring: m=1, k=830, c=43.2 → ζ=0.75, ~2.8% overshoot, settles in ~280ms.
   linear() is normalised across whatever duration you declare, so changing the
   duration rescales the physics. Re-derive if you move off --dur-slow. */
:root {
  --ease-spring-physical: linear(
    0, 0.079 5.6%, 0.250 11.1%, 0.445 16.7%, 0.624 22.2%, 0.769 27.8%,
    0.876 33.3%, 0.949 38.9%, 0.993 44.4%, 1.017 50%,  1.027 55.6%,
    1.028 61.1%, 1.025 66.7%, 1.020 72.2%, 1.014 77.8%, 1.009 83.3%,
    1.005 88.9%, 1.003 94.4%, 1.001
  );
  --motion-spring: var(--dur-slow) var(--ease-spring-physical);
}

/* Gate it; do not stack two declarations. The second would read a custom
   property, so no parser can reject it: it wins, and where linear() is
   unknown it computes to nothing and the sheet loses its transition. */
.sheet { transition: transform var(--motion-emphasis); }
@supports (transition-timing-function: linear(0, 1)) {
  .sheet { transition: transform var(--motion-spring); }
}
```

**Support.** `linear()` is in Chromium 113+, Firefox 112+, Safari 17.2+ — safe as a progressive enhancement, and the two-declaration fallback above is the whole mitigation: an unsupported value makes the declaration invalid at parse time, so the previous one survives. Check current status before relying on it for anything load-bearing.

**Deriving the stops.** `progress(t) = 1 − e^(−ζωₙt)·(cos(ω_d t) + (ζωₙ/ω_d)·sin(ω_d t))` with `ωₙ = √(k/m)`, `ζ = c/(2√(km))`, `ω_d = ωₙ√(1−ζ²)`. Sample 16–24 points to the settle time. Keep ζ in 0.6–0.85 for UI: below 0.5 it wobbles visibly, above 0.9 you have paid for a spring and got an ease-out.

---

## 4. Choreography

### Stagger

Animating a list all at once reads as one block moving. Staggering reads as items arriving.

**The band is 20–60ms per item.** Below 20ms the offset is imperceptible and you have paid complexity for nothing. Above ~60ms the *last* item's delay dominates the perceived duration: ten items at 80ms means the tenth starts 720ms after the click, and the list feels slow no matter how fast each item is.

```css
/* job: causality — results arrive in reading order after the query resolves.
   40ms is the midpoint of the 20–60ms band, composed from a token so that
   the reduced-motion override collapses it too. */
.result {
  --stagger-step: calc(var(--dur-instant) / 2);   /* 40ms; 1ms under reduce */
  animation: rise var(--motion-enter) both;
  animation-delay: calc(var(--index) * var(--stagger-step));
}

@keyframes rise {
  from { opacity: 0; transform: translateY(var(--motion-travel-sm)); }
  to   { opacity: 1; transform: none; }
}
```

**Cap the total.** Stagger the first 6–8 items and give everything after them the same final delay. A 200-row table staggered honestly takes eight seconds.

```css
.result:nth-child(n + 8) { animation-delay: calc(7 * var(--stagger-step)); }
```

**Stagger direction follows reading order** — top to bottom, leading to trailing. A grid staggers along its diagonal from the origin corner, never randomly.

### Related moves together, unrelated moves independently

This is Gestalt common fate, and it is the rule that makes choreography legible rather than busy.

- Elements that belong to one object share one duration, one easing, and one delay. A card's image, title and body do **not** get three different entrances; the card enters, and they are on it.
- Elements that are genuinely independent — a toast and a modal, a sidebar and the content — animate on their own timelines and may overlap.
- **Never animate a parent and its children on different curves.** The child's motion is composed with the parent's transform, and the result is a rubber-banding artefact nobody designed.

### Shared-element transitions

When the same object exists on both sides of a state change, move it; do not fade one out and the other in. The user's eye stays locked on it and the new screen arrives already understood. Classic cases: grid thumbnail → detail hero, avatar in a list → avatar in a profile header, collapsed card → expanded card.

Two implementation routes: FLIP (§5, works everywhere, same-document only) and the View Transitions API.

### View Transitions API

```css
/* Same-document: name the element on both sides. Names must be unique per
   snapshot — two elements with the same view-transition-name at once throws. */
@layer components {
  .hero-image { view-transition-name: hero; }
}

/* Cross-document: opt both pages in. */
@view-transition { navigation: auto; }

/* The generated pseudo-elements belong to the document, not to a component,
   so they are styled in base, with tokens like anything else. Set the
   longhands: the `animation` shorthand would reset the UA's animation-name. */
@layer base {
  ::view-transition-old(hero),
  ::view-transition-new(hero) {
    animation-duration: var(--dur-slow);
    animation-timing-function: var(--ease-in-out);
  }
  ::view-transition-group(root) { animation-duration: var(--dur-base); }

  @media (prefers-reduced-motion: reduce) {
    ::view-transition-group(*),
    ::view-transition-old(*),
    ::view-transition-new(*) { animation: none; }
  }
}
```

```js
// Same-document. Feature-detect; never branch your data flow on it.
function navigate(render) {
  if (!document.startViewTransition) return render();
  return document.startViewTransition(render).finished;
}
```

**Support, honestly.** Same-document view transitions: Chromium 111+, Safari 18+, Firefox from 144. Cross-document (`@view-transition`): Chromium 126+, Safari 18.2+, Firefox still landing at the time of writing. **Verify on caniuse before you rely on it** — this is the fastest-moving area in this document.

**Progressive enhancement framing, non-negotiable:** the navigation must be complete and correct with zero transition. `startViewTransition` wraps a DOM update you were going to do anyway; if the API is absent, the update still happens, instantly. Never put state changes, data fetches or focus management *inside* the callback and nowhere else — a browser without the API must still run them. And move focus explicitly after the transition resolves; the API snapshots pixels, not focus.

---

## 5. Performance

### The compositor-only rule

The browser renders in stages: **style → layout → paint → composite**. A property animation that dirties an earlier stage re-runs every later one, on the main thread, every frame.

- **`transform` and `opacity` skip to composite.** They are handled on the compositor thread, off the main thread, and survive JavaScript jank. These are the only two that are cheap on every engine, on every device.
- **`filter` and `backdrop-filter` are composited in modern Chromium and WebKit but are not free**: `blur()` cost scales with the *area* being blurred, so a full-viewport backdrop blur on a mid-range Android will drop frames even though it never touches layout. Profile before shipping one.
- **`clip-path` can be composited** when the two keyframes use the same shape function with the same point count. Mismatch the functions (`inset()` → `polygon()`) and it silently falls back to a discrete jump.
- **`height`, `width`, `top`, `left`, `margin`, `padding`, `font-size` trigger layout** — the browser recomputes geometry for that element *and* everything its geometry affects, then repaints, then composites. 60 times a second. This is the single biggest cause of janky UI animation.
- **`box-shadow`, `background-color`, `border-color`, `color` trigger paint** — cheaper than layout, still main-thread. Fine for a `--motion-hover` on one button; not fine on 200 table rows at once.

**Substitutions that are almost always available:**

| Instead of | Animate | Note |
|---|---|---|
| `left` / `top` | `transform: translate()` | Identical visual result |
| `width` / `height` | `transform: scale()` | Distorts children — counter-scale them, or cross-fade instead |
| `height: 0 → auto` | `grid-template-rows: 0fr → 1fr` | The modern accordion; see §7 |
| `box-shadow` on hover | `opacity` of a pseudo-element holding the shadow | Keeps a large blur off the paint path |
| `background-color` on a list | `opacity` of an overlay pseudo-element | One composited layer instead of N paints |

### FLIP

FLIP animates a layout change you have already let the browser perform — which means you get real layout (grid, flex, wrapping, `auto` heights) **and** a compositor-only animation.

**F**irst: measure. **L**ast: apply the change and measure again. **I**nvert: transform the element back to where it was. **P**lay: animate the transform to `none`.

```js
// Tokens are the source of truth for JS animations too. WAAPI does NOT read
// prefers-reduced-motion for you; reading --dur-* is what makes it obey.
const tokenMs = (name, el = document.documentElement) => {
  const v = getComputedStyle(el).getPropertyValue(name).trim();
  return v.endsWith('ms') ? parseFloat(v) : parseFloat(v) * 1000;
};
const tokenStr = (name, el = document.documentElement) =>
  getComputedStyle(el).getPropertyValue(name).trim();

function flip(el, mutate) {
  const first = el.getBoundingClientRect();
  mutate();                                   // forces the real layout
  const last = el.getBoundingClientRect();

  const dx = first.left - last.left;
  const dy = first.top  - last.top;
  const sx = first.width  / last.width;
  const sy = first.height / last.height;

  if (Math.abs(dx) < 1 && Math.abs(dy) < 1 &&
      Math.abs(sx - 1) < 0.01 && Math.abs(sy - 1) < 0.01) return null;

  return el.animate(
    [
      { transformOrigin: 'top left',
        transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})` },
      { transformOrigin: 'top left', transform: 'none' },
    ],
    {
      duration: tokenMs('--dur-slow'),
      easing:   tokenStr('--ease-in-out'),   // both ends visible → in-out
      fill:     'none',
    }
  );
}
```

Three things people get wrong:

1. **Batch the reads.** For a list, measure *every* item, then mutate once, then measure every item again. Interleaving read/mutate/read per item is layout thrashing and will be slower than the naive version.
2. **Scale distorts descendants.** Text scaled from 0.6 → 1 looks smeared. Either animate position only (`translate`, no `scale`), or apply the inverse scale to a single wrapper child, or cross-fade the contents over the top.
3. **Interrupting.** If a second FLIP starts before the first finishes, `getBoundingClientRect()` returns the *animating* rect. Either call `getAnimations().forEach(a => a.finish())` on the element first, or read the untransformed box by temporarily removing the transform.

### `will-change` discipline

`will-change` promotes an element to its own compositor layer *in advance*, so the first frame is not spent doing the promotion.

- **It helps** only when you know an animation is imminent and the promotion cost is visible — typically set on `:hover`/`:focus-within` of the parent, a beat before the child animates.
- **Leaving it on hurts**, concretely: each promoted layer holds its own GPU texture (width × height × 4 bytes), and hundreds of them exhaust memory on mobile and force the compositor to do more work per frame, not less. A promoted layer can also change text rasterisation, producing a visible font-weight shift the moment the property is applied.
- **Never put it in a base rule.** `.card { will-change: transform; }` on a 60-card grid is a bug.

```css
.card { transition: transform var(--motion-hover); }
.card:hover { transform: translateY(calc(var(--motion-travel-xs) * -1)); }
.card-grid:hover .card { will-change: transform; }   /* armed only while relevant */
```

The browser already auto-promotes elements with active `transform`/`opacity` animations. **If you cannot name the frame that `will-change` saves, delete it.**

### `content-visibility`

`content-visibility: auto` lets the browser skip style, layout and paint for off-screen subtrees. On a long marketing page with a dozen heavy sections it is often a larger win than any animation tuning.

```css
.section-heavy {
  content-visibility: auto;
  /* Required: without a size estimate the scrollbar jumps as sections render. */
  contain-intrinsic-size: auto 60vh;
}
```

Caveats: it creates a containment context (so `position: fixed` descendants and some `overflow` behaviour change), and skipped content is **still found by in-page search and still reachable by the accessibility tree** in current engines — but verify, because a rendering optimisation that hides content from `Ctrl+F` is a bug. Never apply it to above-the-fold content.

### Checking it in DevTools

An ordered procedure, not a vibe:

1. **Rendering panel → Frame Rendering Stats.** Run the interaction. If the frame graph drops below the display refresh rate, continue; if not, stop — you do not have a problem.
2. **Rendering panel → Paint flashing.** Green rectangles on every frame of the animation mean you are repainting. A composited animation flashes once (or never) after the first frame.
3. **Rendering panel → Layer borders.** Confirms what actually got promoted, and shows accidental layer explosions.
4. **Performance panel → record the interaction, 4× or 6× CPU throttle.** Look at the main-thread flame chart for purple (Layout) and green (Paint) bars repeating at frame cadence. Purple repeating = you are animating a layout property. Find the offending property in the "Layout" event's summary.
5. **Performance panel → the Animations track.** Chromium marks non-composited animations with a warning and *names the property that blocked compositing*. This is the fastest single answer.
6. **Throttle to "Mid-tier mobile" and retest.** A desktop GPU hides nearly every motion sin.

---

## 6. Scroll-driven animation

CSS can now drive an animation's progress from scroll position instead of from time, entirely off the main thread.

```css
/* A reading-progress bar tied to the document's scroll. */
.progress-bar {
  transform-origin: left center;
  animation-name: grow;
  animation-duration: auto;             /* the timeline owns it */
  animation-timing-function: var(--ease-linear);   /* progress tracks the scroll */
  animation-timeline: scroll(root block);
}
@keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }

/* Reveal each card as it crosses the viewport: view() tracks the element's own
   intersection with the scrollport. The range is the useful half of the API. */
.reveal {
  animation-name: rise-in;
  animation-fill-mode: both;
  animation-timing-function: var(--ease-out);   /* no duration: the timeline owns it */
  animation-timeline: view();
  animation-range: entry 10% cover 35%;
}
@keyframes rise-in {
  from { opacity: 0; transform: translateY(var(--motion-travel-md)); }
  to   { opacity: 1; transform: none; }
}

/* A named timeline, when the scroller is not an ancestor of the animated element. */
.gallery      { scroll-timeline: --gallery-x inline; }
.gallery-dots { animation-timeline: --gallery-x; }
```

- `scroll()` — progress across a **scroll container's** full range. Arguments: the scroller (`nearest`, `root`, `self`) and the axis (`block`, `inline`, `x`, `y`).
- `view()` — progress across an **element's** pass through the scrollport. Paired with `animation-range` (`cover`, `contain`, `entry`, `exit`, `entry-crossing`, `exit-crossing`) this replaces essentially every "animate on scroll" library.
- **What it replaces:** AOS, ScrollMagic, hand-rolled `IntersectionObserver` reveal code, and `scroll` listeners driving `style.transform`. Those all run on the main thread and stutter under load; this does not.

**Support.** Chromium 115+, Safari 26+; Firefox has been implementing behind a flag. Treat it as progressive enhancement: everything must be visible and usable with the timeline ignored. The safe authoring shape is to put the *hidden* state inside the feature query, so an unsupporting browser simply never hides the content:

```css
@supports (animation-timeline: view()) {
  @media (prefers-reduced-motion: no-preference) {
    .reveal { animation-name: rise-in; animation-fill-mode: both;
              animation-timing-function: var(--ease-out); animation-timeline: view(); }
  }
}
```

Note the nested reduced-motion query: **scroll-driven animations have no duration**, so the `--dur-*` collapse in `tokens.css` does not touch them. They must be disabled explicitly. This is the one place the token mechanism does not save you.

### Scroll hijacking: don't

Overriding the scroll wheel to snap between full-screen panels, animate at a scroll rate you chose, or pause the page while something plays. The specific harms:

1. **It breaks the scroll-position contract.** A wheel notch, a spacebar and a trackpad flick have learned meanings. Redefining them means the user has no model of how far anything will move.
2. **It breaks find-in-page.** `Ctrl+F` scrolls the document to a match. A hijacked scroller either ignores that or fights it, and the match is never shown.
3. **It causes motion sickness.** Large-area movement the user did not directly cause is a vestibular trigger (§8). Full-viewport parallax under a hijacked scroll is the worst case in common use.
4. **It fights trackpad and touch momentum.** Inertial scrolling emits a long tail of events. Hijack code written against wheel *clicks* either double-fires or swallows the tail, producing the characteristic "stuck between sections" bug.
5. **It breaks assistive tech and keyboard navigation.** `Page Down`, `Home`, `End` and screen-reader reading cursors all move the scroll position programmatically.

**The legitimate subset:** CSS `scroll-snap-type` (the browser stays in control, momentum and keyboard still work), `scroll-behavior: smooth` for in-page anchors (wrapped in a reduced-motion query), and scroll-*driven* animation as above, which reads scroll without commanding it.

---

## 7. Micro-interaction catalog

Each entry: **job · duration · easing · must not**.

### Button press
Job 1 (causality). `--motion-instant` down, `--motion-hover` up.
```css
.btn { transition: transform var(--motion-instant),
                   background-color var(--motion-hover); }
.btn:active { transform: scale(0.97); }
```
**Must not** move the button's layout box (use `transform` only), delay the actual action until the animation ends, or exceed ~3% scale — more and the label visibly reflows.

### Toggle / switch
Job 2 (continuity — the knob is one object moving). `--motion-instant`.
```css
.switch-knob { transition: transform var(--motion-instant); }
.switch[aria-checked="true"] .switch-knob { transform: translateX(100%); }
.switch { transition: background-color var(--motion-hover); }
```
**Must not** be the only indicator of state (colour + position + accessible name), and must not animate the track and knob on different durations.

### Checkbox check
Job 3 (attention — confirm the hit registered). `--motion-instant`.
```css
.check-path { stroke-dasharray: 22; stroke-dashoffset: 22;
              transition: stroke-dashoffset var(--motion-instant); }
.check-input:checked + .check :where(.check-path) { stroke-dashoffset: 0; }   /* 0,3,0: under the cap */
```
**Must not** delay the underlying form state. **Must not** animate on initial render — a form restoring 12 checked boxes should not draw 12 ticks.

### Input focus
Job 3. `--motion-hover`, and the ring itself is instant.
```css
.input { transition: border-color var(--motion-hover); }
.input:focus-visible { border-color: var(--border-focus); }   /* the ring is reset.css's outline */
```
**Must not** animate the ring's *size* (it reads as a pulse and fails Focus Appearance during the transit), must not exceed `--dur-fast`, and must never be suppressed under reduced motion — the ring appears, it just appears immediately.

### Loading — pick by expected duration

| Wait | Use | Why |
|---|---|---|
| **< 300ms** | Nothing | A spinner that flashes for 200ms is perceived as a glitch. Render the result. |
| **0.3–1s** | Spinner or inline indicator | Too short for a skeleton to be read as structure. |
| **1–10s, layout known** | Skeleton | It communicates the shape of what is coming, so the page does not reflow on arrival. Skeletons must match the real layout's boxes or they lie. |
| **> 10s, or determinate** | Progress bar with a percentage or step count | Indeterminate motion past ~10s reads as "broken". |

```css
.skeleton {
  background: linear-gradient(90deg,
    var(--bg-sunken) 25%, var(--bg-hover) 37%, var(--bg-sunken) 63%);
  background-size: 400% 100%;
  animation: shimmer var(--motion-loop) infinite;
}
@keyframes shimmer { from { background-position: 100% 0; }
                     to   { background-position: 0 0; } }

@media (prefers-reduced-motion: reduce) {
  .skeleton { animation: none; background: var(--bg-sunken); }
}
```
**Must not** shimmer forever with no timeout (show an error state), must not use a skeleton whose boxes differ from the loaded layout, and must not animate under reduced motion — the `--dur-*` collapse would make a 1ms infinite loop, which is worse than none. Kill the animation explicitly, as above.

### Success / error feedback
Job 3. `--motion-enter` in, `--motion-exit` out. Errors: no shake longer than one cycle at `--dur-fast`.
**Must not** rely on colour or motion alone — the message must be in text, announced via a live region, and the error must persist until resolved. **Must not** auto-dismiss an error. A success toast may auto-dismiss, never under 5 seconds.

### Hover lift
Job 4 (personality) with a touch of 1. `--motion-hover`.
```css
.card { transition: transform var(--motion-hover), box-shadow var(--motion-hover); }
@media (hover: hover) and (pointer: fine) {
  .card:hover { transform: translateY(calc(var(--motion-travel-xs) * -1));
                box-shadow: var(--elevation-raised); }
}
```
**Must not** shift layout — no `margin`, no `height`, nothing that moves a neighbour. **Must not** be the only affordance (the card must look interactive at rest). **Must not** apply on touch, where `:hover` sticks after the tap — hence the `(hover: hover)` guard.

### Drag affordance
Job 1. Pick-up `--motion-instant`; drop `--motion-enter`; reorder of displaced siblings via FLIP at `--motion-expand`.
```css
.draggable { transition: box-shadow var(--motion-instant),
                         transform var(--motion-instant); }
.draggable[data-dragging] { box-shadow: var(--elevation-overlay);
                            transform: scale(1.02); cursor: grabbing; }
```
**Must not** be the only way to perform the action — WCAG 2.5.7 requires a single-pointer alternative (see `references/accessibility.md`). **Must not** animate the dragged element's position; it follows the pointer with zero delay or it feels broken.

### Optimistic UI
Job 1. The state change is **immediate** — no animation at all on the happy path. The animation budget goes to the *rollback*: `--motion-enter` to restore the previous state, plus a persistent error message.
**Must not** show a spinner on the optimistically-updated element (that contradicts the optimism), and must not roll back silently.

---

## 8. Reduced motion

`prefers-reduced-motion: reduce` is set by a real person who gets sick, disoriented or distracted by movement. It is not a performance hint and it is not "animations off".

### Remove motion, keep the information

The distinction that matters: **an animation may carry information** — that a panel came from the button, that a row was inserted, that an error appeared. Deleting the animation must not delete the information.

- **A state change must still be perceivable.** Panel opens → it is open, immediately. A newly inserted row still needs to be distinguishable: swap the slide-in for an instant background tint that fades over a longer, non-moving beat, or simply ensure the change is announced.
- **Cross-fades are usually acceptable** where translation is not. Opacity change is not vestibular. When in doubt, replace *movement* with *opacity*, not with nothing.
- **Never remove a focus indicator, a loading indicator, or an error state** because it was implemented as an animation. Reduce the motion; keep the signal.

### The vestibular triggers, specifically

These are the ones that actually make people ill, in rough order of severity:

1. **Parallax** — layers moving at different rates create a depth cue the inner ear disagrees with. The single worst offender.
2. **Large-area movement** — anything moving that occupies a big fraction of the viewport, especially full-bleed sliding sections.
3. **Zoom / scale on large surfaces** — a hero scaling on scroll simulates self-motion.
4. **Rotation and spin**, at any size above an icon.
5. **Auto-playing loops** — carousels, background video, infinite marquees. These are also a WCAG 2.2.2 failure if they run over 5 seconds with no pause control.
6. **Motion the user did not initiate**, generally. Self-initiated motion is far better tolerated than motion that simply happens.

Small, local, self-initiated motion (a 4px knob, a fading tooltip) is *not* a trigger and does not need removing — over-suppressing makes an interface feel dead and removes real feedback.

### Why this skill collapses durations to 1ms

```css
@media (prefers-reduced-motion: reduce) {
  :root {
    --dur-instant: 1ms; --dur-fast: 1ms; --dur-base: 1ms;
    --dur-slow: 1ms; --dur-slower: 1ms;
    --ease-spring: var(--ease-out);
  }
}
```

The common alternative — `* { transition: none !important; animation: none !important; }` — breaks working code. Components routinely wait on `transitionend`/`animationend` to remove a node, release a focus trap, or fire a callback. `transition: none` means **the event never fires**, so the dialog never unmounts and focus is never restored. A 1ms duration still fires the event on the next frame. The override also disables `--ease-spring`'s overshoot, since an overshoot is a small reversal of direction and reversals are disproportionately provocative.

**What the token collapse does not cover — you must handle these by hand:**

- **Infinite loops.** 1ms × infinite is a strobe. Set `animation: none` explicitly (see the skeleton above). Anything with `infinite` in it needs its own reduced-motion rule.
- **Scroll-driven animations.** No duration to collapse (§6).
- **WAAPI / JS animations.** `el.animate()` takes its duration from your code. Read it from the token (`tokenMs()` in §5) or check `matchMedia('(prefers-reduced-motion: reduce)').matches` — and listen for `change`, because the preference can flip mid-session.
- **`scroll-behavior: smooth`.** Not on `html`: it animates find-in-page and every programmatic scroll. Smooth one in-page link from its click handler, with `behavior: 'auto'` when reduced motion is on (reset.css says how).
- **Autoplaying video and animated GIF/WebP.** Not CSS at all. Gate autoplay on the media query and provide a play control.
- **View transitions.** Kill the pseudo-element animations (§4).
- **Third-party libraries.** Lottie, Rive, video backgrounds, carousel scripts. Each needs an explicit check.

### Adjacent signals

- **`prefers-reduced-transparency: reduce`** — replace translucent surfaces and `backdrop-filter` with opaque ones. Users set it for legibility, and it is also a free performance win.
  ```css
  @media (prefers-reduced-transparency: reduce) {
    .sheet { backdrop-filter: none; background: var(--bg-surface); }
  }
  ```
- **`prefers-contrast: more`** — strengthen borders and foregrounds by re-pointing Tier 2 roles only, never by touching component rules.
  ```css
  @media (prefers-contrast: more) {
    :root { --border-default: var(--border-strong); --fg-muted: var(--fg-default); }
  }
  ```
- **`forced-colors: active`** — a different mechanism entirely; see `references/accessibility.md`. Relevant here because `box-shadow` is dropped in forced-colors mode, so any motion that *reveals* a shadow-based indicator reveals nothing.

---

## 9. Anti-patterns

| Anti-pattern | Why it fails | Instead |
|---|---|---|
| **Entrance animation that delays content on page load** | The user came for the content and you put a 600ms curtain in front of it. It also delays LCP, measurably. | Animate nothing above the fold on first paint. If brand demands a reveal, run it on content that is already painted (opacity only), and never gate text on it. |
| **Anything over 500ms in UI** | Past ~350ms the user is waiting; past 500ms they think it is broken and click again. | `--dur-slower` (480ms) is the ceiling, for route transitions only. |
| **Animating on every keystroke** | Fires 8–12 animations per second, each interrupting the last; the element never reaches a resting state and the input feels laggy. | Debounce the *visual* feedback, or make it instant (`--dur-instant`) and non-moving. Validation animation waits for blur, not for keyup. |
| **Hover animations that change layout** | `margin`, `height`, `padding`, `font-size` on hover reflows neighbours — cursor lands on a moving target and the element flickers in/out of hover (the "hover trap"). | `transform` and `opacity` only. Reserve the space at rest. |
| **Infinite attention-grabbing loops** | A permanently pulsing badge or bouncing arrow trains the user to ignore it, and is a WCAG 2.2.2 failure over 5s with no control. It is also a vestibular trigger. | Animate once on change. If something must loop, cap it at three cycles or give it a pause control. |
| **Motion that blocks input until it finishes** | The user's next click is swallowed by a 400ms transition. This is the most-hated interaction in modal UI. | Make every animation interruptible. A dialog must be dismissible during its own entrance; a menu must accept a click while opening. Never gate a handler on `transitionend` for *input*, only for *cleanup*. |
| **`transition: all`** | Animates properties you never considered — including ones the browser adds later. It forces the engine to diff every animatable property each frame, it silently animates layout properties, and it produces a flash when a class swap changes five things at once. | Name the properties. Always. `transition: opacity var(--motion-enter), transform var(--motion-enter);` |
| **Symmetric enter/exit** | Exit is latency; matching it to enter doubles the perceived cost of a dismiss. | `--motion-enter` in, `--motion-exit` out. |
| **Literal durations in component CSS** | Invisible to the reduced-motion override. An accessibility defect, not a style nit. | `--dur-*` / `--motion-*` only, including inside `el.animate()`. |
| **Animating a scroll position the user controls** | See §6. | `scroll-snap-type`, or nothing. |

---

## 10. Ship checklist

Law 9. Run every item; a failure is a blocker, not a nit.

1. **Grep for literals.** `grep -rnE '(transition|animation)[^;]*[0-9]+m?s' src/` and `grep -rn 'cubic-bezier(' src/` must return only `tokens.css`.
2. **Grep for `transition: all`** and `will-change` in base rules. Both must return nothing.
3. **Every animation names its job** in a comment (§1). Anything unnamed is deleted before review, not during.
4. **Enter and exit differ**, and exit is the shorter one.
5. **DevTools Performance, 6× CPU throttle**, on the three heaviest interactions: no repeating Layout bars, no non-composited-animation warnings.
6. **Toggle reduced motion** (DevTools → Rendering → Emulate CSS media feature) and re-run every flow. Confirm: nothing moves; every state change is still perceivable; no infinite animation is now a strobe; scroll-driven reveals are off; content is not stuck hidden.
7. **Interrupt every animation** — click the trigger twice fast, dismiss a dialog mid-entrance, navigate during a route transition. Nothing may get stuck, and no element may be left mid-transform.
8. **Test on a real mid-tier Android** over a throttled network at least once per project.
9. **Confirm no motion delays first content paint.**
10. **Confirm focus survives** every transition — dialogs, view transitions, route changes. Cross-reference `references/accessibility.md` §3.

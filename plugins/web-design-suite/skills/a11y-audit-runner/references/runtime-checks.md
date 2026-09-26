# Runtime Checks

What a browser lets you check that source analysis cannot, and how to check it. Every technique here is implemented in `scripts/a11y_runtime.mjs` except §6, reduced motion: the script runs with reduced motion off, so §6 is a procedure to run by hand. This file is why each one works the way it does, and what it costs.

The premise, stated once: **source describes intent, and a browser produces the result.** Every gap between them is somewhere an accessibility bug lives. `outline: none` is intent. Whether a ring is visible is a result. `aria-labelledby="x"` is intent. Whether the control has a name is a result, and it depends on whether `#x` exists, is unique, is not itself hidden, and contains text.

## Contents

1. [What changes when you render it](#1-what-changes-when-you-render-it)
2. [Accessible names and roles, computed](#2-accessible-names-and-roles-computed)
3. [Tab order: trap, skip, jump](#3-tab-order-trap-skip-jump)
4. [Focus visibility, measured in pixels](#4-focus-visibility-measured-in-pixels)
5. [Forced colors](#5-forced-colors)
6. [Reduced motion](#6-reduced-motion)
7. [Contrast, with overlays composited](#7-contrast-with-overlays-composited)
8. [Driving the key map](#8-driving-the-key-map)
9. [Zoom and reflow](#9-zoom-and-reflow)
10. [What a browser still cannot tell you](#10-what-a-browser-still-cannot-tell-you)

---

## 1. What changes when you render it

| Question | Source says | The browser says |
|---|---|---|
| Does this control have a name? | `aria-label` is present | the computed name is `""`, because the label is on a wrapper the AccName algorithm does not traverse |
| Is there a focus ring? | `:focus-visible { box-shadow: … }` exists | 0 of 7,353 pixels change, because a later rule set `outline: none` and the shadow is clipped by an ancestor's `overflow: hidden` |
| Where does Tab go? | DOM order | third, because something else has `tabindex="3"` |
| Is this text readable? | `#767676` on `#ffffff` is 4.54:1 | 1.4:1, because a 70%-white scrim is painted over it |
| Does Esc close the dialog? | there is a `keydown` handler | it fires on the dialog, and focus was on the body, so it never ran |
| Does the ring survive High Contrast? | `box-shadow` is set | nothing is drawn; `box-shadow` is discarded |

Four practical requirements before any of this is meaningful:

- **Serve over HTTP.** `file://` blocks `fetch`, breaks module scripts and gives you a document no user will ever receive. `--file` exists for a self-contained artefact like a proof sheet; everything else wants `--url`.
- **Freeze animation.** A ring measured mid-transition is a false negative and a colour sampled mid-fade is a false positive. The runner injects a 1ms `animation-duration`/`transition-duration` override before measuring, the same determinism trick `snapshot_matrix.mjs` uses.
- **Wait for fonts.** `document.fonts.ready` before any geometry, or every rect is measured against the fallback face.
- **Pin the viewport, DPR, locale, timezone and colour scheme.** Measurements you cannot reproduce cannot be regressed against.

---

## 2. Accessible names and roles, computed

### Why "computed" is the whole point

The Accessible Name and Description Computation is a real algorithm with a precedence order, and it is not "read the `aria-label`". Roughly: `aria-labelledby` (recursively resolving each reference), then `aria-label`, then the native mechanism for the element (a `<label>`, a `<legend>`, `alt`, `<caption>`, the `value` of a submit button), then content, then `title`. Hidden subtrees are excluded — except when referenced by `aria-labelledby`, which is the exception that surprises everyone.

Reimplementing that is a mistake. **Use axe-core's implementation**, which is already loaded:

```js
axe.setup(document);                       // build axe's virtual tree
const name = axe.commons.text.accessibleTextVirtual(axe.utils.getNodeFromTree(el));
const role = axe.commons.aria.getRole(el);
const type = axe.commons.aria.getRoleType(role);   // widget | landmark | structure
axe.teardown();                            // before any axe.run()
```

Chromium's `Accessibility.getFullAXTree` over CDP is the other option and gives you the browser's own answer, which is arguably more authoritative. It is also slower, returns backend node ids you then have to map back to selectors, and differs slightly between engines. For a gate, axe's implementation is the right trade.

### What to assert

| Assertion | Why | Severity |
|---|---|---|
| **Non-empty** for every element whose role type is `widget` | A control announced as "button" and nothing else is a 4.1.2 failure and a dead end for the user | error |
| **Unique within its context** | Two controls named "Edit" are indistinguishable in the form-controls list, and voice control cannot address either | warning |
| **Not merely the element type** | "Button", "Link", "Menu", "Icon". The role is already announced, so the user hears "button, button" | warning |
| **Contains the visible text** (2.5.3) | A voice-control user says what they can see; the command matches the *name* | error |

### The filter that keeps this usable

Query `[tabindex]` and you will collect `<main tabindex="-1">`, `<h1 tabindex="-1">` and every dialog container — **focus targets, not controls**, none of which require a name. Reporting them is noise, and noise is how a check gets switched off. Filter to natively-interactive elements plus anything whose role type is `widget`, and skip negative-tabindex non-controls. That single filter is the difference between a report a team reads and a report a team mutes.

### Duplicate names: the honest caveat

Two links with the same name *and the same destination* are correct — a logo and a wordmark both going home, "Buy" on three pricing cards where the card supplies the context. The runner groups by role, name and enclosing matrix cell and reports duplicates as warnings, not errors, precisely because the tool cannot see the context 2.4.4 explicitly permits. **Read them; do not gate on them blindly.**

---

## 3. Tab order: trap, skip, jump

### Extracting the real sequence

```js
await page.evaluate(() => document.activeElement?.blur());
for (let i = 0; i < steps; i++) {
  await page.keyboard.press('Tab');
  seq.push(await page.evaluate(() => describeActive()));   // selector + DOM index + rect
}
```

Press `2 × expectedTabbables + 20` times. That is enough to complete a full cycle and then some, which is what makes the three failure shapes separable. Run it again with `Shift+Tab`.

Independently, enumerate everything that *should* be a stop: the focusable selector set, minus `disabled`, minus negative `tabindex`, minus anything inside `[inert]`, minus anything not visible. **The comparison between the two lists is where the findings are.**

### The three failure shapes

| Shape | Signature | Meaning |
|---|---|---|
| **Trap** | the tail of the sequence cycles among ≤3 elements while tab stops outside that set were never reached | Focus can never leave. Level A failure (2.1.2), and the page is unusable rather than degraded |
| **Skip** | an expected tabbable never appears in the sequence | Either it is behind a trap, or a positive `tabindex` rewrote the order, or something swallows the key |
| **Jump** | within the first cycle, focus moves *backwards* in DOM order more than once | Visual order and DOM order disagree. Exactly one backwards step per cycle is the legitimate end-of-page wrap |

Distinguishing a trap from a wrap is the only subtle part, and it is not very subtle: **a healthy cycle visits every tab stop before repeating; a trap visits two or three.** Compare the cycle length against the expected count.

Real output from the fixture, which is the clearest way to see it:

```
   16. button#trap-a  "Trap A"
   17. button#trap-b  "Trap B"
  ↺ from step 18 the sequence repeats, cycling among 2 element(s) for the remaining
    39 press(es) — button#trap-a, button#trap-b. A cycle this short is a TRAP, not a wrap.
```

**Fix traps first.** The unreachable list usually empties on its own afterwards, because those controls were only unreachable because focus never got past the trap. Reporting twenty "unreachable" findings downstream of one trap is technically true and practically useless.

### The positive-`tabindex` jump, seen rather than inferred

```
    1. nav > a:nth-of-type(2)  [tabindex=3]  "Pricing"     ← runs first
    2. nav > a:nth-of-type(1)  "Home"
    3. nav > a:nth-of-type(3)  "Docs"
```

A linter can tell you a positive `tabindex` exists. **This shows what it did**, which is a different and much more persuasive artefact in a pull request. One positive value moved the second link to the front of the entire page, ahead of every other control, invisibly to anyone using a mouse.

### Print the sequence, always

The listing is the single highest-yield output in the whole runner and almost nothing else produces it. Read it as a sentence. A checkout that goes *email → promo code → newsletter → card number → expiry → CVC → edit shipping address → Pay* has no violations of any kind and is plainly wrong, and you can see that in four seconds. `automation-coverage.md` §4.3.

### What it still misses

Shadow DOM (unless the selector engine pierces it), cross-origin iframes (focus enters and the content is opaque — which at least shows you *whether* it comes back), and the browser's own chrome, which a real user reaches with Tab and a headless run does not.

---

## 4. Focus visibility, measured in pixels

### Why the stylesheet cannot answer this

A focus rule existing in CSS tells you nothing about whether a ring is drawn. It can be:

- overridden by a later rule, a more specific one, or an unlayered stylesheet that beats every layer;
- clipped by an ancestor's `overflow: hidden` — extremely common on cards, table cells and scroll containers, and it removes the outer half of the ring;
- drawn in a colour indistinguishable from what it sits on (the ring that works on the page background and vanishes on the accent-filled button);
- applied to `:focus` when the browser is matching `:focus-visible`, or vice versa;
- composed entirely of `box-shadow`, and therefore absent in forced-colors (§5).

All five are invisible to source analysis and obvious to a camera.

### The method

```
scrollIntoView(center)                       →  a stable rect
blur()  →  rAF rAF  →  screenshot(clip = rect + 10px)          = A
el.focus({preventScroll: true})  →  rAF rAF  →  screenshot(…)  = B
diff A,B in an OffscreenCanvas
```

Three details that matter:

- **Pad the clip by ~10px.** A ring with `outline-offset` sits *outside* the border box. Clip to the element and you measure nothing.
- **`preventScroll: true`.** If focusing scrolls the page, A and B are of different content and every pixel differs.
- **Two `requestAnimationFrame`s**, one for the style change and one for the paint it caused.

### Two numbers, and why the second one needs care

**Pixel fraction.** What proportion of the clip changed. Below ~0.5% there is no indicator. Verified values from the fixture:

```
  normal   forced    element
   0.00%    0.00%    form > button.plain            ← outline:none, no replacement
  19.52%    0.00%    button.shadowring              ← box-shadow only
  18.01%   18.69%    button.goodring                ← transparent outline + shadow
   9.66%    9.84%    input#email                    ← the UA's own ring
```

**Indicator contrast.** SC 2.4.13 (Level AAA, so beyond this skill's AA floor) asks for 3:1 between the focused and unfocused states of the indicator's own pixels. The obvious implementation — average the changed pixels before and after, take the contrast — **is wrong**, and it is worth knowing why:

> This suite's ring is two bands: an inner band in `--bg-canvas` and an outer band in `--border-focus`. The inner band's job is to sit between the accent and the component's own colour so the indicator is legible on a dark button or a photo. Average the two bands and you blend a 5.7:1 band with a ~1.0:1 band and report **2.39:1** for a ring that is plainly visible. The first implementation of this check did exactly that and flagged the *correct* ring as too weak.

Compute contrast **per pixel** and report a high percentile — the runner histograms per-pixel contrast and reports the 90th, which ignores a stray antialiased pixel and describes the band the eye actually sees. The same fixture, same ring: **5.68:1**.

### The suite-specific reading

A row where the normal column is healthy and the forced column is zero is a `box-shadow`-only ring. That is a single-line fix and it is in the token contract: pair the shadow with `outline: var(--stroke-focus) solid transparent`. §5.

---

## 5. Forced colors

### Emulating it

```js
const ctx = await browser.newContext({ forcedColors: 'active' });
// verify, do not assume:
const on = await page.evaluate(() => matchMedia('(forced-colors: active)').matches);
```

**Verify the media query actually matches** and skip the check if it does not, rather than reporting a pass. A forced-colors check that silently did not run is worse than no check, because it appears in the report as a green row.

Emulation is close and not identical: real Windows High Contrast also supplies the user's own system colour values, which can be any pair, and which is why the rule is *use the keywords in pairs* and never *guess which is light*.

### What predictably breaks in a token system

The symptom table is in `accessibility.md` §10 and is not repeated here. What matters for a *runner* is which of those symptoms are measurable and which are only surveyable:

| Symptom | How the runner sees it |
|---|---|
| **The focus ring disappears** | **Measured.** Re-run §4's measurement in a forced-colors context and compare. `19.52% → 0.00%` is the finding, with numbers |
| **All elevation vanishes** | Surveyed from computed style: count elements with a non-`none` `box-shadow` at rest. Each one is a card that will go flush with the page |
| **Filled and ghost buttons become identical** | Surveyed: controls with a background fill and no border. Both backgrounds are forced to `ButtonFace` |
| **Background images survive when everything else is re-coloured** | Surveyed: elements with a non-`none` `background-image`. Forced-colors keeps these, so a decorative image can end up the only un-adjusted thing on the page |
| **A transparent border becomes visible** | Surveyed: `border-color: transparent` with a non-zero width. Deliberate in the focus-ring bridge; a bug everywhere else, where `border-style: none` was meant |

### Why the ring is measured and not surveyed

An earlier version of this runner read the focus ring from computed style — focus the element, check whether `outline-style` and `box-shadow` are both set. **It was wrong**, in a way worth recording: Chromium resolves `outline-width` for `outline-style: auto` lazily, so the browser's *own* default ring reads as `0px` until it has painted. The check reported that every UA ring on the page was shadow-only, which is the opposite of the truth.

The lesson generalises past this one bug: **where a criterion is about what the user sees, measure what is drawn.** Computed style is a description of intent that has been through one more layer of processing, and it is still not the picture.

### The ring, one more time because it is the whole fix

<!-- snippet: reset.css#focus-ring -->
```css
:focus-visible {
  /* A TWO-ring indicator:
       ring 1  --stroke-focus  in --bg-canvas    (separation gap)
       ring 2  --stroke-focus  in --border-focus (the visible ring)
     Two rings are what make a focus indicator survive an element sitting
     on an accent fill, an image, or an inverse surface — there is always
     a contrasting edge somewhere in the pair.

     The visible ring is an OUTLINE, not a box-shadow. Components draw
     their own box-shadow (a button's elevation, a card's shadow) in a
     LATER layer, and a later layer's box-shadow replaced a ring drawn with
     box-shadow here: the canonical Button showed no focus at all
     (WCAG 2.4.7). No component sets an outline, so this ring survives all
     of them; a component with its own shadow loses only the gap ring. */
  outline: var(--stroke-focus) solid var(--border-focus);
  outline-offset: var(--stroke-focus);
  /* stylelint-disable-next-line declaration-property-value-allowed-list -- ring 1, the gap: a spread of two tokens, drawn here once */
  box-shadow: 0 0 0 var(--stroke-focus) var(--bg-canvas);
}

/* Windows High Contrast / forced-colors DISCARDS box-shadow and forces
   colours; the outline survives and is repainted in the system colour, in
   a mode whose whole users are people who need the ring most. */
@media (forced-colors: active) {
  :focus-visible {
    outline-color: Highlight;
    box-shadow: none;
  }
}
```

The ring is the outline. Forced-colors mode discards `box-shadow` and repaints `outline` in the system highlight colour, so an outline ring survives where a shadow ring vanishes. A component's own `box-shadow`, in a later layer, cannot remove an outline either. The box-shadow is only the canvas-coloured gap that keeps the ring readable on an accent fill. The older "bridge", a transparent outline under a box-shadow ring, also survives forced colours, but in normal mode any component shadow replaces its ring. `references/token-contract.md`, Accessibility floor.

### Auditing every state, which is where this pays

Run the forced-colors measurement against a `component-state-matrix` proof sheet and you get the answer for every state × density × theme at once. On the fixture built for this skill — a `.button` with a shadow-only ring and a `.chip` with the paired ring — **24 of 34 measured rings disappeared: every button cell, in both themes, at all three densities, and not one chip cell.** A page-level audit would have caught one of those twenty-four.

One integration detail worth knowing if you write your own: the proof sheet renders the `focus-visible` state by **mirroring the rule onto `[data-force-state~="focus-visible"]`**, so the ring is already painted at rest. Blurring and focusing such a cell changes nothing, and a naive measurement reports "no focus indicator" on the one cell that exists to prove the indicator. For those cells the A/B is the state attribute itself — remove it, shoot, restore it, shoot — which is the same comparison by a different lever and behaves identically under forced-colors.

---

## 6. Reduced motion

Not in `a11y_runtime.mjs`, which runs with `reducedMotion: 'no-preference'`. Run this one by hand, in a context of its own:

```js
const ctx = await browser.newContext({ reducedMotion: 'reduce' });
```

What to assert:

- **Motion actually reduced.** Record two short screenshot sequences of the same element, one in each mode, and compare the amount of change over time. A page that ignores the preference looks identical.
- **Nothing became inoperable.** The most common reduced-motion bug is not too much motion — it is a transition-driven reveal whose `opacity: 0` never animates to 1 because the transition was disabled globally, leaving the content permanently invisible. `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; … } }` is the standard nuclear reset and it causes this every time somebody uses a transition to *show* something rather than to soften a change.
- **Loops still loop.** `--dur-loop` is the one duration reduced-motion does not collapse, because a spinner that stops spinning reads as a hung page. If your reset caught it, you have made a loading state worse.

Deliberately measure performance with reduced motion **off** (that is `perf-budget-gate`'s choice, and it is the right one — the animations users see are the ones whose cost matters) and measure accessibility with it **on**. Different questions.

---

## 7. Contrast, with overlays composited

### The algorithm

For every element with a direct non-empty text node:

1. `fg = getComputedStyle(el).color`, with its alpha.
2. Walk ancestors compositing `background-color` with source-over until one is opaque. **If any ancestor has a `background-image`, stop and report the pair as unmeasurable** — do not guess.
3. Find everything painted *above* the text at its centre point and composite each in turn, over both the foreground and the background.
4. Required ratio: **3:1** if ≥24px, or ≥18.66px and weight ≥700; otherwise **4.5:1**.

Step 3 is the one that distinguishes this from a stylesheet checker.

### Finding the overlays

`document.elementsFromPoint(cx, cy)` returns the hit-test stack from the top down, respecting z-index and stacking contexts, which is exactly the paint order you need. Everything before the text's own element and not an ancestor of it is painted over the text.

**It misses `pointer-events: none`**, which is how most scrims are built, so scan separately for positioned elements with `pointer-events: none` and a non-transparent background whose rect contains the point, and take the union. That is two cheap passes and it covers the real cases.

### What it finds that nothing else does

From the fixture, verbatim:

```
error  contrast-under-overlay  "This paragraph sits under a 72% white scrim." measures
                               1.46:1 (needs 4.5:1 at 16px) — 1 translucent overlay(s)
                               composited in. The colour pair in the stylesheet reads
                               as 5.33:1.
```

**5.33:1 declared, 1.46:1 rendered.** Every source-level contrast checker, every design-token audit and every "we checked our palette" spreadsheet reports the first number. Report both, so the gap is the finding rather than a number somebody argues with.

Where this shape occurs in practice: loading veils over a form, a "fade to background" gradient at the bottom of a truncated article, a disabled-state overlay on a panel, a hero scrim over a photo, a modal backdrop that catches content it was not meant to, and `mix-blend-mode` anywhere near text.

### Where it still refuses

Text over a `background-image` is reported as **unmeasurable**, not as a pass. Contrast against a photograph varies per pixel and the worst pixel is the one that matters; a tool that quietly passed those would be lying. The finding names the ancestor that carries the image so a human can go and look — and the honest fix is usually to put the text on a solid scrim that *is* measurable, which converts a permanent unknown into a number.

---

## 8. Driving the key map

The 12-pattern key map in `accessibility.md` §4 is the ARIA Authoring Practices behaviour a user has already learned somewhere else. Deviating is a usability failure even when it is technically conformant — and it is exactly the class of thing a scanner never reports and a user notices in one second.

### The config

An expectation has to be declared, because a tool cannot know a `<div>` is a menu:

```json
{ "name": "Account menu", "pattern": "menu", "trigger": "#acct-btn",
  "container": "#acct-menu", "items": "[role=menuitem]" }
```

### What is worth automating, and what each assertion catches

| Pattern | Driven | The bug it catches |
|---|---|---|
| **Dialog** | Enter on the trigger opens it and moves focus inside; Esc closes it and focus returns to the trigger | Focus falling to `<body>` on close. The user is silently returned to the top of the document and their next Tab starts from the beginning of the page. This is the single most common modal bug and it is invisible to every scanner |
| **Menu** | Enter opens it and focuses the first item; Down arrow moves between items; `aria-expanded` flips; Esc closes it **and returns focus** | An `aria-expanded` that never updates — it tells the user the menu is closed while it is open, which is worse than saying nothing |
| **Tabs** | exactly one tab has `tabindex="0"`; Right arrow moves | A composite widget that is N tab stops instead of one. A 40-item widget where every item is a tab stop is a failure even though every item is reachable |
| **Disclosure** | Enter toggles `aria-expanded`; **focus stays on the trigger** | A disclosure that moves focus into its panel. The user did not ask to go there, and Shift+Tab now takes them somewhere they have already been |
| **Combobox** | Down arrow opens it; `aria-expanded` flips | A combobox the keyboard cannot open, or whose `aria-expanded` never changes |

Not driven, so check these by hand: Space on a button, Home and End in tabs, arrow wrap in a menu, Tab leaving a menu, Tab staying inside an open dialog, and Esc on a combobox. Esc must close only the popup, without committing and without closing a dialog behind it.

All five correct widgets in the verification fixture pass silently; all five broken ones are caught, each with its own rule name. The one sequencing note: if Esc does not close a thing, the focus-return assertion is not evaluated — you cannot check where focus went after a close that never happened, and reporting both would be one bug counted twice.

### The rule about the missing config

If no key map is supplied, **say so loudly**. Without one, every dialog, menu, tab set, disclosure and combobox on the page is unverified — which is the honest state of most CI accessibility jobs and almost never the state they report. The runner emits a warning naming the gap rather than passing quietly.

### What not to automate

Anything whose correctness is a judgement: whether a roving `tabindex` lands on the *right* item after a deletion, whether typeahead should reset after 500ms or 1000ms, whether Esc should close one layer or two. Automate the contract; leave the taste to the manual pass.

---

## 9. Zoom and reflow

Two viewport changes, two assertions:

| Check | How | SC |
|---|---|---|
| **200% zoom** | viewport 640×512 (half of 1280×1024); horizontal scroll is reported as a **warning**. It does not fail 1.4.4, which asks only that text resize without loss of content or function. Clipped or overlapping text is not measured: check it by eye | 1.4.4 (manual) |
| **400% zoom / 320px reflow** | viewport 320×256 — 1280 CSS px at 400% is a 320px viewport, which is how the criterion is specified and tested | 1.4.10 |

The assertion for 1.4.10 is `document.scrollingElement.scrollWidth > innerWidth`: two-dimensional scrolling, which means reading every line requires a horizontal scroll and back. **Name the widest offending element**, because the answer is nearly always one element:

- a fixed-width container or `min-width` on a wrapper;
- a table that will not wrap (data tables are a specified exception; a layout table is not);
- a long unbroken string — a URL, a code sample, a token name — which `overflow-wrap: anywhere` on prose fixes;
- a sticky header that at 400% eats half the viewport and should collapse.

Restore the viewport afterwards. Anything measured after a resize and before a settle is measuring a reflow in progress.

What this cannot decide: whether content or *functionality* was lost rather than merely rearranged. A nav that collapses to a hamburger at 320px is correct; a nav that disappears is a failure; both look the same to `scrollWidth`.

---

## 10. What a browser still cannot tell you

The honest list. Everything here is a reason the manual protocol exists.

| It cannot tell you | Because |
|---|---|
| **Whether the accessible name is correct** | It computed "Home" for the careers link. That is a fact about the DOM, not about the truth |
| **Whether the tab order makes sense** | It can print the sequence. Reading it as a sentence is a human act, and it is the highest-yield thirty seconds in the protocol |
| **What a screen reader actually says** | The a11y tree is an input to a screen reader, not its output. NVDA, JAWS and VoiceOver each apply their own heuristics, verbosity settings and bugs on top of it. Nothing headless reproduces that |
| **Whether an announcement happened at the right moment** | It can confirm a live region exists and its content changed. Whether the user heard it *then*, once, and in a useful order, is a timing question about a piece of software the browser is not running |
| **Whether the error message helps** | 3.3.3 is about whether a person can act on it |
| **Whether the page is comprehensible** | The largest category of real-world difficulty, and entirely outside the frame |
| **Whether a "disabled" control is genuinely inactive** | The contrast exemption depends on it. A control that looks disabled and still works is exempt from nothing |
| **What real Windows High Contrast does** | Emulation approximates it. The user's actual system colours can be any pair, and some pairs break things emulation does not |
| **Anything inside a cross-origin iframe** | Payment forms, maps, chat widgets, video players — where keyboard traps actually live. You can see focus go in and not come back, which is often enough to know you have a problem and never enough to fix it |
| **Whether the design is usable by the people it excludes** | Only those people can tell you. `manual-protocol.md` §8 |

One more, which belongs at the end because it is the failure mode of this entire file: **a browser cannot tell you that a green run stopped somebody doing the manual pass.** That outcome produces no finding, no log line and no failing build, and it is the most likely way this tooling does harm. Build the human pass into the release checklist before you build the CI job, not after.

# Review Checklist

The last gate. Run this on yourself before declaring any page or component finished —
before saying "done", before opening the PR, before handing back to a human.

It is built to be executed, not read. Each check names **the specific thing to look at**
and **the failure signature** — what it looks like when it's wrong — so you are matching
a pattern, not exercising judgement. Judgement is what the other references are for.
Twelve groups, roughly in order of how expensive the failure is to fix later.

Two rules govern how you run it:

- **Look, don't assume.** "The tokens handle dark mode" is not check 5.2. Toggling
  `[data-theme="dark"]` and looking is check 5.2.
- **A failed check is fixed at the system level**, not patched locally. See the last
  section; this is the whole reason the checklist exists.

### Set up once, then run straight through

Have these open before you start; groups 1–12 assume them and will otherwise tempt you
into assuming instead of looking.

```bash
npm run design:audit     # group 1 — must be clean before anything else is worth checking
npm run test
rg -n '#[0-9a-fA-F]{3,8}|[0-9]+px|[0-9]+ms' src/components/   # 1.2
rg -n -- '--space-|--neutral-|--accent-|--text-' src/components/  # 1.3
rg -n '!important|:global|#[a-z]' src/**/*.css                # 3.4, 3.5
rg -n 'dark' src/components/                                  # 5.2 — expect zero hits
rg -n 'margin-top|margin-bottom|margin-block-end' src/components/  # 2.2
```

In DevTools: the responsive bar preset to 320 / 390 / 768 / 1024 / 1440 / 1920; Rendering
panel with **Emulate `prefers-reduced-motion`**, **Emulate `forced-colors`**, and
**Layout Shift Regions** ready; a contrast picker; and `document.documentElement.dataset`
handy for flipping `theme` and `density`.

Order matters: run group 1 first because a token failure invalidates every visual
judgement below it, and groups 6–8 before 9–12 because a layout fix changes what the
later groups are looking at.

---

## 1. Tokens & values — Laws 1, 3, 6

| # | Look at | Failure signature |
|---|---|---|
| 1.1 | Run `python -m scripts.audit_design` (or `npm run design:audit`) | Any finding. Not "only warnings" — any finding |
| 1.2 | Grep the diff for `#`, `px`, `rem`, `ms`, `%` outside `tokens.json` and generated files | A literal in a component rule. `0` is the one literal every gate accepts; `1px` is `--stroke-hairline`, and `100%` is usually a layout mistake |
| 1.3 | Grep component files for `--space-`, `--neutral-`, `--accent-`, `--text-`, `--success-` etc. | A Tier 1 token read by a component. Skipped a tier; the rebrand will miss it |
| 1.4 | Tier 3 tokens in the component's first block | `--btn-pad-x: 12px` — Tier 3 sourced from a literal instead of Tier 2 |
| 1.5 | `git diff` on generated `tokens.css` / `tokens.ts` | Changed without a matching `tokens.json` change. Someone hand-edited a generated file |
| 1.6 | New tokens in the diff | A new Tier 1 step with no sign-off link, or a Tier 2 role named after its value (`--gap-24`) |
| 1.7 | `style={{…}}` in JSX | Anything that isn't a custom property carrying a runtime number. `style={{ marginTop: 8 }}` is three law violations in eleven characters |
| 1.8 | Every `z-index` | A literal. The ladder is closed (`--z-raised` → `--z-tooltip`); a `z-index: 9999` means two people are bidding against each other |
| 1.9 | Every `box-shadow` | A raw `--shadow-*` where an `--elevation-*` role exists, or a shadow typed inline. Elevation is a role, and dark mode re-points it |

## 2. Spacing — Law 2

| # | Look at | Failure signature |
|---|---|---|
| 2.1 | Every gap between siblings at the same level of the page | Two different values for the same relationship — cards 24px apart in one row, 20px in the next |
| 2.2 | Grep component CSS for `margin-block-end`, `margin-top`, `margin-bottom`, `margin` on a `.root` | A child setting its own outer margin. The parent owns it |
| 2.3 | The gap *role* chosen vs what the elements mean to each other | `--gap-separate` between a label and its input. The spacing says "unrelated"; the meaning says "fused" |
| 2.4 | Padding pairs on the same container | Asymmetric inset with no reason — `--pad-card` inline, a literal block. Usually a copy-paste |
| 2.5 | Icon + text, button label + edge, quoted/round shapes | No optical correction where the geometry demands it: a right-pointing icon centred mathematically reads left-heavy; a circular avatar in a square slot reads small |
| 2.6 | Section separations down the page at 1440px | Mixed rhythm — one section at `--space-section`, the next at a hand-picked value. Squint: the page should have an obvious beat |
| 2.7 | A rounded element inside a rounded container | Inner radius not `outer − inner padding`. Equal radii make the corners look peeled; it reads as sloppy before anyone can say why |
| 2.8 | Set `[data-density="compact"]` on `<body>` | Anything that doesn't move, or moves and breaks. A frozen element has a literal or a Tier 1 token in it (Law 7) |

## 3. Style architecture — Laws 4, 5

| # | Look at | Failure signature |
|---|---|---|
| 3.1 | Each component file | Two styling systems in one component — module classes *and* utility classes, or a stylesheet plus inline styles |
| 3.2 | The top of every CSS file | A rule outside a layer. Unlayered CSS beats every layer, silently, forever |
| 3.3 | `@layer` names in use | A layer not in `reset, tokens, base, layout, components, utilities, overrides`, or components declaring `@layer utilities` to win |
| 3.4 | Grep for `!important` | Any occurrence outside a documented third-party fix in `overrides` |
| 3.5 | Grep for `#` selectors and `:global` | An ID used for styling; a `:global` reaching into another component |
| 3.6 | Selector nesting depth | Depth ≥ 3. `.root .header .title` — the middle element should be doing this itself |
| 3.7 | Selectors naming another component | `.dashboard .button { padding: … }`. Use the component's documented Tier 3 property instead |
| 3.8 | Deleted or renamed markup in the diff | Its CSS still present. Dead CSS is invisible until it collides with something a year from now |

## 4. Typography

| # | Look at | Failure signature |
|---|---|---|
| 4.1 | Every `font-size` in the diff | A size not in the `--text-*` scale, or a raw `--text-*` where a `--type-*` composite role exists |
| 4.2 | Body text column width at 1440px | Measure outside 60–75ch. Over 75ch the eye loses the line return; under ~45ch it ping-pongs |
| 4.3 | `line-height` values | A fifth leading value invented. Big type on `--leading-normal` looks unset; body on `--leading-tight` is unreadable |
| 4.4 | Space above vs below every heading | Symmetric. A heading must sit closer to the text it introduces than to the block it follows, or it groups with the wrong content |
| 4.5 | Every text style on the page | An orphan size used exactly once. Either it's a role (token it) or it's drift (delete it) |
| 4.6 | Display/hero type ≥ 44px | No negative tracking. Large type set at `0` tracking reads loose and amateur |
| 4.7 | Uppercase labels | No `--tracking-caps`. Uppercase without added tracking is a legibility bug, not a style choice |

## 5. Color

| # | Look at | Failure signature |
|---|---|---|
| 5.1 | Measure contrast — don't eyeball it. Body, muted text, placeholder, disabled-adjacent, and text on accent | Body/muted below 4.5:1, large text below 3:1, focus ring or control boundary below 3:1. `--fg-subtle` on `--bg-sunken` is the pair that fails most |
| 5.2 | Toggle `[data-theme="dark"]` and look at every surface | A component that needed CSS to survive the toggle. Grep confirms it: any `dark` selector inside `components/` is an automatic fail |
| 5.3 | Dark mode shadows | Unchanged from light. Shadows read as mud on dark surfaces; depth must come from a lighter surface plus a hairline |
| 5.4 | Every use of `--bg-danger` / `--fg-success` / `--bg-warning` | Semantic color used decoratively — red because it looked good, not because something failed. It costs you the ability to signal |
| 5.5 | Any state communicated by color | Color is the *only* channel. Add an icon, a label, or a shape; ~4% of male users can't read your red/green |
| 5.6 | Accent usage across the full page | Accent on more than a few percent of the surface. When everything is emphasized, the primary action stops being findable |
| 5.7 | Text over images or gradients | No scrim, no guaranteed contrast. It tested fine on the one photo you used |

## 6. Layout & responsive

| # | Look at | Failure signature |
|---|---|---|
| 6.1 | Render at 320, 390, 768, 1024, 1440, 1920 | Anything clipped, overlapping, or stranded. 320 is where fixed widths die; 1920 is where centred content looks abandoned |
| 6.2 | Browser at 200% zoom, 1280px viewport | Text clipped, overlapping or cut off by a fixed height. This is WCAG 1.4.4, and it is the check that catches fixed heights. Then 400% zoom, a 320px viewport, for reflow (1.4.10): no two-axis scrolling |
| 6.3 | Horizontal overflow at every width | A scrollbar at the document level. Usual causes: a fixed `width` in px, `100vw` with a scrollbar present, an unwrapped long string, a negative margin |
| 6.4 | Where the breakpoints are | A breakpoint at a device name rather than where the content actually broke. Two-column-to-one at "iPad" instead of at the width where the measure went too narrow |
| 6.5 | Grid/flex children | A fixed `width` where `minmax()`/`flex` belongs. Fixed widths are how a layout survives 1440 and fails 1180 |
| 6.6 | Touch targets on mobile | Below `--tap-min` (44px), or two targets closer than 8px apart |
| 6.7 | Sticky/fixed chrome at 390px height | More than ~20% of the viewport eaten by chrome, or a fixed footer covering the last form field |

## 7. States

| # | Look at | Failure signature |
|---|---|---|
| 7.1 | Every interactive element: default, hover, focus-visible, active, disabled, loading, error | A missing state. `:active` and `loading` are the two that get skipped; the result is a button that feels dead on tap |
| 7.2 | Hover vs focus | Focus styled as a copy of hover with no ring, or hover effects on a touch device that stick after tap |
| 7.3 | Disabled controls | Disabled with no explanation of why, or a disabled state below 3:1 against its background *and* used to convey required information |
| 7.4 | The empty state of every collection | A blank area. An empty state names what goes here and offers the action that creates it |
| 7.5 | The loading state | A centred spinner replacing content that had a known shape. Use a skeleton matching the real layout, or the page jumps on arrival |
| 7.6 | The error state | A raw error string, or a toast that vanishes before it's read. An error says what happened, what it means, and what to do next |
| 7.7 | Loading → loaded transition | Layout shift. The skeleton's dimensions must equal the content's |

## 8. Accessibility

| # | Look at | Failure signature |
|---|---|---|
| 8.1 | Tab through the whole page without touching the mouse | A control you can't reach, a trap you can't leave, or focus jumping to the end of the DOM after closing an overlay |
| 8.2 | The focus indicator on every focusable element, including over accent backgrounds, at every density | Invisible, clipped by `overflow: hidden`, or below 3:1. `outline: none` anywhere without a replacement ring is a fail. `a11y_runtime.mjs` measures it at each tab stop and density |
| 8.3 | Focus order vs visual order | They diverge — usually because a flex/grid `order` or a visual reposition moved something the DOM still lists elsewhere |
| 8.4 | Element semantics in the DOM | `<div onClick>`. It is unreachable, unannounced, and doesn't fire on Enter/Space |
| 8.5 | Landmarks | No `<main>`, more than one `<main>`, unlabelled repeated `<nav>`s, or no skip link |
| 8.6 | Heading outline (read the `h1`–`h6` sequence alone) | No `h1`, multiple `h1`s, a skipped level, or a heading chosen for its size instead of its rank |
| 8.7 | Every form control | No programmatic label; placeholder used as label; error text not tied via `aria-describedby`; error announced only in color |
| 8.8 | Icon-only controls | No accessible name. An icon button with nothing but an SVG is a blank to a screen reader |
| 8.9 | Emulate `forced-colors: active` | Content that disappears — backgrounds carrying meaning, borders removed, SVG fills hard-coded instead of `currentColor`. `a11y_runtime.mjs` measures the focus ring there; the rest is by eye |
| 8.10 | Overlays (modal, drawer, menu) | Focus not moved in, not trapped, not returned to the trigger; background not inert; Escape doesn't close |

## 9. Motion

| # | Look at | Failure signature |
|---|---|---|
| 9.1 | Every animation and transition | You can't name its job in one clause — *shows where this came from*, *confirms the tap*, *covers the wait*. If you can't, it's decoration; delete it |
| 9.2 | Durations | A literal instead of `--motion-*`, or a mismatch: a hover at 320ms feels sticky, a modal at 80ms feels broken |
| 9.3 | Easing | `ease`/`ease-in-out` defaults, or something arriving with an `--ease-in`. Things entering decelerate; things leaving accelerate |
| 9.4 | Emulate `prefers-reduced-motion: reduce` | Motion still playing, or transitions zeroed so hard that `transitionend` never fires and a component hangs open |
| 9.5 | The animated properties | Anything other than `transform`, `opacity`, and (carefully) `filter`. Animating `width`/`top`/`height` triggers layout every frame |
| 9.6 | Entrance animations on content | Content animating in on scroll that a reader has to wait for, or that never fires because the observer missed it. Above-the-fold content never animates in |
| 9.7 | Looping/auto-playing motion | No pause control, or it runs longer than 5 seconds — WCAG 2.2.2 |

## 10. Performance

| # | Look at | Failure signature |
|---|---|---|
| 10.1 | Font loading in the `<head>` | No `preload` on the LCP font, no `font-display: swap`, or no metric-matched fallback — the text reflows when the webfont lands |
| 10.2 | Number of font files | More than 2 families / 4 weights shipped. Each one is a render-blocking round trip |
| 10.3 | Every `<img>` | No `width`/`height` or `aspect-ratio`; no `srcset`/`sizes`; raster served at 3× its display box; not AVIF/WebP |
| 10.4 | Below-the-fold images / above-the-fold hero | Missing `loading="lazy"` below the fold; `loading="lazy"` *on* the LCP image, which delays it |
| 10.5 | Record a page load and watch for shift | CLS from: unsized media, late-injected banners, webfont swap, content appearing above existing content |
| 10.6 | CSS bundle | Unused rules from a deleted feature, a whole icon set imported for four icons, or an unpurged utility framework |
| 10.7 | The LCP element | Unidentified. If you can't name it, you can't preload it, and it's usually a hero image or a webfont heading |

## 11. Content

| # | Look at | Failure signature |
|---|---|---|
| 11.1 | Every string on the page | Lorem ipsum, "Card title", or a placeholder name. Real copy changes the layout, and it always changes it late |
| 11.2 | The longest plausible value in every slot | Truncation with no tooltip, a wrapped button, a broken table cell. Test a 60-character name and a 7-figure number |
| 11.3 | The shortest / zero case | A one-item grid stretching to full width, a chart with one point, a table with a header and nothing else |
| 11.4 | Microcopy on buttons and errors | "Submit", "Error occurred", "Are you sure?". A button says what it does; an error says what to do next |
| 11.5 | Set `dir="rtl"` | The layout mirrors incorrectly. Caused by physical properties (`margin-left`, `left`) where logical ones belong |
| 11.6 | Any hard-coded English, date, or currency format | Concatenated strings that can't be translated; `MM/DD/YYYY` assumed; currency symbol hard-coded before the number |
| 11.7 | Text in images, and text containers | Copy baked into a raster; a container that can't grow when a translation runs 30% longer than English |

## 12. Handoff

| # | Look at | Failure signature |
|---|---|---|
| 12.1 | `IMPLEMENTATION.md` | "Last Completed Task" still names the previous task. The next session starts by guessing |
| 12.2 | `DESIGN_DECISIONS.md` | A non-obvious choice in the diff with no entry. It will be "fixed" by someone who doesn't know why it's like that |
| 12.3 | `tokens.json` | A new token with no comment naming its role. An unexplained token gets duplicated within a month |
| 12.4 | Stories | A variant, size, or tone that ships without a story. If it isn't in the stories, the designer never reviewed it |
| 12.5 | The component's doc comment | Public Tier 3 properties and the keyboard map undocumented. Undocumented means private; consumers will fork instead |
| 12.6 | `CLAUDE.md` | Stale after a stack or convention change — still says CSS Modules after the project moved to Tailwind |
| 12.7 | Deprecations in the diff | `@deprecated` with no replacement named, no removal version, and no codemod or exact grep. "Search for it" is not a migration path |

---

## What to do when a check fails

**Fix it at the system level. Never patch it locally.** A local patch is not a smaller
version of the right fix — it is the mechanism by which a codebase drifts, and it makes
the real fix harder by adding a consumer that depends on the drift.

Read the failure as a diagnosis of the system, then act:

| The failure | What it actually means | The fix |
|---|---|---|
| A spacing value has no token | Either the layout is wrong, or a role is missing | Snap to the nearest step; if the *relationship* genuinely has no name, add a **Tier 2 role**. Adding a Tier 1 step needs sign-off |
| A component needs a color that doesn't exist | A semantic role is missing | Add the role and re-point it in both themes. Never a hex, never a `dark` selector |
| You reach for `!important` | Two rules are in the wrong layers | Move the rule to the correct layer. `!important` doesn't resolve the conflict, it hides which rule was wrong |
| A component needs a tweak "just here" | The component's adjustment API is incomplete | Expose a documented Tier 3 custom property and set it from the parent. Never style it from outside |
| A gap looks wrong at one breakpoint only | A fixed value is doing a fluid value's job | Use a fluid role (`--space-section`) or fix the layout. Not a media-query override |
| The page needed new CSS to look right | A layout primitive is missing | Build the primitive in `layout.css` and use it. Page-level CSS is where systems go to die |
| Dark mode needs a component rule | A Tier 2 role is carrying two meanings | Split it into two roles and re-point both |
| The same fix appears in three places | It was never a component bug | Fix the shared ancestor — the token, the primitive, or the base style |

Three rules on top of that:

1. **If the right fix is out of scope, the check still failed.** Record it in
   `DESIGN_DECISIONS.md` with what the correct fix is and why it was deferred. An
   undocumented compromise becomes the new convention by default.
2. **A fix at the system level re-runs the checklist.** Changing a Tier 2 role changes
   every consumer. That's the point — and the reason to look at them.
3. **Never suppress the auditor.** An ignore comment on a Law-1 finding converts a
   fifteen-minute fix into a permanent exception nobody will ever revisit.

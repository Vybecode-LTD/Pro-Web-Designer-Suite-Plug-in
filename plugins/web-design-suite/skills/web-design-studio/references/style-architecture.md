# Style Architecture

Where every declaration lives, and why it lives there. This is the companion to `references/spacing-system.md`: spacing decides *what* the values are, this decides *where the rules go*.

If a codebase has good tokens and bad architecture, it still rots — just more slowly, and with more confusing symptoms.

## Contents

1. [The problem, stated precisely](#1-the-problem-stated-precisely)
2. [Law 4 — one home per component's styles](#2-law-4--one-home-per-components-styles)
3. [The only legitimate inline style](#3-the-only-legitimate-inline-style)
4. [Law 5 — layers, not specificity](#4-law-5--layers-not-specificity)
5. [The layer contract](#5-the-layer-contract)
6. [The component stylesheet shape](#6-the-component-stylesheet-shape)
7. [Tier-3 properties as a component's public API](#7-tier-3-properties-as-a-components-public-api)
8. [State belongs in data attributes](#8-state-belongs-in-data-attributes)
9. [The placement decision table](#9-the-placement-decision-table)
10. [Theming without touching components](#10-theming-without-touching-components)
11. [Containing third-party and legacy CSS](#11-containing-third-party-and-legacy-css)
12. [Dead CSS and how to find it](#12-dead-css-and-how-to-find-it)
13. [Anti-patterns](#13-anti-patterns)

---

## 1. The problem, stated precisely

Open a mature front-end codebase and the styling for one button is typically spread across:

- a base class in a global stylesheet
- a utility class list in the JSX
- a `style={{ marginTop: 12 }}` someone added under deadline
- a `!important` in a page-level override file
- a styled-component wrapper from a previous architecture
- a media query in a third file that nobody remembers

Nobody can answer "what makes this button look like this?" without opening DevTools, and even then the answer is "these six things, in an order determined by specificity, source order, and which bundle loaded first."

This is not a discipline failure. It is the predictable result of three missing constraints:

| Missing constraint | Symptom |
|---|---|
| No single home per component | You cannot find the styles, so you add more somewhere else |
| No layer order | Overriding means winning a specificity fight, so specificity ratchets upward forever |
| No override API | The only way to adjust a component is to reach in from outside, which breaks encapsulation and multiplies homes |

Laws 4, 5 and the Tier-3 socket pattern in §7 are those three constraints. They are cheap to adopt and they hold under multiple developers, which is the only test that matters.

---

## 2. Law 4 — one home per component's styles

> **A component's visual rules live in exactly one place. Reading that one file tells you everything about how the component looks.**

"One place" means one of these, chosen per project and never mixed:

- one `Component.module.css` beside the component (CSS Modules — the studio default for React work)
- one `@layer components` block in one `.css` file (vanilla CSS)
- one `cva`/`tv` variant table in the component file (Tailwind)

The test: **can a developer who has never seen this component predict its appearance from one file?** If they must also check a global override file, a parent's descendant selectors, and the JSX for inline styles, the answer is no and the component is unmaintainable regardless of how good it looks.

### The corollaries that make it hold

**No descendant styling across component boundaries.** A `.page` rule may not style `.card__title`. The page does not own the card. If a card needs to look different on a page, the page sets one of the card's documented Tier-3 properties (§7) — that is the sanctioned channel, and it is visible in both files.

```css
/* WRONG — the page reaches into the card. Now the card has two homes. example: wrong */
.pricing-page .card__title { font-size: 20px; color: #333; }
```

```css
/* RIGHT — the page uses the card's documented API: a socket that takes a
   type role (card.css reads font: var(--card-title-type, var(--type-h3))). */
.pricing-page .card { --card-title-type: var(--type-h2); }
```

**No style props.** `<Card padding="large" color="blue" />` recreates the same problem in TypeScript: the component's appearance is now decided at every call site. Use a closed `variant` / `size` / `tone` triad instead, where the variant table lives in the one home and the call site chooses from a finite set.

**No styling by element in component scope.** `.card h3 { … }` breaks the moment someone uses an `h2` for correct document outline. Address parts by class.

---

## 3. The only legitimate inline style

Inline `style` sets the *highest-specificity* declaration in CSS short of `!important`, in the one place that is invisible to every stylesheet, linter and theme. Which is why it is banned for visual properties.

There is exactly one thing it is good at, and it is genuinely important: **passing a runtime number into the cascade.**

```tsx
// LEGITIMATE — a value that cannot exist until runtime, handed to CSS as data.
// The component's rules still live in one file; this only supplies a number.
<li className={styles.card} style={{ '--card-span': span } as React.CSSProperties}>
```

```css
/* The rule that uses it stays in the one home, with a sane default. */
.card { grid-column: span var(--card-span, 1); }
```

Why this is different in kind: the inline declaration sets no visual property. It sets a *variable*. The visual decision — that `--card-span` maps to `grid-column` — still lives in the stylesheet, is still themeable, is still lintable, and still has a default for when the value is absent.

### The rule the tooling enforces

> `style` is permitted if and only if **every** key in the object is a CSS custom property (starts with `--`).

`assets/configs/eslint.design.config.mjs` implements exactly this. `style={{ marginTop: 12 }}` fails. `style={{ '--offset': `${n}px` }}` passes. A mixed object fails, because the mixed object is how the exception becomes the rule.

### The four cases people reach for inline style, and what to do instead

| Reach | Instead |
|---|---|
| A value computed at runtime (span, progress, position) | Custom property, as above |
| A value from a CMS or API (brand colour, background image) | Custom property set on a wrapper, consumed by the stylesheet |
| "Just this once" under deadline | A `variant` on the component, or a Tier-3 socket. It is never once. |
| Animating a property from JS | Web Animations API, or a custom property the CSS transitions |

### The same rule in other forms

The law is about *dispersal*, not about the `style` attribute specifically. These are the same violation wearing different clothes:

- `<div className="mt-3">` next to a `Component.module.css` that also sets margins — two homes.
- A `sx` prop, a `css` prop, a one-off `styled(Card)` wrapper — two homes.
- `element.style.width = …` in an effect — a home that no stylesheet can see.

Pick one mechanism per project and let the linter hold the line.

---

## 4. Law 5 — layers, not specificity

> **Override order is declared once, in the layer statement. It is never fought over with selectors.**

Before cascade layers, the only way to make rule B beat rule A was to give B higher specificity. This ratchets: every override raises the floor, until the codebase is full of `.page .section .card__title.card__title` and `!important`, and adding a new rule requires archaeology.

Layers decouple *override order* from *selector strength*. A single-class selector in a later layer beats an ID selector in an earlier one. Specificity becomes purely a matter of *which element this rule is about*, which is what it was always supposed to be.

### The order

```css
@layer reset, vendor, tokens, base, layout, components, utilities, overrides;
```

Declared once, as the **first statement** in the entry stylesheet, before any `@import`. A layer's position in the cascade is fixed the first time its name is seen, so if a component file creates `components` before the statement runs, the order is wrong and nothing later fixes it.

| Layer | Contains | Never contains |
|---|---|---|
| `reset` | Element defaults zeroed and normalized | Any project-specific look |
| `tokens` | Custom property definitions only | Any selector that paints |
| `base` | Element-level typography and link styles | Classes for specific components |
| `layout` | Layout primitives — Stack, Cluster, Grid, Center — and the two flow containers, `.flow` and `.prose`, which share one rhythm | Colours, component internals |
| `components` | Everything with a component's name on it | Layout of *other* components |
| `utilities` | The small closed set of single-purpose classes | Anything that needs more than one declaration |
| `overrides` | Page-specific escapes, documented and rare | Anything that should have been a variant |

### The two things everyone gets wrong

**1. Unlayered styles beat every layer.** Any CSS not inside a `@layer` block wins against all layered CSS regardless of specificity. This is the intended design (so that a page author can always override a framework), and it is also how a single forgotten `@layer` wrapper in one component file silently makes that component unoverridable. Every stylesheet in the project is wrapped. The auditor checks this.

**2. `!important` inverts layer order.** An `!important` declaration in `reset` beats an `!important` declaration in `overrides`. This is correct per spec and completely counterintuitive, and it is one more reason `!important` is banned outright. The one place it remains legitimate is a utility class that must win by definition (`.visually-hidden`), and even there prefer putting the utility in the `utilities` layer and skipping the `!important`.

### Importing into a layer

<!-- snippet: index.css#entry -->
```css
/* 1. The order, first: before every import and every rule. `vendor` is
      named before there is any vendor CSS, because a layer first named by
      its import is appended after `overrides`, where its rules beat every
      rule you write. */
@layer reset, vendor, tokens, base, layout, components, utilities, overrides;

/* 2. Each of these opens its own @layer block, so import it bare:
      `layer(base)` around base.css would nest it as `base.base`. */
@import url("reset.css");
@import url("tokens.css");
@import url("base.css");
@import url("layout.css");

/* 3. CSS you do not control names no layer: wrap it as it loads.
        @import url("../vendor/datepicker.css") layer(vendor);
      Then one line per component file, after the layers above:
        @import url("components/card.css");
      With CSS Modules there are none: each component imports its own. */
```

Each of those files opens its own `@layer reset { … }` (or `tokens`, `base`, `layout`), so it is imported bare. Wrapping one in `layer(reset)` as well nests it as `reset.reset`: it still sorts inside `reset`, but `@layer reset { … }` written elsewhere no longer targets the same slot. Use `layer()` only for a file that names no layer: vendor CSS, and Tailwind's own files.

---

## 5. The layer contract

A short set of rules that keeps layers doing their job.

1. **No `!important`.** Ever, outside `.visually-hidden`. If you feel you need it, you are in the wrong layer.
2. **No ID selectors.** `#app .card` is specificity for no benefit. IDs are for anchors and `aria-*` references.
3. **Maximum nesting depth 2.** Native nesting desugars through `:is()`, which takes the specificity of its *most specific* argument — so `&:hover` inside `.card` inside `.page` produces a number nobody predicted. Two levels keeps it readable and keeps the number knowable.
4. **`:where()` for anything that should be overridable.** `:where()` has zero specificity. Base element styles, variant defaults, and reset rules use it so that a single class always wins:
   ```css
   @layer base {
     :where(h2) { font: var(--type-h2); }   /* specificity 0,0,0 */
   }
   ```
5. **`:is()` for grouping, knowing the cost.** `:is(h2, h3, h4)` takes the highest specificity among its arguments. Grouping element selectors is free; grouping a class with an element is not.
6. **Selectors describe the element, not the override.** If a selector is long because you are trying to win, the layer is wrong.

### Checking specificity quickly

```bash
# Any selector with an ID, an !important, or 3+ classes is a smell.
rg -n '#[a-zA-Z][\w-]*\s*[.{\[>~+]|!important' src/styles src/components
rg -n '^\s*\.[\w-]+\s*\.[\w-]+\s*\.[\w-]+' src/styles src/components
```

---

## 6. The component stylesheet shape

Every component stylesheet has the same five-part shape. Sameness is the point: a reviewer opening any component file knows where to look before they read a line.

```css
@layer components {
  /* ------------------------------------------------------------------
     1. THE SOCKET BLOCK — this component's Tier-3 API.
        Every adjustable value, declared once on the root, defaulting to
        a Tier-2 role. This is the ONLY place the component reads Tier 2.
     ------------------------------------------------------------------ */
  .button {
    --button-pad-inline: var(--pad-inline-md);
    --button-pad-block:  var(--pad-block-md);
    --button-gap:        var(--gap-fused);
    --button-radius:     var(--radius-lg);
    --button-bg:         var(--bg-surface);
    --button-fg:         var(--fg-default);
    --button-border:     var(--border-default);
    --button-motion:     var(--motion-hover);
    /* Interaction is an OVERLAY, not a replacement fill. See the note
       under the states block — this one socket is why hover works on
       every variant without a per-variant hover colour. */
    --button-overlay:    transparent;

  /* ------------------------------------------------------------------
     2. THE STRUCTURE — everything that does not change between variants.
     ------------------------------------------------------------------ */
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--button-gap);
    min-block-size: var(--tap-min);
    padding: var(--button-pad-block) var(--button-pad-inline);
    border: var(--stroke-default) solid var(--button-border);
    border-radius: var(--button-radius);
    background-color: var(--button-bg);
    background-image: linear-gradient(var(--button-overlay), var(--button-overlay));
    color: var(--button-fg);
    font: var(--type-ui);
    cursor: pointer;
    transition: background-color var(--button-motion),
                border-color var(--button-motion),
                color var(--button-motion);
  }

  /* ------------------------------------------------------------------
     3. VARIANTS — re-point sockets only. Never add structure here, or
        the variants drift apart and stop being the same component.
     ------------------------------------------------------------------ */
  .button[data-variant="primary"] {
    --button-bg:     var(--bg-accent);
    --button-fg:     var(--fg-on-accent);
    --button-border: transparent;
  }

  .button[data-variant="ghost"] {
    --button-bg:     transparent;
    --button-border: transparent;
  }

  .button[data-size="sm"] {
    --button-pad-inline: var(--pad-inline-sm);
    --button-pad-block:  var(--pad-block-sm);
    --button-radius:     var(--radius-md);
  }

  /* ------------------------------------------------------------------
     4. STATES — every interactive component implements all seven.
        Ordered so that the cascade resolves them the way users expect:
        hover, focus, active, then the states that must win (disabled).
     ------------------------------------------------------------------ */
  .button:hover:not(:disabled)  { --button-overlay: var(--bg-hover); }
  .button:active:not(:disabled) { --button-overlay: var(--bg-active); }

  .button:focus-visible {
    outline: var(--stroke-focus) solid transparent;  /* forced-colors bridge */
    box-shadow: var(--elevation-focus);
  }

  .button:disabled,
  .button[aria-disabled="true"] {
    --button-bg: var(--bg-disabled);
    --button-fg: var(--fg-disabled);
    cursor: not-allowed;
  }

  .button[data-state="loading"] { cursor: progress; }

  /* ------------------------------------------------------------------
     5. PARTS — addressed by class, never by element.
     ------------------------------------------------------------------ */
  .button__icon {
    inline-size: 1em;
    block-size: 1em;
    flex: none;
  }
}
```

Read what this buys you:

- Every variant is three lines, because variants only re-point sockets.
- Dark mode required zero lines, because every colour is a role.
- Density required zero lines, because every space is a role.
- A page that needs a wider button sets `--button-pad-inline` from outside. No new class, no specificity fight, no second home.
- The whole component is one flat specificity level, so nothing can accidentally out-rank anything.

**Hover is guarded with `:not(:disabled)`** rather than ordered after the disabled rule, because ordering-based state resolution breaks the moment someone adds a rule in between. Guard conditions are explicit; order is implicit.

**Hover composes; it does not replace.** The obvious version of that rule is `:hover { --button-bg: var(--bg-hover) }` — and it is wrong, because it *overwrites* the primary variant's `--button-bg: var(--bg-accent)`. Your primary button turns pale grey the instant a pointer touches it. Painting the state as a translucent overlay on `background-image` instead means one hover rule darkens every variant correctly, forever, including variants that do not exist yet.

This is worth dwelling on because of how it is found. Looking at one button, in one variant, you will never see it. Render states × variants on one sheet and it is unmissable — every variant's hover cell is the same grey. That is the whole argument for the `component-state-matrix` skill: some bugs are only visible in the cross-product.

---

## 7. Tier-3 properties as a component's public API

This is the piece that makes Law 4 survivable. Without it, "never reach into a component" is a rule people break because they have no alternative.

> **A component's Tier-3 custom properties are its documented, supported adjustment surface. Anything not in that list is private.**

The parallel is exact: a component's props are its JavaScript API; its custom properties are its CSS API. Both are documented, both are stable, both can be deprecated deliberately.

```css
/* The card publishes four knobs. */
.card {
  --card-inset:  var(--pad-card);
  --card-radius: var(--radius-xl);
  --card-bg:     var(--bg-surface);
  --card-shadow: var(--elevation-card);
  /* … */
}
```

```css
/* A consumer adjusts them from outside, legally and visibly. */
@layer components {
  .pricing-grid > .card--featured {
    --card-inset:  var(--pad-card-lg);
    --card-shadow: var(--elevation-raised);
  }
}
```

The consumer's rule sets no visual property. It supplies values to an API. The card's one home still fully describes how the card looks; it just has parameters.

### Naming and documenting the API

- Name them `--<component>-<thing>`: `--card-inset`, `--button-pad-inline`. The prefix makes them greppable and prevents collisions.
- Declare **all** of them at the top of the root rule, even the ones no consumer uses yet. Declaration-site grouping is the documentation.
- Publish the list in the component's docs with the default and the allowed value type.
- Adding one is routine. Removing or renaming one is a breaking change and needs the deprecation path in `references/handoff-conventions.md`.

### The inheritance trap

Custom properties inherit. `--card-inset` set on `.pricing-grid` reaches *every* descendant, including nested cards you did not mean to touch. Two defences:

1. Set the socket on the component root, not on an ancestor, whenever you can.
2. For a socket only the component root reads, register it as non-inheriting. A value set on an ancestor then never reaches the card:
   ```css
   @property --card-bg {
     syntax: "<color>";
     inherits: false;
     initial-value: transparent;
   }
   ```
   Two limits:
   - **Only sockets the root alone reads.** `.card__media` reads `--card-radius` and `--card-inset` from the card root (`references/spacing-system.md` §8). If those were registered as non-inheriting, the media would get the initial value, not the card's. Leave part-read sockets inheriting, and rely on defence 1.
   - **The initial value must be computationally independent.** Use `24px`, not `1.5rem`. A rem depends on the root font size, so the browser drops the whole `@property` rule and the property stays unregistered (checked in Chromium 153).

   `@property` also gives you type checking (an invalid value falls back to the initial rather than silently becoming a string) and makes the property animatable, which raw custom properties are not.

---

## 8. State belongs in data attributes

State is `data-state="open"`, not `class="is-open"`. Four concrete reasons, not a style preference:

1. **Exclusivity is free.** `data-state` holds one value, so "open" and "closed" cannot both be true. Two classes can, and eventually will.
2. **Specificity stays flat.** `[data-state="open"]` and `.card` are both 0,1,0. Class-based state tends to accumulate compound selectors to win.
3. **Tests read what the CSS reads.** `getByRole('button', { current: true })` and a Playwright assertion on `[data-state="open"]` check the same attribute the stylesheet checks. Class names are implementation detail — and under CSS Modules they are hashed, so a test literally cannot assert on them.
4. **It survives a styling-system change.** Move from CSS Modules to Tailwind and the data attributes are unchanged.

Prefer a real ARIA attribute when one exists and already carries the state: `[aria-expanded="true"]`, `[aria-current="page"]`, `[aria-selected="true"]`, `[aria-invalid="true"]`, `:disabled`. Styling the accessibility attribute directly means the visual state and the announced state cannot diverge — which is a whole class of bug eliminated by construction.

```css
.disclosure__panel { display: none; }
.disclosure__trigger[aria-expanded="true"] + .disclosure__panel { display: block; }
```

If that selector ever stops matching, the panel is visually closed *and* announced as closed. There is no state where the screen reader and the screen disagree.

Use `data-*` for state that has no ARIA equivalent: `data-state="loading"`, `data-variant`, `data-size`, `data-density`.

---

## 9. The placement decision table

The lookup for "where does this declaration go?" Consult it instead of guessing.

| The declaration | Goes in | Why |
|---|---|---|
| A raw value (`1.5rem`, `#e8440a`) | `tokens.css`, Tier 1 | Literals exist in exactly one file (Law 1) |
| A value bound to a role (`--pad-card`) | `tokens.css`, Tier 2 | The vocabulary the team speaks (Law 6) |
| A component's adjustable value | The component's root rule, Tier 3 | Its public API (§7) |
| Element default typography | `base.css`, `@layer base`, in `:where()` | Applies to every instance, must be overridable |
| Anything about arranging boxes | `layout.css`, `@layer layout` | Composable primitives, not per-component CSS |
| Anything named after a component | `Component.module.css`, `@layer components` | One home (Law 4) |
| A variant of a component | Same file, socket re-point | Variants are parameters, not new components |
| A single-purpose class used everywhere | `utilities.css`, `@layer utilities` | Only if it is one declaration and genuinely global |
| A runtime-computed number | Inline `style`, custom property only | The one legal inline style (§3) |
| A page-specific escape | `overrides.css`, `@layer overrides`, with a comment | Rare, visible, deliberately last |
| A theme | Tier-2 re-point under a selector | Zero component changes (§10) |
| A third-party stylesheet | A low layer via `@import … layer()` | So it can never out-rank your components (§11) |

If a declaration does not fit a row, that is a signal to stop and reconsider the structure rather than to invent a new home.

---

## 10. Theming without touching components

The whole token architecture exists so this is true:

> **Adding a theme means adding one selector that re-points Tier-2 roles. It touches zero component files.**

```css
@layer tokens {
  [data-theme="dark"] {
    --bg-canvas:  var(--neutral-1000);
    --bg-surface: var(--neutral-950);
    --fg-default: var(--neutral-100);
    /* … roles only. No component selectors below this line, ever. */
  }

  [data-brand="clientB"] {
    --accent-500: oklch(62% 0.17 265);   /* Tier 1 re-point for a white-label */
    --font-sans:  "Inter", system-ui, sans-serif;
  }
}
```

**The test for whether your token layer actually works:** search the dark-theme block for a component class name. If you find one, the component had a hardcoded colour, and that colour is now wrong in some third context you have not discovered yet.

### The flash-of-wrong-theme problem

`@media (prefers-color-scheme: dark)` alone cannot honour a user's explicit override. `[data-theme]` alone cannot honour the OS before JS runs. The correct solution is a tiny blocking script in `<head>`, before any stylesheet, so the attribute is set before first paint:

```html
<script>
  // Blocking on purpose: ~1ms, and it prevents a full-page flash.
  try {
    const stored = localStorage.getItem("theme");
    const os = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    document.documentElement.dataset.theme = stored || os;
  } catch { document.documentElement.dataset.theme = "light"; }
</script>
```

Wrap it in `try/catch` — `localStorage` throws in some privacy modes, and an exception here means no theme at all. Also set `color-scheme` so form controls, scrollbars and the browser's own UI match.

---

## 11. Containing third-party and legacy CSS

Vendor stylesheets are written to win. A date picker ships `#datepicker .dp-day.dp-selected { background: #007bff !important; }` and now your accent colour has an exception nobody documented.

Layers solve this completely, because **a layer declared earlier loses to every later layer regardless of specificity**:

```css
@layer reset, vendor, tokens, base, layout, components, utilities, overrides;

@import url("flatpickr/dist/flatpickr.css") layer(vendor);
```

That `#id` selector now loses to `.calendar__day` in `components`: layer order is checked before specificity. No specificity war, no wrapper divs, no forking the vendor CSS. Its `!important` still wins, because important declarations reverse the order of layers: strip those at build time (`stack-vanilla-css.md` §5).

Same technique for legacy CSS during a migration: put the old stylesheet in a `legacy` layer below `components`, and new work automatically wins without anyone having to delete the old file first. This makes incremental migration actually incremental.

The one thing to watch: `!important` inside the vendor layer still beats non-`!important` declarations everywhere, and `!important` in an *earlier* layer beats `!important` in a later one. For the small number of vendor rules that use it, you will need `!important` in `overrides` — and those are exactly the cases worth a comment naming the vendor rule being fought.

---

## 12. Dead CSS and how to find it

Dead CSS is not merely waste. It is actively harmful: it makes grep results lie, it makes reviewers believe a rule is load-bearing, and it is the reason nobody dares delete anything.

**Find unused CSS Module classes** (fast, accurate enough to act on):

```bash
# Every class defined in a module that is never referenced in the sibling component
for f in $(find src -name '*.module.css'); do
  comp="${f%.module.css}.tsx"
  [ -f "$comp" ] || continue
  grep -oE '^\s*\.([a-zA-Z][\w-]*)' "$f" | tr -d ' .' | sort -u | while read -r cls; do
    grep -q "$cls" "$comp" || echo "UNUSED  $f  .$cls"
  done
done
```

**Find orphaned tokens** — a Tier-2 role nothing consumes is a decision nobody is honouring:

```bash
grep -oE '^\s*--[a-z0-9-]+' assets/starter/styles/tokens.css | tr -d ' ' | sort -u | while read -r t; do
  n=$(grep -rE "var\($t[,)]" src assets --include='*.css' --include='*.tsx' --include='*.ts' | wc -l)
  [ "$n" -eq 0 ] && echo "ORPHAN  $t"
done
```

**Rules for deletion.** Delete in its own commit, never mixed with a feature. Run the visual check at all three densities and both themes. If you are not confident, that is a sign the component has more than one home — find the others first.

---

## 13. Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| `style={{ marginTop: 12 }}` | Law 4. Highest specificity, invisible to every tool, unthemeable, off-scale. |
| `!important` | Inverts layer order, makes the next override harder, and is always a symptom of a wrong layer. |
| `#app .card` | Specificity that buys nothing and forces every future override to match it. |
| A page styling another component's internals | Two homes. Use the component's Tier-3 API. |
| `styles.card` and `className="p-4"` on the same element | Two homes, wearing different hats. |
| A stylesheet not wrapped in `@layer` | Unlayered wins over everything. One forgotten wrapper breaks the whole model. |
| `@apply` for a component class (Tailwind) | Recreates the specificity problem Tailwind exists to avoid, and hides the class list from the scanner. |
| Nesting four levels deep | The resulting specificity is unpredictable because `:is()` takes the max of its arguments. |
| `.card h3` | Breaks when the heading level changes for correct document outline. Address parts by class. |
| A `.dark` selector inside a component file | The component has a hardcoded colour. Fix the token, not the selector. |
| A `variant` implemented by adding structure | The variants drift and stop being one component. Variants re-point sockets only. |
| `style` props (`<Card padding="lg" color="blue" />`) | Moves the styling decision to every call site. Use a closed variant set. |
| Two class-name conventions in one repo | Every developer has to know both, and reviewers stop noticing violations of either. |

---

## The three sentences to remember

1. **One home** — if a reviewer cannot predict the component's appearance from one file, nothing else about the architecture matters.
2. **Layers decide who wins, selectors decide what they are about** — the moment those two jobs get mixed, specificity starts ratcheting and never stops.
3. **Tier-3 properties are the component's CSS API** — publish them, and "never reach into a component" becomes a rule people can actually follow.

Related: `references/spacing-system.md` (what the values are), `references/layout-composition.md` (the layout layer), `references/handoff-conventions.md` (repo shape and review), `assets/configs/stylelint.config.mjs` and `assets/configs/eslint.design.config.mjs` (the enforcement), `scripts/audit_design.py` (the gate).

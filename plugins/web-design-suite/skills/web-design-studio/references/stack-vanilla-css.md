# Stack: Vanilla CSS

Plain CSS, custom properties, cascade layers, native nesting. No framework, no compiler required. Optionally a three-plugin PostCSS pass that removes nothing and invents nothing.

This is the reference implementation of the Nine Laws. The other stacks in this skill are translations of it.

---

## Contents

1. [When this is the right answer](#1-when-this-is-the-right-answer)
2. [The honest weakness](#2-the-honest-weakness)
3. [File architecture](#3-file-architecture)
4. [`index.css` and the import order](#4-indexcss-and-the-import-order)
5. [Cascade layers in depth](#5-cascade-layers-in-depth)
6. [Native CSS nesting](#6-native-css-nesting)
7. [The component authoring pattern](#7-the-component-authoring-pattern)
8. [Worked example: button](#8-worked-example-button)
9. [Worked example: card](#9-worked-example-card)
10. [Scoping without a bundler](#10-scoping-without-a-bundler)
11. [The utility layer](#11-the-utility-layer)
12. [Progressive enhancement](#12-progressive-enhancement)
13. [PostCSS, if you use it](#13-postcss-if-you-use-it)
14. [Anti-patterns](#14-anti-patterns)
15. [The audit (Law 9)](#15-the-audit-law-9)

---

## 1. When this is the right answer

Agency work has a shape that framework CSS handles badly.

**No build coupling.** The CSS is the deliverable. It runs from a `<link>` tag. When the client's developer opens it in six months there is no toolchain to reconstruct, no lockfile to resolve, no Node version to guess. A stylesheet that needs a build is a stylesheet with an expiry date.

**It survives a CMS.** The moment content is authored in WordPress, Craft, Sanity or a rich-text field, you lose control of the markup. Class-per-element systems (Tailwind, CSS-in-JS) have no answer for `<h2>` emitted by an editor, so teams bolt on a `prose` plugin and re-implement element defaults badly. Element selectors in `@layer base` *are* the answer, and they cost nothing.

**It hands off cleanly.** Handover means: another team, a different stack, possibly a different agency. `tokens.css` plus seven files of ordinary CSS is readable by anyone who knows CSS. There is no dialect to learn, and the browser's DevTools show exactly the source you shipped — the line in the Styles pane is the line in your file.

**Zero framework churn.** Utility frameworks version their class names. Preprocessors deprecate their APIs. A CSS custom property declared in 2020 works identically in 2030 and will still work when the framework you almost picked is on its third breaking major.

**Choose something else when**: the app has hundreds of one-off stateful components whose styles are meaningless outside their JSX (use CSS Modules — see `stack-css-modules.md`); or the team is large, junior and shipping fast enough that build-time enforcement beats review discipline.

---

## 2. The honest weakness

Nothing in this stack stops a developer typing `margin-top: 13px`.

A bundler can enforce scoping. A type system can enforce a variant union. Vanilla CSS enforces nothing. Every law in this skill is, here, a *convention* — and conventions decay at exactly the rate you stop checking them.

This is why **Law 9 (nothing ships un-audited) matters more in this stack than in any other**. The audit is not a nicety appended to the process; it is the enforcement mechanism. §15 gives the greps. Wire them into CI on day one, before the first component exists, because a codebase with 400 violations will never be cleaned and a codebase with 0 stays at 0.

The second-order effect is worth stating: teams that adopt this stack without the audit conclude within a quarter that "plain CSS doesn't scale". Plain CSS scales. Unaudited plain CSS does not.

---

## 3. File architecture

One file per concern. The concern is the *kind of decision* the file makes, not the feature it belongs to.

```
styles/
  index.css            layer order + imports. NO declarations.
  reset.css            @layer reset      — delete UA defaults
  tokens.css           @layer tokens     — Tier 1 + Tier 2, themes, density
  base.css             @layer base       — bare elements get type + colour roles
  layout.css           @layer layout     — page shells, grids, stacks, containers
  components/
    button.css         @layer components
    card.css           @layer components
    field.css          @layer components
    …
  utilities.css        @layer utilities  — a closed, tiny set (§11)
  overrides.css        @layer overrides  — page-specific escape hatches, dated
```

Three rules keep this from rotting.

**A file may only write into its own layer.** `components/card.css` contains exactly one top-level `@layer components { … }` and nothing outside it. If a card needs a base-level change, that change belongs in `base.css` and affects every card-like thing — which is the conversation you wanted to have anyway.

**One component, one file, one root class.** `card.css` owns `.card` and every `.card__*` part. It owns nothing else. Grep for `.card` and you find one file; that is Law 4 made operational.

**`overrides.css` entries carry a date and a reason.** It is a quarantine, not a layer. An entry older than a sprint is a bug report about the component it overrides.

```css
/* 2026-03-14 — campaign LP hero needs an off-scale gap pending brand sign-off.
   Owner: RD. Remove after the token proposal lands. */
```

---

## 4. `index.css` and the import order

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
      With CSS Modules there are none: each component imports its own.
      Last, once the project has them, the closed set of utilities and the
      dated overrides. Each opens its own @layer block, so import it bare:
        @import url("utilities.css");
        @import url("overrides.css"); */
```

### Why the layer statement must come first

**A layer's position is fixed the first time its name is seen.** If `reset.css` loads before the statement, the layer `reset` is created at that moment and lands *first* — which happens to be right. But if a network hiccup delivers `components/card.css` first, `components` is created first and now sits *below* `reset`, and your entire cascade inverts. The order depends on load order, which depends on the network, which means the bug is intermittent and only in production.

The `@layer a, b, c;` **statement** form creates all the names at once, empty, in the order you wrote, and every later `@layer a { … }` block appends into the existing slot. Declaring it on line one makes cascade order a property of your source, not of the network.

It is legal on line one: `@import` must precede all other rules *except* `@charset` and layer **statements**. Order within `<head>` is therefore: `@charset` → `@layer` statement → `@import` → everything else. Put a declaration above an `@import` and every import silently stops working.

### How `@import url(…) layer(name)` works

`@import url("x.css") layer(vendor)` wraps the *entire* contents of `x.css` in `@layer vendor { … }` as it loads. The imported file needs no cooperation — it does not know it has been layered, cannot opt out, and any `@layer` blocks it declares internally become sub-layers of `vendor` (`vendor.theme`, etc.), still contained.

`@import url("x.css") layer` (bare keyword, no name) wraps it in a fresh **anonymous** layer at that position. Anonymous layers can never be referenced again, which is exactly what you want for a vendor file nobody should be extending.

**Do not pass `layer()` to a file that already declares its own layer.** `tokens.css` opens with `@layer tokens { … }`. Importing it as `layer(tokens)` produces `@layer tokens { @layer tokens { … } }` — a nested layer named `tokens.tokens`. It still sorts inside `tokens`, so nothing visibly breaks, but `@layer tokens { … }` written elsewhere no longer targets the same slot and DevTools shows a layer name you did not write. Use `layer()` only for files you do not control.

### Production: kill the waterfall

`@import` is serial. The browser must fetch and parse `index.css` before it discovers `reset.css`, then parse that before it discovers `tokens.css`. Nine files is nine round trips on the critical render path.

Two acceptable answers:

1. **Flatten at build time** with `postcss-import` (§13). It inlines every import and preserves `layer()` wrapping. Ship one file.
2. **Parallel `<link>`s.** There is no `layer` attribute on `<link>`, so each file must self-declare its layer, and a tiny inline style must establish the order before any of them arrive:

```html
<style>@layer reset, vendor, tokens, base, layout, components, utilities, overrides;</style>
<link rel="stylesheet" href="/styles/reset.css">
<link rel="stylesheet" href="/styles/tokens.css">
<!-- … -->
```

Because the names already exist in order, the files may now arrive in any order at all.

---

## 5. Cascade layers in depth

### What layers actually solve

**Specificity arms races.** Without layers, "make this override that" is answered with specificity, and specificity only goes up. `.card .title` beats `.title`; someone then needs `.page .card .title`; six months later the codebase's average selector is four compounds long and nobody can override anything without reading the whole file. Layers replace the question "how specific must I be?" with "which layer does this belong in?" — a design question with a correct answer.

**Third-party CSS.** A vendor stylesheet ships `.dp-calendar__day.dp-selected { background: #0af !important }`. You cannot out-specify it and you refuse to use `!important` (Law 5). Layers let you put it *underneath* everything you write. See the worked example below.

**Override order without `!important`.** `utilities` beats `components` because it is later in the statement, not because `.u-hidden` is more specific than `.card__footer`. Both can stay single-class selectors forever.

### The thing everyone gets wrong: unlayered styles win

The cascade's layer step, weakest to strongest, for **normal** declarations:

```
@layer reset  →  @layer tokens  →  …  →  @layer overrides  →  UNLAYERED
```

**Unlayered author styles beat every layer.** Not "act like the last layer" — they are a separate, higher step. This is the opposite of most people's intuition ("layers are for organising, unlayered is the default/weakest") and it causes one specific production failure: a developer adds a quick rule at the bottom of a file, outside its `@layer` block, it works, and now nothing in `overrides.css` can touch it.

Two consequences to internalise:

- **Every author rule you write must be inside a layer.** No exceptions. The audit greps for this (§15).
- It is a genuine tool for a genuine emergency. An unlayered rule is a `!important` that does not break `:hover`. Treat it with the same suspicion: dated, commented, in `overrides.css`, removed next sprint.

And the mirror-image rule for `!important`: **important declarations reverse the layer order entirely.** An `!important` in `reset` beats an `!important` in `overrides`, and important layered beats important unlayered. This is coherent (it is the same reversal that makes user `!important` beat author `!important`) and it is a second reason not to use `!important`: in a layered codebase it does the opposite of what the person typing it expects.

### Nesting layers

`@layer components.button { … }` puts rules in the sub-layer `button` inside `components`. Sub-layers sort among themselves, and the whole group sorts as one unit within `components`.

Useful when a single component has a genuine internal precedence problem — a theme skin that must beat the component's own defaults but still lose to `utilities`:

```css
@layer components {
  @layer base, skin;          /* order inside `components` */
}

/* components/card.css */
@layer components.base { .card { --card-bg: var(--bg-surface); } }

/* themes/editorial.css */
@layer components.skin { .card { --card-bg: var(--bg-sunken); } }
```

Do not reach for this early. A flat `components` layer is correct for almost every project, and sub-layers are one more thing a new developer has to hold in their head.

### Worked example: burying a vendor stylesheet

A third-party datepicker ships this:

```css
/* vendor/datepicker.css — not yours, do not edit. example: illustration */
#dp-root .dp-day.dp-day--selected {
  background: #0af !important;
  font-family: Helvetica, sans-serif !important;
  padding: 7px 9px !important;
}
```

An ID, a double class, and `!important` on all three. In an unlayered codebase this is unwinnable without `#dp-root .dp-day.dp-day--selected.dp-day--selected { … !important }` and a note apologising for it.

Add one line to your layer statement and one to your imports:

```css
@layer reset, vendor, tokens, base, layout, components, utilities, overrides;

@import url("../vendor/datepicker.css") layer(vendor);
```

Now write the component normally:

```css
@layer components {
  .dp-day {
    background-color: var(--bg-surface);
    font: var(--type-ui);
    padding-inline: var(--pad-inline-sm);
    padding-block: var(--pad-block-sm);

    &:where([aria-selected="true"]) {
      background-color: var(--bg-accent);
      color: var(--fg-on-accent);
    }
  }
}
```

A single class in `components` now beats an ID in `vendor`, because **layer order is checked before specificity**. Specificity is only consulted to break ties *within* one layer.

The `!important` declarations are the one part that still bites: important declarations reverse layer order, so the vendor's important rules beat your normal ones. Handle it once, in the import, by stripping them at build time (`postcss-discard-important` scoped to that file) — or, if you cannot, patch those declarations in a vendored copy and document why. An `!important` of your own does not help: in `overrides` it loses to the vendor's, because the order is reversed. Do not let it spread.

### `revert-layer`

`revert-layer` rolls a property back to the value it had in the previous layer, rather than to the UA default. It is the precise tool for "undo the utility, keep the component":

```css
@layer overrides {
  /* 2026-02-02 — legacy embed brings its own type. Restore the component
     value for this subtree only. Owner: KM. */
  .legacy-embed .card__title { font: revert-layer; }
}
```

---

## 6. Native CSS nesting

Baseline in every current engine. No preprocessor needed, and DevTools shows the nested source rather than a flattened selector you did not write.

### The `&` rules

The one rule that matters: **a nested selector is a *relative* selector, and `&` is implicitly prepended with a DESCENDANT combinator when you do not write it.**

```css
.card {
  :hover      { … }   /* → .card :hover     — a hovered DESCENDANT. Wrong. */
  &:hover     { … }   /* → .card:hover      — the card itself. Right.      */
  .title      { … }   /* → .card .title     — descendant. Usually right.   */
  &.is-active { … }   /* → .card.is-active  — compound. Needs &.           */
  > .title    { … }   /* → .card > .title   — combinator may lead.         */
}
```

So: **`&` is mandatory whenever you are compounding onto the parent** — pseudo-classes, pseudo-elements, attribute selectors, additional classes. Omit it only for descendants.

`&` may also appear in the middle or end of a nested selector, which is how you write "when an ancestor has X":

```css
.button {
  [data-theme="dark"] & { … }   /* → [data-theme="dark"] .button */
}
```

Prefer re-pointing a token to this. An ancestor-qualified component rule means the component knows about its context, which is the thing tokens exist to prevent.

### Specificity: `&` desugars to `:is()`

A nested rule's parent reference behaves as `:is(<the full parent selector list>)`, and **`:is()` takes the specificity of its most specific argument.** That is the trap:

```css
/* example: wrong */
.card, #promo {          /* selector list with an ID in it */
  & .title { … }         /* → :is(.card, #promo) .title  →  specificity (1,1,0) */
}
```

`.title` inside `.card` now has ID-level specificity, everywhere, including inside `.card` where no ID is involved. Nothing you write with classes will ever override it.

Rules that avoid it entirely:

- **Never put an ID in a selector.** Law 5 already says this; nesting raises the cost from "one bad rule" to "every descendant of that rule".
- **Never nest under a comma-separated list of differing specificities.** If you must, hoist: write the shared declarations at the top level and nest under a single selector.
- Reach for `:where()` when you want the parent reference to cost nothing: `:where(.card, .panel) { & .title { … } }` gives `.title` specificity (0,1,0).

### The depth-2 limit

Law 5 caps nesting at **two levels** — the top-level rule plus one nested rule. `&:hover` inside `.card` is depth 1. `& .title { &:hover { … } }` is depth 2 and is already the edge.

Three reasons, in order of how much they hurt:

1. **Specificity grows silently.** Every nesting level compounds. A three-deep rule is a four-compound selector that reads like a two-line rule, so nobody notices the arms race starting.
2. **The selector becomes unfindable.** Depth 3 means the string `.card__footer` does not appear anywhere in the file. Grep is the primary navigation tool in a CSS codebase; nesting that hides selectors from grep removes it.
3. **It encodes structure into style.** `.card { & .body { & .title { & a { … } } } }` breaks the moment the markup is reordered, and it pins you to a DOM shape that a CMS will eventually violate.

If you want depth 3, you have found a new component. Give it a root class and a file.

---

## 7. The component authoring pattern

The canonical shape. Every component file in the project looks like this, and a reviewer should be able to check conformance in ten seconds.

```css
@layer components {
  .thing {
    /* 1. TIER-3 CUSTOM PROPERTIES, declared first, defaulted from Tier 2. */
    --thing-pad:    var(--pad-card);
    --thing-bg:     var(--bg-surface);

    /* 2. Structure: display, flow, gap. */
    /* 3. Box: size, padding, border, radius. */
    /* 4. Paint: colour, background, shadow. */
    /* 5. Type. */
    /* 6. Motion. */

    /* 7. States, via :where() — zero specificity. */
    &:where(:hover) { … }

    /* 8. Variants, as separate top-level rules below. */
  }

  /* 9. PARTS, addressed by class. */
  .thing__part { … }

  /* 10. MODIFIERS, re-pointing Tier-3 properties only. */
  .thing:where([data-variant="loud"]) { --thing-bg: var(--bg-accent); }
}
```

**Tier-3 properties at the top, with Tier-2 defaults.** This is the load-bearing idea. Every value a variant might change becomes a named property with a semantic default. A variant then re-points properties instead of restating declarations, so `background-color: var(--thing-bg)` is written exactly once in the file and there is one place to look when a colour is wrong.

**State via `data-*`, not classes.** `data-state="loading"` is a single attribute a framework can set and a server can render; `.is-loading` is a class you must remember to remove. Attributes are also greppable as a set (`data-state=`) in a way that a scattering of `.is-*` classes is not. Use ARIA state attributes where one exists — `aria-expanded`, `aria-selected`, `[disabled]` — because then the style and the accessibility tree cannot drift apart.

**`:where()` for variants and states.** `.thing:where([data-variant="loud"])` has specificity (0,1,0) — identical to `.thing`. It wins purely by source order. That means variants never accumulate specificity, they can be listed in any order without arithmetic, and a utility (one class, later layer) always beats a variant (one class, earlier layer). Write the plain `.thing` rule first, then every variant below it.

**Parts by class, never by element.** `.card__title`, not `.card h3`. Element selectors pin the component to a DOM shape: the day the title becomes an `<h2>` for outline reasons, or a `<span>` inside a link, the styling silently detaches. A class survives every markup change and is greppable from the template.

**Modifiers as `data-variant` / `data-size`.** Two axes, both closed sets, both expressible in a type union on the framework side. `data-variant` is *what it is* (primary, ghost, danger); `data-size` is *how big* (sm, md, lg). A third axis is usually a second component.

---

## 8. Worked example: button

```css
/* components/button.css */
@layer components {

  .button {
    /* ---- Tier 3: the component's own vocabulary --------------------- */
    --btn-pad-inline: var(--pad-inline-md);
    --btn-pad-block:  var(--pad-block-md);
    --btn-gap:        var(--gap-fused);      /* icon + label are one thing */
    --btn-radius:     var(--radius-lg);
    --btn-bg:         var(--bg-surface);
    --btn-fg:         var(--fg-default);
    --btn-border:     var(--border-default);
    --btn-shadow:     var(--elevation-flat);
    --btn-min-size:   var(--tap-min);

    /* ---- Structure -------------------------------------------------- */
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--btn-gap);

    /* ---- Box -------------------------------------------------------- */
    min-block-size: var(--btn-min-size);
    padding-inline: var(--btn-pad-inline);
    padding-block: var(--btn-pad-block);
    border: var(--stroke-default) solid var(--btn-border);
    border-radius: var(--btn-radius);

    /* ---- Paint ------------------------------------------------------ */
    background-color: var(--btn-bg);
    color: var(--btn-fg);
    box-shadow: var(--btn-shadow);

    /* ---- Type ------------------------------------------------------- */
    font: var(--type-ui);
    letter-spacing: var(--tracking-wide);
    text-decoration: none;          /* beats base.css `a` — later layer */
    white-space: nowrap;

    /* ---- Motion ----------------------------------------------------- */
    transition: background-color var(--motion-hover),
                border-color     var(--motion-hover),
                box-shadow       var(--motion-hover);

    /* ---- States ----------------------------------------------------- */

    /* The hover overlay composes over ANY variant background, which is why
       there is no --btn-bg-hover per variant. --bg-hover is a translucent
       ink; painting it as a gradient layer above background-color tints
       whatever is underneath. One rule, every variant, light and dark. */
    &:where(:hover) {
      background-image: linear-gradient(var(--bg-hover), var(--bg-hover));
    }

    &:where(:active) {
      background-image: linear-gradient(var(--bg-active), var(--bg-active));
    }

    &:where(:disabled, [aria-disabled="true"]) {
      --btn-bg:     var(--bg-disabled);
      --btn-fg:     var(--fg-disabled);
      --btn-border: transparent;
      --btn-shadow: var(--elevation-flat);
      background-image: none;       /* no hover tint on a dead control */
      cursor: default;
    }
  }

  /* ---- Parts -------------------------------------------------------- */

  /* em-relative on purpose: the icon must track the button's type size
     across every --data-size, and no absolute token can do that. */
  .button__icon {
    inline-size: 1em;
    block-size: 1em;
    flex: none;
  }

  /* ---- Variants: re-point Tier 3, declare nothing new ---------------- */

  .button:where([data-variant="primary"]) {
    --btn-bg:     var(--bg-accent);
    --btn-fg:     var(--fg-on-accent);
    --btn-border: transparent;
    --btn-shadow: var(--elevation-card);
  }

  .button:where([data-variant="ghost"]) {
    --btn-bg:     transparent;
    --btn-fg:     var(--fg-accent);
    --btn-border: transparent;
  }

  .button:where([data-variant="danger"]) {
    --btn-bg:     var(--bg-danger);
    --btn-fg:     var(--fg-on-accent);
    --btn-border: transparent;
  }

  /* ---- Sizes -------------------------------------------------------- */

  .button:where([data-size="sm"]) {
    --btn-pad-inline: var(--pad-inline-sm);
    --btn-pad-block:  var(--pad-block-sm);
    --btn-radius:     var(--radius-md);
    font: var(--type-label);
  }

  .button:where([data-size="lg"]) {
    --btn-pad-inline: var(--pad-card);
    --btn-pad-block:  var(--pad-block-md);
    font: var(--type-body);
  }

  /* A small button on a mouse-driven admin screen may be genuinely small.
     On a finger it may not — 44px is not a style preference, it is the
     size of the input device. Shrink the hit area only where the pointer
     is precise. */
  @media (pointer: fine) {
    .button:where([data-size="sm"]) { --btn-min-size: auto; }
  }
}
```

```html
<button class="button" data-variant="primary">
  <svg class="button__icon" aria-hidden="true" …></svg>
  Publish
</button>
```

What to notice: `background-color` appears once. `font:` is set from a role, never from a size plus a weight plus a leading. Every variant is four re-pointed properties and no new declarations. Dark mode required zero lines, because every default came from Tier 2.

---

## 9. Worked example: card

The card exists to demonstrate the two problems buttons do not have: **full-bleed media inside a padded container**, and **a clickable region that contains text**.

```css
/* components/card.css */
@layer components {

  .card {
    --card-pad:    var(--pad-card);
    --card-gap:    var(--gap-related);
    --card-radius: var(--radius-xl);
    --card-bg:     var(--bg-surface);
    --card-border: var(--border-subtle);
    --card-shadow: var(--elevation-card);

    position: relative;                /* anchor for the link overlay */
    display: flex;
    flex-direction: column;

    background-color: var(--card-bg);
    border: var(--stroke-hairline) solid var(--card-border);
    border-radius: var(--card-radius);
    box-shadow: var(--card-shadow);

    /* Clips the media to the card's radius. Note the consequence, handled
       in .card__link below: it also clips a box-shadow focus ring. */
    overflow: hidden;

    transition: box-shadow var(--motion-hover),
                border-color var(--motion-hover);

    &:where(:hover) {
      --card-shadow: var(--elevation-raised);
      --card-border: var(--border-strong);
    }

    /* The card is a group; make focus inside it visible on the whole card. */
    &:where(:focus-within) {
      --card-border: var(--border-focus);
    }
  }

  /* THE PADDING LIVES ON THE BODY, NOT THE CARD.
     The obvious alternative — padding on .card, then a negative margin on
     .card__media to bleed it back out — is a child setting its own outer
     margin to escape its parent (Law 2), and it breaks the moment the card's
     padding changes with --density. Moving the inset one level down means
     media is flush because it was never inset. No negative values anywhere. */
  .card__media {
    aspect-ratio: 16 / 9;             /* a ratio, not a scale value */
    inline-size: 100%;
    object-fit: cover;
    background-color: var(--bg-sunken);   /* visible while loading */
  }

  .card__body {
    display: flex;
    flex-direction: column;
    gap: var(--card-gap);              /* the parent owns the gaps */
    padding: var(--card-pad);
    flex: 1;                           /* so __footer's auto margin has room */
  }

  .card__meta {
    font: var(--type-label);
    letter-spacing: var(--tracking-wide);
    color: var(--fg-muted);
    text-transform: uppercase;
  }

  .card__title {
    font: var(--type-h4);
    color: var(--fg-strong);
    text-wrap: balance;
  }

  .card__text {
    color: var(--fg-muted);
    max-inline-size: var(--measure-narrow);
  }

  /* `margin-block-start: auto` is the ONE outer margin a child may set, and
     it is not a gap: in flex layout `auto` is a distribution instruction
     ("absorb the free space"), not a spacing value. There is no token for it
     because it has no magnitude. Pinning the footer to the bottom is what
     makes a row of unequal cards line their actions up. */
  .card__footer {
    margin-block-start: auto;
    display: flex;
    gap: var(--gap-tight);
    align-items: center;
  }

  /* Whole-card click target. The overlay makes the entire card activate the
     title's link, while the accessibility tree still sees one ordinary link
     with the title as its name. */
  .card__link {
    color: inherit;
    text-decoration: none;

    &::after {
      content: "";
      position: absolute;
      inset: 0;
      z-index: var(--z-raised);
    }

    /* The card clips overflow, and a ring drawn outside the border box is
       clipped with it: an outline exactly as much as a box-shadow. So draw
       it inside, with a negative offset. See reset.css §7. */
    &:where(:focus-visible) {
      box-shadow: none;
      outline: var(--stroke-focus) solid var(--border-focus);
      outline-offset: calc(var(--stroke-focus) * -1);
    }
  }

  /* ---- Variants ----------------------------------------------------- */

  .card:where([data-variant="flat"]) {
    --card-shadow: var(--elevation-flat);
    --card-bg:     var(--bg-sunken);
    --card-border: transparent;
  }

  .card:where([data-size="compact"]) {
    --card-pad: var(--pad-well);
    --card-gap: var(--gap-tight);
  }

  /* Runtime value passed in as a custom property — Law 4's only exception.
     <article class="card" style="--card-span: 2"> */
  .card:where([style*="--card-span"]) {
    grid-column: span var(--card-span, 1);
  }
}
```

**Usability note (Law 8).** The `::after` overlay breaks text selection inside the card and swallows any second link in the body. Both are real regressions. Use it only when the card has exactly one action and its text is not worth copying; otherwise make the title the only link and give the card `:hover` feedback driven by `:has(.card__link:hover)`.

---

## 10. Scoping without a bundler

There is no build step to hash your class names, so the naming convention *is* the scoping mechanism. It has to be strict enough that collisions are impossible by construction.

### BEM, done correctly

The grammar, exactly:

```
.block
.block__element
.block--modifier          ← we use data-* instead; see below
```

- **Block**: an independently meaningful thing. `card`, `button`, `field`, `site-header`. Multi-word blocks use one hyphen: `.site-header`.
- **Element**: a part with no meaning outside its block, joined by `__`. `.card__title`.
- **Never chain elements.** `.card__body__title` is not BEM. The grammar is deliberately flat: an element belongs to its *block*, not to another element. If the nesting is real, the inner thing is a new block.

**`__element` vs a new block** — the test is *can this thing be lifted out and used elsewhere?*

- `.card__title` cannot. Outside a card it means nothing. Element.
- A badge inside a card *can*. It appears in tables and list rows too. It is `.badge`, a block, and it is composed: `<span class="badge card__badge">`, where `.card__badge` sets only position/spacing and `.badge` sets appearance. This is the single most useful BEM idea and the most commonly missed one.

Keep the depth-2 discipline: a block has elements; elements do not have elements.

### Why `data-*` instead of `--modifier`

`.button--primary` and `data-variant="primary"` carry the same information. The attribute wins on three counts: it is a named axis (you can read "the variant axis" out of the markup), it maps directly to a prop and a TypeScript union, and the set of values is enumerable by grepping one string. Classic `--modifier` is still fine — it is BEM's own answer — but pick one and use it everywhere.

### `@scope`, and when it is worth it

`@scope` gives real, native scoping, including an explicit lower boundary:

```css
@layer components {
  @scope (.card) to (.card__body :where(.card, [data-scope])) {
    :scope { … }
    .title { … }           /* only matches inside .card, above the boundary */
  }
}
```

Two things it buys that BEM cannot: the **donut** (`to (…)`) stops the scope at a nested component's root, which is the actual solution to "my card styles leaked into the card inside my card"; and proximity — when two scopes both match, the *closer* scope root wins regardless of specificity.

Support notes as of 2026: shipped in Chromium and Safari, and in Firefox from 128. That is Baseline "newly available", not "widely available" — meaning a meaningful tail of business and locked-down enterprise browsers do not have it. Treat it as an *enhancement over* a correct BEM structure, not a replacement for one: name your classes as though `@scope` did not exist, then add it where a real nesting collision exists. Never let `@scope` be the only thing preventing a collision.

### The naming discipline that replaces build-time scoping

Four rules. They are boring and they are the entire mechanism.

1. **One block name per file, and the filename is the block name.** `card.css` may define selectors starting `.card` and nothing else. Violations are a one-line grep.
2. **Block names are globally unique and never generic.** `.card`, not `.item`, `.wrapper`, `.container`, `.content`, `.inner`, `.box`. Generic names are how two features collide.
3. **Utilities carry a prefix.** `.u-visually-hidden`, `.u-flow`. It makes them visible in markup and prevents a utility ever colliding with a block.
4. **Layout primitives carry a prefix too.** `.l-stack`, `.l-grid`, `.l-center`. Layout is a different kind of thing from a component and the markup should say so.

---

## 11. The utility layer

A utility layer becomes a framework the moment you add the second spacing utility. Hold the line by requiring a written justification for each one.

**A class earns a place in `utilities.css` only if all four are true:**

1. It expresses **one** decision, not a style.
2. That decision is genuinely **orthogonal** to every component — it is about the *situation*, not the thing.
3. Getting it right by hand is **error-prone** (visually-hidden is nine lines nobody remembers).
4. There are **fewer than ~20** of them in total.

The set that passes:

```css
@layer utilities {

  /* Available to screen readers, invisible on screen. The nine lines people
     get wrong: `display: none` and `visibility: hidden` remove it from the
     a11y tree; `text-indent: -9999px` breaks RTL; `width/height: 0` makes
     some engines skip it. This is the version that works. */
  .u-visually-hidden:not(:focus-visible) {
    position: absolute;
    /* stylelint-disable-next-line declaration-property-value-allowed-list -- design-audit-ignore-next-line: L1 -- the technique's 1px box, not a design size */
    inline-size: 1px;
    /* stylelint-disable-next-line declaration-property-value-allowed-list -- design-audit-ignore-next-line: L1 -- the technique's 1px box, not a design size */
    block-size: 1px;
    padding: 0;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
    border: 0;
  }

  /* Vertical rhythm for content whose structure you do not control. The owl
     lives on the PARENT (Law 2); the spacing is passed in as a property so
     it is set once per usage, not per child. */
  .u-flow {
    --flow: var(--gap-grouped);
    > * + * { margin-block-start: var(--flow); }
  }

  /* One-dimensional stack with a real gap. Prefer this over .u-flow whenever
     the children are elements you control. */
  .u-stack {
    display: flex;
    flex-direction: column;
    gap: var(--gap-grouped);
  }

  .u-balance  { text-wrap: balance; }
  .u-pretty   { text-wrap: pretty; }
  .u-measure  { max-inline-size: var(--measure-prose); }

  /* Truncation. One line is a different mechanism from many, and the
     many-line one needs the -webkit- prefixed box model on every engine. */
  .u-truncate {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .u-clamp {
    --clamp-lines: 3;              /* override inline: style="--clamp-lines:2" */
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: var(--clamp-lines);
    overflow: hidden;
  }

  /* Reserves layout space before media loads — the single biggest CLS fix. */
  .u-ratio-16-9 { aspect-ratio: 16 / 9; }
  .u-ratio-4-3  { aspect-ratio: 4 / 3; }
  .u-ratio-1-1  { aspect-ratio: 1 / 1; }
}
```

**What must never become a utility:**

- **Spacing scales.** `.u-mt-4`, `.u-p-6`. They put the gap on the child, which is Law 2 inverted, and they re-open the closed scale as a class namespace.
- **Colours.** `.u-text-muted` duplicates the token layer with a second, unthemed vocabulary.
- **Type sizes.** `.u-text-lg` skips the `--type-*` role and separates size from weight and leading, which is the exact drift the roles prevent.
- **Display and flex properties.** `.u-flex`, `.u-items-center`. If an element needs a layout, it is a layout primitive in `layout.css` with a name, not three utilities in the template.

If you find yourself wanting all of those, you want Tailwind, and that is a legitimate choice — but make it deliberately, not by accreting a bad copy of it in `utilities.css`.

---

## 12. Progressive enhancement

**The rule: a fallback must be a simpler correct design, not a broken one.** "Correct" means a user on the fallback path never sees an overlap, an unreadable contrast, a cut-off word or a control they cannot reach. They see a design with less nuance. If you cannot describe the fallback as a design decision, you do not have a fallback, you have a bug you have not seen yet.

Write the simple version first, unconditionally. Enhance inside `@supports`. Never write the fancy version first and try to patch it back.

### `oklch()`

Every colour in this system funnels through the Tier-1 ramps in `tokens.css`, which means the entire fallback is one block in one file — roughly twenty declarations for a whole palette. That is the architectural payoff cashing out.

```css
@layer tokens {
  @supports not (color: oklch(0% 0 0)) {
    :root {
      --neutral-0:   #ffffff;
      --neutral-50:  #fafaf9;
      --neutral-100: #f5f5f4;
      /* … each ramp step, sRGB-converted, generated by
         scripts/generate_color_ramp.py --format hex … */
      --accent-500:  #e2622b;
    }
  }
}
```

Not one component changes. Tier 2 re-points automatically because it references Tier 1 by name.

Note what is *not* being attempted: matching the wide-gamut rendering. The fallback is deliberately the sRGB approximation — a simpler correct design.

### Container queries

```css
/* Simpler correct design: the card is always vertical. Readable everywhere. */
.card__body { display: flex; flex-direction: column; gap: var(--card-gap); }

@supports (container-type: inline-size) {
  .card { container-type: inline-size; container-name: card; }

  @container card (inline-size > 30rem) {
    .card__body { flex-direction: row; align-items: center; }
  }
}
```

The `@supports` wrapper is strictly optional here — an unsupporting browser ignores the `@container` block anyway — but wrapping it keeps the enhancement and its precondition in one readable unit, and it stops someone later adding a declaration outside the query that assumes containment.

**Container query units** (`cqi`, `cqw`) have no graceful fallback: a length that does not parse invalidates the whole declaration. If you use them, provide the fallback declaration immediately above, relying on the cascade:

```css
.card__title {
  font: var(--type-h4);              /* parsed everywhere */
  /* stylelint-disable-next-line declaration-property-value-allowed-list -- design-audit-ignore-next-line: L1 --
     a cqi length cannot sit in a token: var() makes an unsupported value invalid at computed-value
     time, which resets font-size instead of falling back to the declaration above. */
  font-size: clamp(1rem, 4cqi, 1.75rem);   /* dropped where unsupported */
}
```

### `:has()`

Selector support is detected with `@supports selector(…)`, not a property test:

```css
/* Simpler correct design: the label sits above the field, always. */
.field__label { display: block; }

@supports selector(:has(*)) {
  /* Enhancement: the field group reacts to its own contents. */
  .field:has(.field__control:user-invalid) {
    --field-border: var(--border-strong);
    --field-fg:     var(--fg-danger);
  }
}
```

Two cautions worth internalising. `:has()` is *not* forgiving — one invalid selector inside invalidates the whole argument, unlike `:is()`. And it is easy to write a `:has()` that forces style recalculation on a large subtree during scroll; keep the argument shallow and scoped to a component root.

---

## 13. PostCSS, if you use it

PostCSS is optional in this stack and should stay optional: the source must remain a valid stylesheet that a browser can run directly. That is not purity — it is the property that makes the "hands off cleanly" argument in §1 true.

**One rule governs the whole config: PostCSS may not introduce syntax the browser cannot ship.** No mixins, no `@extend`, no loops, no functions the CSS spec does not have. If a plugin lets you write something that would not parse in a browser, you have re-invented a preprocessor, the source stops being debuggable, and DevTools now shows output you did not write.

The minimum useful set is three plugins.

**`postcss-import`** — flattens `@import` at build time, removing the request waterfall from §4. Nothing else. Verify it preserves `layer()` wrapping on vendor imports (recent versions do; it is worth a test in your build, because a silently dropped `layer()` puts the datepicker back on top of your components).

**`postcss-custom-media`** — the one genuinely necessary plugin, because **custom properties do not work in media query conditions.** `@media (min-width: var(--bp-md))` is invalid and silently never matches. This is the one real gap between the token file and the stylesheet:

```css
/* media.css */
@custom-media --md (min-width: 48rem);   /* mirrors --bp-md */
@custom-media --lg (min-width: 64rem);   /* mirrors --bp-lg */

/* usage */
@media (--md) { .l-grid { grid-template-columns: repeat(2, 1fr); } }
```

The literals are duplicated between `tokens.css` and `media.css`; that duplication is unavoidable today and is an explicit audit item (§15). Without the plugin, breakpoint literals scatter across every component file instead, which is strictly worse.

**`postcss-preset-env`** — configure it *narrowly*, feature by feature. Left on its defaults it enables a large set of transforms, some of which produce output that no longer resembles your source.

```js
// postcss.config.js
module.exports = {
  plugins: {
    'postcss-import': {},
    'postcss-custom-media': {},
    'postcss-preset-env': {
      stage: false,                 // opt in explicitly; no stage-based bundle
      features: {
        'custom-media-queries': false,   // handled above
        'nesting-rules': false,          // native; do NOT transpile it away
        'oklab-function': { preserve: true },  // emits an sRGB fallback ABOVE
        'color-mix': { preserve: true },
      },
      autoprefixer: { grid: false },
    },
  },
};
```

`preserve: true` matters: it emits the fallback declaration *above* the modern one, so capable browsers still get `oklch()`. Without it the plugin replaces your source and the wide-gamut colour is gone for everyone.

**Autoprefixer: do you still need it?** For a modern browser target, almost never — grid, flexbox, transforms, transitions, custom properties and sticky positioning have needed no prefix for years. It stays in the config for a short, real list: `-webkit-backdrop-filter` (Safari), `-webkit-mask-*`, and `-webkit-text-size-adjust`. It is bundled inside `postcss-preset-env`, so you do not install it separately. Set your `browserslist` honestly from analytics; a stale `> 0.2%` query is why some teams still ship 40% prefix bloat.

**What is deliberately absent:** `postcss-nested` (native nesting exists; transpiling it changes the selectors DevTools shows you), `postcss-mixins`, `postcss-simple-vars` (custom properties are better — they cascade and they theme), and any plugin that generates utility classes.

---

## 14. Anti-patterns

**`margin-top` on a component root.** The component now injects a gap into every parent that adopts it, and the gap is wrong in at least one of them. It also breaks `gap` arithmetic: flex `gap` and child margin add rather than collapse. *Fix:* delete it; the parent sets `gap`.

**A literal outside `tokens.css`.** `padding: 13px`, `color: #f5f5f5`, `z-index: 9999`. Each one is a decision made without the system's knowledge and invisible to theming, density and dark mode. *Fix:* find the Tier-2 role; if none fits, the missing role is the actual work.

**Reaching into Tier 1 from a component.** `gap: var(--space-6)`. It works, and then "a bit more air in cards" becomes a grep for `--space-6` across forty files, half of which meant something else by it. *Fix:* `var(--pad-card)`.

**`!important`.** In a layered codebase it inverts layer order, so it beats things you did not intend and loses to things you did. *Fix:* a later layer, or `revert-layer`.

**An ID in a selector.** (1,0,0) that no class can ever beat, and with nesting it contaminates every descendant rule through `:is()` (§6). *Fix:* a class.

**A rule outside a layer.** It silently beats everything in `overrides.css` and the developer who hits it will not know why. *Fix:* put it in a layer; the audit catches this.

**Nesting deeper than two.** Hides selectors from grep, compounds specificity invisibly, and hard-codes DOM shape. *Fix:* the depth-3 thing is a component.

**Styling a component part by element.** `.card h3`. Detaches the moment the heading level changes for accessibility reasons. *Fix:* `.card__title`.

**`.is-active` classes for state that the DOM already expresses.** The class and `aria-expanded` will drift; one of them will be wrong, and it will be the one screen readers use. *Fix:* style the ARIA attribute.

**Two homes for one component's styles.** A base rule in `components/card.css` and three "small tweaks" inline in a template. Nobody can find the third one. *Fix:* one file; inline `style` only to pass a runtime number in as a custom property.

**A media query inside a component that uses a hard-coded breakpoint.** `@media (min-width: 812px)`. It will not match `--bp-*`, and it makes the component depend on the viewport when it almost always depends on its own width. *Fix:* `@custom-media`, or better, a container query.

**Duplicating dark mode in components.** `[data-theme="dark"] .card { background: … }`. Every component now has to be re-audited on every theme change. *Fix:* re-point the Tier-2 role in `tokens.css`; `tokens.css` contains no component selector and that is the test.

**Anonymous `overrides.css` entries.** An undated, unsigned override is permanent by default. *Fix:* date, owner, removal condition, or it does not merge.

---

## 15. The audit (Law 9)

This stack enforces nothing at build time, so these run in CI and fail the build. Ship them before the first component.

```bash
S=styles

# 1. Literal lengths outside tokens.css (the Law-1 check).
grep -rnE '^\s*[a-z-]*(margin|padding|gap|inset|top|right|bottom|left|width|height|size)[a-z-]*:\s*-?[0-9.]+(px|rem|em)' \
  $S --include='*.css' | grep -v 'tokens.css'

# 2. Colour literals outside tokens.css.
grep -rnE ':\s*(#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\()' $S --include='*.css' \
  | grep -v 'tokens.css'

# 3. Tier-1 reached from a component (Law 6).
grep -rnE 'var\(--(space|text|neutral|accent|leading|tracking|shadow|dur|ease)-' \
  $S/components $S/layout.css $S/utilities.css

# 4. Child outer margins (Law 2). `margin-*: auto` is exempt; see card.css.
#    -P only: GNU grep rejects -E and -P together, and the negative lookahead
#    requires PCRE.
grep -rnP 'margin(-block-start|-top|-inline|-block)?:\s*(?!auto)' $S/components

# 5. !important and IDs (Law 5).
grep -rn '!important' $S --include='*.css'
grep -rnE '^\s*#[a-zA-Z]' $S --include='*.css'

# 6. Unlayered rules — every file must open with @layer.
for f in $(find $S -name '*.css' ! -name 'index.css'); do
  head -n 40 "$f" | grep -q '@layer' || echo "UNLAYERED: $f"
done

# 7. Breakpoint literals outside tokens.css / media.css (the §13 duplication).
grep -rnE '@media[^{]*\([^)]*[0-9]+(px|rem)' $S --include='*.css' \
  | grep -vE 'tokens.css|media.css'

# 8. Nesting depth. Three or more leading indent levels inside a @layer block
#    is the cheap proxy; a stylelint rule is the real one.
```

Pair the greps with **stylelint** for the checks a regex cannot make honestly:

```json
{
  "rules": {
    "max-nesting-depth": [2, { "ignoreAtRules": ["media", "supports", "container"] }],
    "selector-max-id": 0,
    "selector-max-specificity": "0,3,0",
    "declaration-no-important": true,
    "selector-max-type": [0, { "ignoreTypes": ["/^h[1-6]$/"] }],
    "custom-property-pattern": "^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
  }
}
```

And the two checks only a human can make, in review:

- **Does every new Tier-3 property default to a Tier-2 role?** A `--btn-*` defaulting to a literal is Law 1 laundering.
- **Does the fallback path read as a simpler correct design?** Load the page with `oklch` support faked off and look at it. Nobody has ever caught this with a regex.

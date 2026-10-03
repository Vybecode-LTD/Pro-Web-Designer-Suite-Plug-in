# Tailwind, Bound to the System

How this studio uses Tailwind without letting Tailwind become the system. The
theme files live in `assets/configs/theme.css` (v4) and
`assets/configs/tailwind.config.ts` (v3); the enforcement lives in
`assets/configs/eslint.design.config.mjs`,
`assets/configs/stylelint.config.mjs` and
`assets/configs/pre-commit-design-gate.sh`. This document explains why each of
them is shaped the way it is.

Law 1 governs this file as it governs the rest: **no component ever contains a
value.** In Tailwind that reads: no component ever contains a bracket.

---

## Contents

1. [The problem Tailwind creates, and the shape of the fix](#1-the-problem-tailwind-creates-and-the-shape-of-the-fix)
2. [Tailwind v4: wiring `@theme`](#2-tailwind-v4-wiring-theme)
3. [`@theme` vs `@theme inline`, and why dark mode breaks](#3-theme-vs-theme-inline-and-why-dark-mode-breaks)
4. [Semantic utilities: exposing roles, not steps](#4-semantic-utilities-exposing-roles-not-steps)
5. [Class organization](#5-class-organization)
6. [Variants with `cva` / `tv`](#6-variants-with-cva--tv)
7. [When NOT to use a utility](#7-when-not-to-use-a-utility)
8. [Dark mode and density, with zero component changes](#8-dark-mode-and-density-with-zero-component-changes)
9. [Failure modes in agency work](#9-failure-modes-in-agency-work)
10. [Enforcement: what runs, and when](#10-enforcement-what-runs-and-when)
11. [Appendix: Tailwind v3](#11-appendix-tailwind-v3)

---

## 1. The problem Tailwind creates, and the shape of the fix

### 1.1 Two scales, one codebase

Tailwind ships a complete design system: a spacing scale, a palette of 22 color
ramps, a type scale, a radius scale, a shadow scale. Every one of them is
competent. Not one of them is *ours*.

Our card padding is `--pad-card` (24px, density-scaled, re-pointable).
Tailwind's is `p-6` (24px, fixed, anonymous). They agree until the client says
"a bit more air in cards", at which point the token moves and `p-6` does not —
and `p-6` is now 40 components deep, indistinguishable by grep from the `p-6`
that was always meant to be 24px.

This is not a discipline problem. It is two valid answers being available, one
of which is faster to type.

### 1.2 The three doors, and which ones close

Tailwind lets a value reach the browser three ways:

| Door | Example | Can config close it? |
|---|---|---|
| A stock scale class | `p-6`, `bg-neutral-800`, `text-sm` | **Yes** — delete the scale |
| An arbitrary value | `mt-[13px]`, `text-[#e8440a]` | **No** — it is a parser feature |
| The `style` prop | `style={{ padding: 16 }}` | **No** — it is React |

So the fix has two halves, and skipping either one leaves a door open:

> **The theme IS the token file** — Tailwind's scale is *replaced*, not
> extended, so an off-scale class generates no CSS at all. That is silent,
> not a build error: the element simply ships unstyled.
>
> **Arbitrary values, literal utilities and the `style` prop are lint-banned**
> — because no amount of theme configuration can shut them. `duration-300`,
> `z-50`, `border-2`, `bg-accent/37` and `p-(--space-6)` all still generate
> with `--*: initial`; the ESLint config and `audit_design.py` refuse them.

### 1.3 Replaced, not extended

This is the whole trick, and it is one line:

```css
@theme {
  --*: initial;   /* every default namespace, gone */
}
```

After that line `p-4` does not exist — not "is discouraged": the class is not
generated, the CSS is not emitted, the element renders unpadded. Nor do
`bg-neutral-800`, `text-sm`, `rounded-lg`, `shadow-md`, `duration-200`,
`space-y-4`. What exists is what we bind, and what we bind are Tier-2 roles:

```
p-card   gap-related   bg-surface   text-muted   rounded-panel   shadow-card
```

The deletion converts a *review* problem ("someone should notice `p-6` here")
into a *build* problem (the element is visibly unpadded in dev). Reviews are
sampled; builds are not.

The consequence is the point, not a side effect: **you cannot express an
off-system value in a class name any more.** When a designer hands you a 28px
gap, the right response is not `gap-[28px]` but "the scale has 24 and 32 —
which did you mean?" Nine times out of ten the answer is one of them.

### 1.4 Why `--spacing` stays deleted

Tailwind v4 has a single multiplier, `--spacing: 0.25rem`, that generates
`p-<any number>` on demand: `p-4` is `calc(var(--spacing) * 4)`, and so is
`p-7`, `p-13`, `p-97`.

`--*: initial` removes it, and **we deliberately do not restore it.** That
single omission is Law 3 — the scale is closed — expressed in one line of
config. With no generator, an off-scale numeric step has no way to come into
existence. `p-7` generates nothing — no 28px, and no error either, which is
why the linter has to catch it.

Restoring `--spacing` while defining named steps looks harmless and reopens the
whole door.

---

## 2. Tailwind v4: wiring `@theme`

The complete, working setup. The file is `assets/configs/theme.css`; this is
the part you must get right in the project's entry stylesheet.

### 2.1 Do not use `@import "tailwindcss"`

The single-line import hardcodes Tailwind's own layer order —
`theme, base, components, utilities` — which cannot express Law 5's seven
layers. Split it:

<!-- snippet: web-design-studio/assets/configs/index.tailwind.css#entry -->
```css
/* 1. The order, first. `@import "tailwindcss"` would state Tailwind's own
      four layers instead, so its files are imported one by one. `vendor`
      is named before there is any vendor CSS: a layer first named by its
      import is appended after `overrides`. */
@layer reset, vendor, tokens, theme, base, layout, components, utilities, overrides;

/* 2. Tailwind's files name no layer: wrap each as it loads. */
@import "tailwindcss/preflight.css" layer(reset);
@import "tailwindcss/theme.css"     layer(theme);
@import "tailwindcss/utilities.css" layer(utilities);

/* 3. These open their own @layer block, so import them bare. */
@import "./tokens.css";
@import "./theme.css";                  /* assets/configs/theme.css */
@import "./base.css";
@import "./layout.css";

/* 4. CSS you do not control names no layer: wrap it as it loads.
        @import "../vendor/datepicker.css" layer(vendor);
      Then one line per component file:
        @import "./components/card.css"; */
```

Two details that are not obvious:

- **The bare `@layer` statement must come first.** It is the one rule CSS
  permits before `@import`, and the only thing that fixes the order: layers
  rank by the order they are *first named*, so a layer used before it is
  declared is appended to the end, where it beats `utilities` and `overrides`.
  The symptom is a component correct in dev and wrong in production, because a
  bundler split changed which file loaded first.
- **`utilities` must come after `components`.** Both are often a single class,
  so without the layer order `p-card-lg` on a `.card` loses to
  `.card { padding: var(--pad-card) }` by source order — the classic "the
  utility isn't working" ticket.

### 2.2 The `@theme` block

Structure, in order:

```css
@theme {
  --*: initial;                /* §1.3 — burn the default theme            */
  --breakpoint-md: 48rem;      /* literal: media queries cannot read var() */
  --aspect-video: 16 / 9;
}

@theme inline {                /* §3 — everything else, and inline matters */
  --color-surface:   var(--bg-surface);
  --spacing-card:    var(--pad-card);
  --text-h2:         var(--text-3xl);
  --text-h2--line-height: var(--leading-tight);
  --radius-card:     var(--radius-lg);
  --shadow-card:     var(--elevation-card);
  --ease-enter:      var(--ease-out);
  /* … */
}

@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));

@source "../../packages/ui/src";

@utility z-modal { z-index: var(--z-modal); }
```

### 2.3 What `--*: initial` takes with it

It takes *everything*, including things that are not design decisions. Give
these back consciously:

| Gone | Give back? | Why |
|---|---|---|
| `--spacing` | **No** | §1.4. The closed scale depends on its absence. |
| `--breakpoint-*` | Yes, as literals | §2.4 |
| `--color-transparent/current/inherit` | Yes | CSS keywords, not colors |
| `--animate-*` **and their keyframes** | Yes, if used | Tailwind only emits keyframes for animations it generates; delete the theme entry and the `@keyframes` goes with it, so `animate-spin` produces a valid `animation` referencing a name that does not exist |
| `--default-font-family`, `--default-transition-duration` | Yes | Preflight's base values; without them the page falls back to Times New Roman and a 0s transition |
| `--container-*` | **No** | §2.5 |

### 2.4 Breakpoints must be literal

```css
--breakpoint-md: 48rem;   /* mirrors --bp-md in tokens.css */
```

Not `var(--bp-md)`. A media query *condition* cannot read a custom property:
`@media (width >= var(--bp-md))` is invalid and the browser drops the entire
block without a word. Every responsive rule silently stops applying.

This is a genuine duplication and the only honest way to handle it is to make
drift detectable rather than pretend it cannot happen:
`scripts/audit_design.py` diffs `--breakpoint-*` against `--bp-*` and fails on
mismatch. Change one, change both.

### 2.5 `--container-*` is a trap; use `@utility` instead

It is tempting to write `--container-prose: var(--measure-prose)` and get
`max-w-prose` for free. Do not.

The `--container-*` namespace feeds **two** things: the `max-w-*` utilities
(a declaration, where `var()` is fine) and the container-query variants
`@prose:` (a `@container` *condition*, where `var()` is invalid for exactly the
reason in §2.4). Tailwind generates both. The first works; the second emits an
invalid condition the browser discards. You get a variant that silently does
nothing, on some elements, some of the time.

`@utility` only ever emits a declaration, so it is safe:

```css
@utility max-w-prose   { max-inline-size: var(--measure-prose); }
@utility max-w-content { max-inline-size: var(--width-content); }
```

### 2.6 `@custom-variant dark`

tokens.css themes on `[data-theme="dark"]`, so the `dark:` variant must be
redefined to match:

```css
@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));
```

`:where()` holds the variant at zero specificity, which is what stops `dark:`
from accidentally out-ranking a later `hover:`. The second selector covers
descendants, so a scoped `<section data-theme="dark">` themes its subtree.

**If a component has more than one or two `dark:` classes, the component is
wrong, not dark mode.** Every Tier-2 color role is already re-pointed by
`[data-theme="dark"]`; `bg-surface` is correct in both themes with no variant
at all. A pile of `dark:` classes means a component is reading something that
is not a role.

### 2.7 `@source`

Tailwind scans the project root, honours `.gitignore`, and does not look inside
`node_modules`. A design system shipped as a workspace package therefore
generates no CSS — the component renders unstyled in the consuming app and
looks like a build bug, not a config omission.

```css
@source "../../packages/ui/src";   /* relative to THIS FILE */

@source not "../../**/dist";       /* never scan build output */
@source not "../../**/*.snap";
```

Scanning `dist` is worse than scanning nothing: stale class names from an old
build keep dead CSS alive forever and make the unused-class audit useless.

`@source inline(...)` is the only legitimate safelist, and only when a class
name genuinely comes from data — a CMS field, an API enum — and cannot exist as
a literal anywhere in source. Everything else that "needs safelisting" is a
dynamically-constructed class name, which is a bug; see §9.1.

### 2.8 Name collisions are a feature

Four Tailwind namespaces collide exactly with Tier-1 token names in tokens.css:

| Namespace | Collides with |
|---|---|
| `--text-*` | `--text-sm`, `--text-3xl`, … |
| `--radius-*` | `--radius-md`, `--radius-lg`, … |
| `--shadow-*` | `--shadow-sm`, `--shadow-md`, … |
| `--ease-*`, `--leading-*`, `--tracking-*`, `--font-*` | all of them |

CSS cannot express `--radius-lg: var(--radius-lg)`. So every Tailwind entry
*must* be named after its role rather than its step:

```css
--radius-card:  var(--radius-lg);     /* rounded-card  */
--shadow-card:  var(--elevation-card);/* shadow-card   */
--text-h2:      var(--text-3xl);      /* text-h2       */
--ease-enter:   var(--ease-out);      /* ease-enter    */
```

That is Law 6 arriving for free. The collision is not an obstacle to work
around; it is the constraint that makes the wrong thing unwriteable.

---

## 3. `@theme` vs `@theme inline`, and why dark mode breaks

Read this before changing anything in the theme file. Getting it wrong does not
throw. It produces a product where dark mode works on the page and fails inside
a scoped subtree, and nobody can see why.

### 3.1 The mechanism

Plain `@theme` emits an indirection and points the utility at it:

```css
/* @theme { --color-surface: var(--bg-surface); } generates: */
:root        { --color-surface: var(--bg-surface); }
.bg-surface  { background-color: var(--color-surface); }
```

A custom property whose value contains `var()` is substituted **at
computed-value time, on the element where the declaration applies** — here,
`:root`. So `--color-surface` resolves once against `:root`'s `--bg-surface`
(the light value), and what inherits down the tree is that resolved color.

Now put `[data-theme="dark"]` on a `<section>`. It re-points `--bg-surface`
inside that subtree, but nothing re-declares `--color-surface` there, so the
frozen light value inherits straight through. Every `bg-surface` in the section
stays light. No warning, no error, no failing test.

### 3.2 What `inline` changes

```css
/* @theme inline { --color-surface: var(--bg-surface); } generates: */
.bg-surface { background-color: var(--bg-surface); }
```

The indirection is gone. `var(--bg-surface)` now resolves **on the element the
utility is applied to**, so it sees whatever `[data-theme]` ancestor that
element actually has.

### 3.3 The rule

> Use `inline` for any theme variable whose value is `var(...)` of a token that
> a theme selector can re-point.

In this system that is **every Tier-2 token**, for two reasons at once: colors
are re-pointed by `[data-theme="dark"]`, and every Tier-2 spacing role is
`calc(var(--space-n) * var(--density))` with `--density` re-pointed by
`[data-density]` on a subtree.

The density case is the one teams miss, because they read the `inline` advice in
the color docs and apply it only to colors. Without `inline` on spacing, the
admin table wrapped in `data-density="compact"` renders at exactly the default
density and Law 7 quietly stops being true — the compact mode ships, looks
identical to comfortable, and someone spends an afternoon on it.

So: **the whole mapping block is `inline`.** When in doubt, `inline` — it costs
nothing when the token is not themed.

### 3.4 The price

With `inline`, do not assume `--color-surface` exists at runtime. It is a
compile-time name for generating utilities, not a variable to read. In
hand-written CSS, read the Tier-2 token:

```css
.card { background: var(--bg-surface); }    /* correct */
.card { background: var(--color-surface); } /* do not  */
```

### 3.5 The four-line test

Put this in any project and look at it with `[data-theme="dark"]` on a nested
element, not on `<html>`:

```html
<div class="bg-canvas p-card">
  <section data-theme="dark" class="bg-surface p-card">
    <p class="text-default">If this is dark, inline is wired correctly.</p>
  </section>
</div>
```

If the section is light, the theme file is missing `inline`. Do this once per
project, on day one. It takes thirty seconds and it is the single highest-value
check in this document.

---

## 4. Semantic utilities: exposing roles, not steps

### 4.1 What a class name should say

```html
<!-- measurements -->
<article class="p-6 gap-3 bg-neutral-800 text-neutral-400 rounded-xl">

<!-- intent -->
<article class="p-card gap-related bg-surface text-muted rounded-panel">
```

The second version tells you what the thing *is*. It survives a rebrand, it
follows `[data-density]`, it is already correct in dark mode, and it can be read
aloud in a design review by someone who does not write CSS. The first version is
a set of measurements that happened to be correct on the day it was typed.

### 4.2 The vocabulary

**Spacing — the proximity ladder.** Six steps, chosen by *meaning*. This is the
whole of Gestalt proximity expressed as six class names: two things at
`gap-related` read as one group; the same two at `gap-separate` read as two.

```
gap-fused     icon + its label
gap-tight     label + its input
gap-related   items within one group
gap-grouped   sibling cards, table rows
gap-separate  distinct groups
gap-distinct  unrelated blocks
```

**Spacing — insets.** `p-card`, `p-card-lg`, `p-well`, `px-inline-md`,
`py-block-sm`.

**Spacing — page rhythm.** `gap-section`, `gap-subsection`, `gap-block`,
`px-gutter`. All fluid: `gap-section` is 64px on a 390px phone and 144px on a
laptop, from one class. A fixed section gap is always wrong at one of the two
ends.

**Color.** Tailwind has one color namespace, which generates `bg-x`, `text-x`,
`border-x`, `ring-x`, `fill-x` and the rest from a single entry — with no way to
say "this role is a fill, never an ink". So names are chosen for the position
they are *meant* to occupy:

| Family | Classes |
|---|---|
| Surfaces | `bg-canvas` `bg-surface` `bg-raised` `bg-sunken` `bg-inverse` |
| Interaction | `bg-hover` `bg-active` `bg-selected` `bg-disabled` |
| Text | `text-default` `text-strong` `text-muted` `text-subtle` `text-link` `text-on-accent` `text-on-inverse` |
| Intent fills | `bg-accent` `bg-success` `bg-warning` `bg-danger` |
| Intent inks | `text-accent-fg` `text-success-fg` `text-warning-fg` `text-danger-fg` |
| Lines | `border-line-subtle` `border-line` `border-line-strong` `ring-focus` |

The convention where a role needs both: **bare name = the fill, `-fg` suffix =
the ink.** `bg-danger` is the 500-weight solid; `text-danger-fg` is the
700-weight that clears 4.5:1 on a light surface. Writing `text-danger` puts
500-weight text on a light background and drops you under contrast — it is
syntactically valid and wrong, which is why the audit checks it.

The leak is real and worth naming: `bg-muted` and `text-canvas` are also
generated and are also nonsense. One namespace cannot encode position. Design
review and the audit catch these; the type system cannot.

**Typography.** Each role ships size + leading + tracking + weight from one
class, via Tailwind's `--text-x--line-height` companions:

```
text-display  text-display-sm  text-h1  text-h2  text-h3  text-h4
text-lead  text-body  text-prose  text-ui  text-label  text-caps  text-meta  text-code
```

You cannot get `text-h2`'s size without its leading. That is the point: a 35px
heading left at body leading is the single most common typographic bug in
shipped marketing sites.

### 4.3 Why `bg-neutral-800` is a Law 6 violation even though it is easy

Two failures, and the second is the expensive one.

**It skips a tier.** `--neutral-800` is Tier 1 — a raw value with no opinion
about what it is for. `--bg-surface` is Tier 2 — a value bound to a role. When
the brand shifts, Tier 2 re-points and every component follows. Tier 1 cannot
move: it is the same graphite in every theme, which is what makes it primitive.

**It does not follow the theme.** `--bg-surface` becomes `--neutral-950` under
`[data-theme="dark"]`; `--neutral-800` is `--neutral-800` forever. So
`bg-neutral-800` is a card that stays dark gray in light mode and barely changes
in dark mode — a component that opted out of the theme system entirely, using a
class that looked completely reasonable.

Here it is worse than wrong, and usefully so: with `--*: initial` the class
generates *nothing*, so the element ships with no background. A visible bug
beats an invisible one.

**When no role fits**, the answer is not a bracket and not a Tier-1 class: add a
Tier-2 role to `tokens.css`, bind it in `theme.css`, and the class exists
everywhere. Four minutes, and it is right far more often than people expect.

---

## 5. Class organization

### 5.1 The canonical order

```
layout → box → typography → visual → interactive → state variants
```

| Group | What it covers |
|---|---|
| Layout | `flex` `grid` `grid-layout` `items-center` `justify-between` `gap-related` |
| Box | `p-card` `px-gutter` `max-w-content` `size-tap` `tap-target` |
| Typography | `text-h2` `font-body` `font-semibold` `leading-body` `tracking-ui` |
| Visual | `bg-surface` `text-muted` `border-hairline` `border-line` `rounded-card` `shadow-card` |
| Interactive | `cursor-pointer` `motion-hover` `transition-colors` |
| State | `hover:` `focus-visible:` `disabled:` `data-[state=open]:` `md:` `dark:` |

The order is not aesthetic. It matches the order you *ask questions* when
reading an unfamiliar component: where does this sit, how big is it, what does
it say, what does it look like, what does it do, when does it change.

### 5.2 It is enforced by the formatter, not by people

```jsonc
// .prettierrc
{ "plugins": ["prettier-plugin-tailwindcss"] }
```

**Do not enforce class order with a lint rule.** A lint rule that reorders
class names produces a diff on every file the first time it runs and an
argument in every review thereafter. Prettier sorts on save; the order stops
being a decision anyone makes; the reading order above is simply what the
formatter produces.

Point the plugin at the custom composers so it sorts inside them too:

```jsonc
{
  "plugins": ["prettier-plugin-tailwindcss"],
  "tailwindFunctions": ["cn", "clsx", "cva", "tv"],
  "tailwindStylesheet": "./src/styles/index.css"   // v4: where the theme lives
}
```

`tailwindStylesheet` is what lets the plugin learn the custom scale. Without
it, our role classes sort into the "unknown" bucket at the front and the order
is arbitrary.

### 5.3 When a class list is too long

The number is not the signal. The signal is **whether you can still see the
component's structure.** A 14-class list that is one coherent surface is fine;
a 9-class list interrupted by three `dark:` and two `[&>svg]:` is not.

Three thresholds, in order:

**1. Repeated across elements → an `@utility`.** If four components open with
`rounded-card border border-line bg-surface shadow-card`, that is a surface,
and it deserves a name:

```css
@utility surface-card {
  border-radius: var(--radius-lg);
  border: var(--stroke-default) solid var(--border-default);
  background: var(--bg-surface);
  box-shadow: var(--elevation-card);
}
```

**2. One component, many states → `cva`.** See §6. The list is not long; it is
*conditional*, and the fix is a variant table, not a shorter list.

**3. Genuinely one complex thing → a component class.** A file in
`@layer components` with a real name. This is rarer than people think, and it
is the correct answer for things with pseudo-elements, complex focus handling,
or more than two levels of internal structure.

What is *not* on the list: `@apply`. See §7.3.

---

## 6. Variants with `cva` / `tv`

### 6.1 The `cn()` helper, and the part everyone gets wrong

```ts
// src/lib/cn.ts
import { type ClassValue, clsx } from 'clsx';
import { extendTailwindMerge } from 'tailwind-merge';

/**
 * tailwind-merge resolves conflicts by knowing which classes occupy the same
 * CSS property — and out of the box it knows Tailwind's DEFAULT scale. It has
 * never heard of `p-card`. Untrained, it keeps BOTH:
 *
 *   cn('p-card', 'p-card-lg')  ->  'p-card p-card-lg'
 *
 * Which one wins is then decided by Tailwind's internal stylesheet order, not
 * by the order you passed them — so an override prop works on one component
 * and silently does nothing on another, invisibly, from the JSX.
 */
export const twMerge = extendTailwindMerge({
  extend: {
    // Theme keys mirror the v4 namespaces, so a role registered here is
    // understood by every class group that reads from it.
    theme: {
      spacing: [
        'fused', 'tight', 'related', 'grouped', 'separate', 'distinct',
        'inline-xs', 'inline-sm', 'inline-md',
        'block-xs', 'block-sm', 'block-md',
        'card', 'card-lg', 'well',
        'section', 'subsection', 'block', 'gutter', 'tap',
      ],
      radius: ['flat', 'hairline', 'inner', 'control', 'card', 'panel', 'hero', 'pill'],
      color: [
        'canvas', 'surface', 'raised', 'sunken', 'inverse',
        'hover', 'active', 'selected', 'disabled',
        'default', 'strong', 'muted', 'subtle', 'link',
        'on-accent', 'on-inverse', 'disabled-fg',
        'accent', 'accent-hover', 'success', 'warning', 'danger',
        'accent-fg', 'success-fg', 'warning-fg', 'danger-fg',
        'line-subtle', 'line', 'line-strong', 'line-accent', 'focus',
      ],
      text: [
        'display', 'display-sm', 'h1', 'h2', 'h3', 'h4',
        'lead', 'body', 'prose', 'ui', 'label', 'caps', 'meta', 'code',
      ],
      // Typography roles. Without these, `font-regular` is read as a font
      // FAMILY and `cn('font-body', 'font-regular')` drops the family.
      font: ['body', 'code'],
      'font-weight': ['regular', 'medium', 'semibold', 'bold'],
      leading: ['flat', 'display', 'heading', 'body', 'long'],
      tracking: ['display', 'heading', 'body', 'ui', 'allcaps'],
      shadow: ['flat', 'card', 'raised', 'overlay', 'modal'],
      ease: ['enter', 'exit', 'move', 'bounce', 'steady'],
    },
    classGroups: {
      // Utilities registered with @utility are invisible to tailwind-merge;
      // it has no stylesheet to read. Group them by the property they set, or
      // two of them will happily coexist on one element. Where tailwind-merge
      // already has the group (`z`, `border-w`), extend IT under its own key,
      // so a role and a stock class conflict too: `z-modal z-50` keeps one.
      motion: [{ motion: ['hover', 'enter', 'exit', 'expand', 'emphasis', 'instant', 'page'] }],
      z: [{ z: ['base', 'raised', 'sticky', 'dropdown', 'overlay', 'modal', 'toast', 'tooltip'] }],
      'border-w': [{ border: ['hairline', 'stroke', 'thick'] }],
    },
  },
});

export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));
```

**Verify it, do not assume it.** One test, and it catches the whole class of
bug:

```ts
expect(cn('p-card', 'p-card-lg')).toBe('p-card-lg');
expect(cn('bg-surface', 'bg-raised')).toBe('bg-raised');
expect(cn('z-modal', 'z-toast')).toBe('z-toast');
expect(cn('motion-hover', 'motion-expand')).toBe('motion-expand');
expect(cn('font-body', 'font-regular')).toBe('font-body font-regular');
expect(cn('z-modal', 'z-50')).toBe('z-50');
```

An unconfigured `twMerge` returns *both* classes for the first, third and fourth.
The colour pair merges already, because stock tailwind-merge accepts any colour
name; it is here so a config change that breaks colours is caught too.

### 6.2 A complete component

```tsx
// src/components/Button.tsx
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/cn';

const button = cva(
  // Base: everything true of every button. Canonical order from §5.1.
  [
    'inline-flex items-center justify-center gap-fused',
    'tap-target rounded-card',
    'text-ui font-semibold',
    'transition-colors motion-hover',
    'cursor-pointer select-none',
    'focus-visible:focus-ring',
    'disabled:cursor-not-allowed disabled:bg-disabled disabled:text-disabled-fg',
  ],
  {
    variants: {
      /* WEIGHT in the hierarchy — how loudly this asks to be pressed.
       * Named for the job, not the colour: a `primary` that is grey in one
       * brand and orange in another is still the primary action. */
      variant: {
        primary: 'bg-accent text-on-accent hover:bg-accent-hover',
        secondary: 'bg-surface text-default border border-line hover:bg-hover',
        ghost: 'bg-transparent text-muted hover:bg-hover hover:text-default',
        link: 'bg-transparent text-link underline hover:text-accent-fg',
      },

      /* SIZE. Only padding and type change — radius does not, or the button
       * stops looking like the same object at a different scale. */
      size: {
        sm: 'px-inline-sm py-block-xs text-label',
        md: 'px-inline-md py-block-sm text-ui',
        lg: 'px-inline-md py-block-md text-lead',
      },

      /* TONE — semantic intent, orthogonal to weight. A destructive action
       * can be primary or ghost; those are different questions. */
      tone: {
        neutral: '',
        danger: '',
        success: '',
      },

      full: { true: 'w-full', false: '' },
    },

    /* COMPOUND VARIANTS are where `tone` acquires meaning. Tone alone emits
     * nothing (see the empty strings above) because "danger" means a red FILL
     * on a primary button and red TEXT on a ghost one. Encoding that in the
     * `tone` variant directly would force a `danger` ghost button to carry a
     * red background it must then override — which is the specificity fight
     * this whole system exists to avoid. */
    compoundVariants: [
      {
        variant: 'primary',
        tone: 'danger',
        class: 'bg-danger text-on-accent hover:bg-danger',
      },
      {
        variant: 'secondary',
        tone: 'danger',
        class: 'text-danger-fg border-line-strong hover:bg-hover',
      },
      { variant: 'ghost', tone: 'danger', class: 'text-danger-fg hover:bg-hover' },
      {
        variant: 'primary',
        tone: 'success',
        class: 'bg-success text-on-accent hover:bg-success',
      },
      /* Optical correction, not a new value: an icon-only button at `sm` is
       * square, so the horizontal inset drops a step. */
      { size: 'sm', full: false, class: 'has-[>svg:only-child]:px-inline-xs' },
    ],

    defaultVariants: {
      variant: 'secondary',
      size: 'md',
      tone: 'neutral',
      full: false,
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof button> {}

export function Button({ className, variant, size, tone, full, ...props }: ButtonProps) {
  return (
    <button
      className={cn(button({ variant, size, tone, full }), className)}
      {...props}
    />
  );
}
```

Three things this shape gets right:

- **`defaultVariants` means the unstyled case is a real decision.**
  `<Button>Cancel</Button>` is a secondary button because secondary is what an
  un-emphasised action *should* be, not because nobody chose.
- **`className` is merged last, through `cn`.** That is the documented override
  point, and it only behaves correctly because §6.1 taught `twMerge` the
  custom scale. Without it, a caller's `p-card-lg` is a coin flip.
- **No `style` prop, anywhere.** If a caller needs a runtime value, it crosses
  the boundary as a custom property and the styling stays in CSS. See §7.4.

`tailwind-variants` (`tv`) is the same model with slots for multi-part
components. Use it when a component has named internal parts (a dialog's
overlay / panel / title); use `cva` otherwise. Do not use both in one codebase —
that is two variant systems, which is §9.7.

---

## 7. When NOT to use a utility

### 7.1 The decision rule

Ask in this order and stop at the first yes:

| Question | Answer |
|---|---|
| Is this one element, styled once? | **Utility classes.** |
| Is this the same combination on 3+ elements? | **`@utility`** — name the surface. |
| Is this one element with many conditional states? | **`cva` / `tv`** — a variant table. |
| Does this need pseudo-elements, `:has()` chains, keyframes, or 3+ levels of internal structure? | **A component class** in `@layer components`. |
| Is this a runtime value? | **A custom property via `style`** — see §7.4. |
| Is this genuinely one-off and genuinely justified? | **`@layer overrides`** with a comment naming why. |

### 7.2 `@utility` vs a component class

`@utility` registers into the `utilities` layer, so it sorts with Tailwind's
own and is overridable by another utility. A component class lives in
`components`, *below* utilities, so a utility beats it.

That difference is the whole choice:

- **`surface-card` is a `@utility`** — you want `bg-sunken` to be able to
  override it on one instance.
- **`.dialog` is a component class** — you want `p-card-lg` on the dialog to
  win, and you want the internal structure to live somewhere a utility list
  cannot express.

Registering a "component" as a utility is the more common mistake, and it shows
up as a component whose styles are randomly overridden by unrelated utility
classes elsewhere in the list.

### 7.3 The hard rule on `@apply`

**Do not use `@apply`.** The narrow exception is at the end; it is narrower than
you want it to be.

`@apply` copies a utility's declarations into a rule. The moment it does, three
things Tailwind exists to prevent come back:

**Specificity returns.** A utility is a single class in the `utilities` layer
and beats component CSS by layer order. `@apply`-ed into `.card .title`, those
same declarations now carry that selector's specificity and live in the
`components` layer — so `p-card-lg` on the element no longer overrides them.
This is precisely the "the utility isn't working" ticket, and it is caused by
the thing that was supposed to make utilities more maintainable.

**Order returns.** Tailwind sorts utilities into a known, stable cascade.
`@apply` output is emitted where you wrote it, so which of two conflicting
declarations wins now depends on file import order — which a bundler is free to
change between dev and production.

**The cost returns.** Utilities are shared by every element that uses them.
`@apply` duplicates their bytes into every rule that applies them. You have
thrown away the atomic-CSS bargain and kept the class-soup syntax.

And it buys nothing. These are the same CSS:

```css
.btn { @apply px-inline-md py-block-sm rounded-card; }
.btn {
  padding: var(--pad-block-sm) var(--pad-inline-md);
  border-radius: var(--radius-lg);
}
```

The second reads as CSS, is greppable by property, and is checked by the
Stylelint value allowlist. The first is a layer of indirection over a token
layer that already exists.

**The exception:** a bridge file during a migration, where third-party or legacy
markup you do not control carries class names you must style, and you want those
styles to track the utilities during the changeover. One file, named for what it
is (`legacy-bridge.css`), allowlisted in `stylelint.config.mjs`, deleted when the
migration lands.

### 7.4 The one legitimate inline style

Law 4 says a component's styles have one home. The `style` prop is a second
home, at a specificity no stylesheet can reach, in a place no theme, no media
query, no `[data-density]` and no audit can see. `style={{ padding: 16 }}` is
unreachable by all of those simultaneously.

The single exception is passing a value only the runtime knows into CSS, so that
the *styling* stays in the stylesheet and only the *number* crosses:

```tsx
<div className="progress" style={{ '--progress': pct } as React.CSSProperties} />
```

```css
@layer components {
  .progress::after {
    --progress-size: calc(var(--progress) * 1%);   /* derived: the number as a share */
    inline-size: var(--progress-size);
    background: var(--bg-accent);
    transition: inline-size var(--motion-enter);
  }
}
```

The rule the linter enforces: **every key must start with `--`**, and the value
must be a runtime expression, not a design literal. `style={{ '--gap': '12px' }}`
is Law 1 sneaking in through Law 4's one exception, and it is reported.

---

## 8. Dark mode and density, with zero component changes

The proof that Laws 6 and 7 hold is that the diff is empty.

### 8.1 Dark mode

```html
<script>
  // In <head>, before first paint. A flash of light theme is a bug report.
  const t = localStorage.theme ??
    (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.dataset.theme = t;
</script>
```

```tsx
// The component. Note what is absent.
export function Card({ title, children }) {
  return (
    <article className="p-card rounded-panel bg-surface border border-line shadow-card">
      <h3 className="text-h4 text-strong">{title}</h3>
      <p className="text-body text-muted">{children}</p>
    </article>
  );
}
```

There is no `dark:` class. There is no `useTheme()`. There is no conditional.
tokens.css re-points `--bg-surface` → `--neutral-950`, `--fg-muted` →
`--neutral-400`, `--border-default` → `--neutral-800` and the shadow steps to
their heavier dark-mode values. `theme.css` is `inline`, so every utility reads
those tokens on the element where it lands. The card is correct in both themes
because it never expressed a color — it expressed a role.

Scoped theming works for the same reason, which is the real test:

```tsx
<section data-theme="dark" className="bg-canvas p-card-lg">
  <Card title="Same component" /> {/* dark, unmodified */}
</section>
```

### 8.2 Density

```tsx
<div data-density="compact">
  <Card title="Same component" /> {/* 12.5% tighter, unmodified */}
</div>
```

`[data-density="compact"]` sets `--density: 0.875`. Every Tier-2 spacing role is
`calc(step * var(--density))`, and `--spacing-*` is `inline`, so `p-card`
recomputes on the element. The whole subtree recomposes. No variant, no prop, no
component change.

This is also the clearest demonstration of why §3.3 matters: **drop `inline` and
this stops working while continuing to compile.** The compact table looks
identical to the comfortable one, and the bug is in a config file nobody thinks
to open.

### 8.3 Reduced motion

Also free. tokens.css collapses every duration to 1ms under
`prefers-reduced-motion` and replaces the spring easing with `ease-out` for
vestibular safety. A component using `motion-hover` inherits that; a component
using a literal `duration-200` would have opted out — which is why
`transition-duration` is on the Stylelint allowlist and `duration-*` numerics
are lint-banned. This is an accessibility failure wearing a style-nit costume.

---

## 9. Failure modes in agency work

Each of these has cost a real project real money. Each has a fix and a gate.

### 9.1 Dynamic class construction

```tsx
<div className={`bg-${tone}-500`} />        // generates nothing
<div className={`text-${size}`} />          // generates nothing
```

**Why.** Tailwind does not execute your code. It reads your files with a
scanner. `` `bg-${tone}-500` `` is not a class name in any file, so no CSS is
generated.

**Why it is worse than it looks.** In dev the class often *appears* to work,
because some other file happened to contain `bg-danger` literally. It breaks in
production, after that file was deleted or tree-shaken — weeks after the cause.

**Fix.** Map to whole class names. Always.

```tsx
const TONE = { danger: 'bg-danger', success: 'bg-success', warning: 'bg-warning' } as const;
<div className={TONE[tone]} />
```

**Gate.** `design-laws/no-dynamic-class-construction` reports any template
literal in a class context whose chunk ends mid-class. A chunk ending in
whitespace is allowed — that is a whole class being switched in, which is the
pattern above.

### 9.2 `space-x-*` instead of `gap`

`space-y-related` compiles to `margin-block-start` on `> * + *`: every child
except the first setting its own outer edge. Four concrete failures, not one
aesthetic objection:

1. It breaks the instant the row wraps — the wrapped item keeps its inline
   margin and gains no block spacing.
2. It inverts under `flex-row-reverse` and puts the gap on the wrong side.
3. `order-*` reorders items visually but `:first-child` does not move, so the
   un-spaced item ends up in the middle of the row.
4. It adds a selector and a specificity bump per child, for a job one `gap`
   declaration does with neither.

It is also a direct Law 2 violation: the child is setting its own outer margin.
`gap` is the parent owning the gap.

**Gate.** `corePlugins: { space: false, divideWidth: false }` in v3 removes the
class entirely; in v4 the namespace deletion does it; ESLint catches it in
either case so the error message names the law.

### 9.3 Arbitrary values under deadline

`mt-[13px]` at 6pm on a Thursday is not a knowledge problem. The developer knows
the scale exists; the 13px is what makes the client's screenshot line up, and
nobody is relitigating the spacing scale before the call.

**This is the failure mode this whole document exists for**, and documentation
cannot fix it, because documentation is not present at 6pm on a Thursday. Only
the build and the gate are.

**Gate.** ESLint bans `-[…]` in class strings: in `className`, inside
`cn()`/`clsx()`/`cva()`/`tv()`, and inside any `*Variants` / `*Styles` /
`*Classes` table — the variant map is where these hide. The error names the role
to use instead.

Arbitrary *variants* are explicitly allowed: `data-[state=open]:`,
`aria-[expanded=true]:`, `group-[.is-open]:`, `has-[img]:`,
`supports-[display:grid]:`. Those select a state; they carry no value and
cannot drift off-scale. Banning them would make every Radix integration
unreachable, and a rule that blocks correct code gets switched off wholesale.

### 9.4 `!important` via the `!` modifier

`!bg-accent` (v3) or `bg-accent!` (v4). An `!` means two rules are fighting, and
the fight is a symptom: something is in the wrong layer.

The seven-layer order exists so the answer is always "move it", never "force
it". `overrides` is the last layer precisely so a genuine one-off wins by
position. If `!` seems necessary, one of these is true:

- a component class is being beaten by a utility → it should be a `@utility`;
- a utility is being beaten by a component class → `utilities` is in the wrong
  place in the layer statement (see §2.1);
- third-party CSS is loading unlayered → import it into `@layer reset`, which
  puts it below everything you write.

**Gate.** ESLint on both spellings; Stylelint's `declaration-no-important`.

### 9.5 Inconsistent breakpoints

`md:` in one component, `lg:` in the next, `min-[840px]:` in a third because the
sidebar felt cramped. Now the site has three layout shifts between 768px and
1024px, each one someone's local fix, and the responsive behaviour cannot be
reasoned about as a whole.

**Fix.** Five breakpoints, mirrored from `--bp-*`, and the arbitrary-value ban
covers `min-[…]` and `max-[…]` too. When a component genuinely needs to respond
to *its own* width rather than the viewport's, that is a container query — a
different tool for a different question, not a new breakpoint.

**Also:** mobile-first, always. `md:` adds at 768px and above. A breakpoint that
*subtracts* (`max-md:`) is a layout built in the wrong order, and it reads as
one.

### 9.6 Class lists so long the structure is invisible

```tsx
// example: wrong — the structure is invisible
<div className="relative flex min-h-0 flex-1 flex-col items-stretch justify-between gap-related overflow-hidden rounded-panel border border-line bg-surface p-card shadow-card transition-shadow motion-hover hover:shadow-raised focus-within:ring-2 focus-within:ring-focus dark:border-line-strong md:flex-row md:items-center md:gap-separate lg:p-card-lg">
```

The JSX tree is no longer readable, so nobody reviews the *structure* — which is
where the real bugs are. §5.3 has the three fixes. The signal is not the count;
it is whether you can still see the shape.

### 9.7 Duplicated variant logic

The same `primary / secondary / ghost` ladder written independently in
`Button`, `LinkButton`, `IconButton` and `MenuItem`. They agree for one sprint.
By the third, `ghost` means three different hover treatments.

**Fix.** One `cva` config, exported and shared:

```ts
// src/components/button-variants.ts — one definition, four consumers
export const buttonVariants = cva([...], { variants: { ... } });
```

```tsx
// LinkButton.tsx
import { buttonVariants } from './button-variants';
export const LinkButton = ({ variant, size, className, children, ...props }) => (
  <a className={cn(buttonVariants({ variant, size }), className)} {...props}>{children}</a>
);
```

This is also the reason the ESLint config scopes its class checks to
`*Variants` / `*Styles` / `*Classes` variable declarators: the shared table is
exactly the file where a stray `bg-neutral-700` does the most damage, and it is
usually the file nobody opens in review.

### 9.8 The `style` prop as a pressure valve

One `style={{ marginTop: 4 }}` to fix an alignment, shipped, forgotten. It is
now invisible to dark mode, to `[data-density]`, to print styles, to the token
audit and to every grep anyone will run. It has a specificity no stylesheet can
reach, so the next person's fix is `!important`.

**Gate.** `design-laws/style-prop-custom-properties-only`. Every key must start
with `--`. §7.4 has the legitimate pattern.

### 9.9 The theme file that stopped being the token file

The slowest failure, and the one with no single commit to point at. Someone adds
`--color-brand-blue: #2563eb` to `@theme` because the client sent a hex. Six
months later a third of the theme is literals and the token file is decorative.

**Gate.** Stylelint's `design/color-no-hex` and `design/no-literal-colour-function`
stay ON for `theme.css`, and its custom properties take the spec's bindings
(`design-rules.json`: `bindings`), which the audit checks too (`binding-literal`):
a token, `currentColor`, `transparent` or a CSS-wide keyword. The file has exactly
four literal exceptions — breakpoints, CSS-wide keywords, keyframe geometry, aspect
ratios — each documented in `theme.css` §0, each justified by a property of CSS
rather than a deadline. A hex is never one of them: a breakpoint *must* be a literal
because media queries cannot read custom properties; a color never must be. So
`--color-brand-blue: #2563eb` and `--spacing-card: 28px` both fail the gate.

---

## 10. Enforcement: what runs, and when

| Gate | Runs | Catches |
|---|---|---|
| `theme.css` / `tailwind.config.ts` | every build | Laws 1, 3, 6 — off-scale classes do not exist |
| `prettier-plugin-tailwindcss` | on save | class order (§5.2) |
| `eslint.design.config.mjs` | on save, pre-commit, CI | Laws 1, 2, 3, 4, 5, 6, 8 |
| `stylelint.config.mjs` | on save, pre-commit, CI | Laws 1, 2, 3, 5, 6 in CSS |
| `pre-commit-design-gate.sh` | every commit | all of the above, staged files only |
| `scripts/audit_design.py` | pre-commit, CI | Law 9 — contrast, token coverage, breakpoint drift |

Three properties matter more than the rule list:

**Staged-files-only.** A gate that lints the whole tree fails for reasons the
committer did not cause, on their first commit in a legacy repo. It gets
bypassed once, then always. Linting only what is being committed keeps the gate
about *this* change — the only way it survives a deadline.

**Errors, not warnings.** A design-system warning is a suggestion, and a
suggestion loses. A rule you keep disabling is not too strict; it is a missing
token. Add the token.

**A visible bypass.** `DESIGN_GATE_BYPASS=1` with a `DESIGN_GATE_BYPASS_REASON`
works. It writes the time, user, reason and staged files to `design-gate.log` in
the repository's git directory. With the same script installed as the commit-msg
hook, it also puts a `Design-Gate-Bypass:` trailer in the commit, so the record
travels with the history. Bypasses are sometimes correct; invisible bypasses never
are. Review them weekly: a bypass nobody can explain is a missing token or a
missing escape hatch, and both are fixable.

**A gate that cannot run fails.** A missing stylelint config, audit script or
Python refuses the commit instead of skipping quietly, because a skipped gate
passes everything. `DESIGN_GATE_ALLOW_SKIP=1` makes it a warning while a stage
is being adopted. Configs are found at the repo root first, then in
`assets/configs/`.

---

## 11. Appendix: Tailwind v3

For clients pinned to v3. The full file is
`assets/configs/tailwind.config.ts`; this is what differs.

### 11.1 `theme`, not `theme.extend`

```ts
export default {
  theme: {
    spacing: { /* … */ },   // REPLACES the default
    colors:  { /* … */ },
    extend: {
      keyframes: { /* … */ },  // only for keys holding no design value
    },
  },
} satisfies Config;
```

`extend` merges and leaves `p-4` and `bg-neutral-800` alive beside our roles —
two scales, one codebase. A top-level key *replaces*. This is the v3 spelling of
`--*: initial`, and it is the single most important line in the file.

Keys not listed keep their defaults deliberately: `opacity`, `flex`,
`gridTemplateColumns` hold no design values.

### 11.2 Values are `var()` references

```ts
const t = (token: `--${string}`): string => `var(${token})`;

spacing: {
  card: t('--pad-card'),
  related: t('--gap-related'),
}
```

The `t()` helper is a choke point as much as a shorthand: the audit greps the
config for any string that is not a `t()` call, so a stray literal cannot hide
in 400 lines.

v3 inlines `var()` into the utility by construction, so there is no
`@theme inline` distinction to get wrong. That is the one thing v3 makes easier.

### 11.3 The opacity-modifier limitation — read this

**`bg-surface/50` does not work with `var()` colors.**

v3 implements `/opacity` by substituting an `<alpha-value>` placeholder into the
color, which requires the token to be stored as bare channels (`210 40% 96%`)
rather than a complete color function. Our tokens are complete `oklch()` values
on purpose: channel-splitting a color token makes it unreadable in devtools,
un-inspectable, and impossible to hand to a designer.

So the modifier produces an invalid value and the declaration is dropped,
silently.

**Do not split the tokens to get the modifier back.** The fix is to stop
reaching for opacity. `--bg-hover` and `--bg-active` are already translucent
overlays that compose over any surface — which is exactly why no component needs
a per-variant hover color. If a new translucency is genuinely needed, it is a
new Tier-2 role.

v4 has no such limitation (`color-mix()` makes the modifier work against
complete colors), which is one more argument for moving clients off v3.

### 11.4 Turn off the plugins that break Law 2

```ts
corePlugins: {
  space: false,          // margin on `> * + *` — Law 2 (§9.2)
  divideWidth: false,    // border-width on `> * + *` — same mechanism
  divideColor: false,
  divideStyle: false,
  container: false,      // hardcodes its own max-widths and padding
},
```

Turning the plugin off means the class cannot be typed, which is stronger than
a lint rule and arrives earlier.

### 11.5 Custom utilities

```ts
plugin(({ addUtilities }) => {
  addUtilities({
    '.motion-hover': {
      transitionDuration: t('--dur-fast'),
      transitionTimingFunction: t('--ease-out'),
    },
    '.focus-ring': {
      outline: `${t('--stroke-focus')} solid ${t('--border-focus')}`,  // forced-colors keeps it
      outlineOffset: t('--stroke-focus'),
      boxShadow: `0 0 0 ${t('--stroke-focus')} ${t('--bg-canvas')}`,   // the gap ring
    },
  });
});
```

Use `addUtilities`, not `addComponents`. Components-layer classes lose to any
utility. And draw the ring as an `outline`: a ring drawn with `box-shadow` is
silently replaced by a stray `shadow-card`, and vanishes in forced-colors mode.

### 11.6 Dark mode and layers

```ts
darkMode: ['selector', '[data-theme="dark"]'],   // v3.4.1+
// older v3: ['class', '[data-theme="dark"]'] — same mechanism, legacy name
```

Layers are the real compromise. **v3 does not emit native cascade layers.** Its
`@layer base|components|utilities` are build-time directives, and the output is
plain, unlayered CSS — which beats every native layer. Put the `@tailwind`
directives straight under a native `@layer` statement and v3's preflight
(`button { background-color: transparent }`) and every utility override your
layered CSS, the opposite of Law 5.

Put Tailwind's output into the layers instead: build it as two sheets and import
them with native `layer()` (postcss-import 15+, before tailwindcss in the PostCSS
plugins):

```css
/* tailwind-base.css */      @tailwind base;
/* tailwind-utilities.css */ @tailwind components; @tailwind utilities;

/* index.css */
@layer reset, vendor, tokens, base, layout, components, utilities, overrides;
@import url("./tailwind-base.css") layer(base);
@import url("./tailwind-utilities.css") layer(utilities);
```

Check the built CSS once: preflight's `button { … }` must sit inside `@layer base`.
If the toolchain cannot do that, keep all hand-written CSS unlayered too and order
it by import; Law 5 then holds only by convention. v4 emits native layers itself.

Do not use v3's `@layer components { … }` directive for hand-written CSS. It is not
the native at-rule: it moves the rules into Tailwind's unlayered output, purges any
class the content globs do not see, and hides where a rule really lands.

---

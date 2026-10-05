# Framework Migrations

The mechanics, per source stack. What a literal looks like in each one, what it becomes, and the trap that is specific to that stack.

The strategy is in `migration-strategies.md`; the clustering is in `extraction-and-clustering.md`. This file is the part you read once you know what you are pointing the scripts at.

## Contents

1. [Plain CSS](#1-plain-css)
2. [SCSS and LESS](#2-scss-and-less)
3. [CSS Modules](#3-css-modules)
4. [styled-components and Emotion](#4-styled-components-and-emotion)
5. [Tailwind](#5-tailwind)
6. [Bootstrap, Material and other framework overrides](#6-bootstrap-material-and-other-framework-overrides)
7. [Inline-style-heavy React](#7-inline-style-heavy-react)
8. [Mixed codebases](#8-mixed-codebases)

---

## 1. Plain CSS

The easy case, and the one the codemod handles most completely.

```css
/* example: before */
.card {
  background: #ffffff;
  border: 1px solid #e6e6e6;
  border-radius: 9px;
  padding: 22px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.07);
  transition: box-shadow 180ms ease-out;
}
```
```css
/* after the codemod: 22px is left for a person to decide. example: illustration */
.card {
  background: var(--bg-surface);
  border: var(--stroke-default) solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 22px;                                  /* reported: 20 or 24? */
  box-shadow: var(--elevation-card);
  transition: box-shadow var(--motion-hover);
}
```

Note what the codemod did *not* do. `22px` is equidistant from 20 and 24 with no frequency signal either way, so it is reported rather than guessed. That single untouched line is the difference between a tool you can trust on someone else's codebase and one you cannot.

### The order of operations that matters

1. `tokens.css` first, imported before everything, changing nothing.
2. Values, one kind per commit.
3. **Then** the layer statement and the `@layer` wrapping — never in the same commit as values.

```css
/* src/styles/index.css — the entry stylesheet, in this exact order */
@layer reset, vendor, tokens, base, layout, components, utilities, overrides;

@import "./reset.css"   layer(reset);
@import "./tokens.css"  layer(tokens);
@import "./base.css"    layer(base);
@import "./layout.css"  layer(layout);
@import "./components.css" layer(components);
```

The statement must come before every `@import`, because a layer's position is fixed the first time its name is used. Put it second and the cascade order is decided by import order instead, silently, and you will chase it for an afternoon.

### The trap: `@import` inside a layer that also has bare rules

A stylesheet with rules outside any layer **beats every layered rule regardless of specificity**. One unwrapped file quietly makes its own rules unoverridable, and the symptom — "this one component ignores the theme" — points nowhere near the cause. The audit catches it as `L5 unlayered`; do not baseline that one away.

---

## 2. SCSS and LESS

The real work here is not the values. It is that **a preprocessor variable is not a token**, and the codebase has been treating it as one for years.

| | `$brand: #2f6df6` | `--bg-accent: var(--accent-600)` |
|---|---|---|
| Exists at runtime | No. Compiled away | Yes |
| Re-pointable by a theme | No | Yes |
| Overridable per subtree | No | Yes |
| Readable from JS | No | Yes |
| Visible in DevTools | No | Yes |
| Works in a media/container query context | Only at compile time | Yes |

A SCSS variable is compile-time text substitution with a name attached. That is why dark mode on a SCSS-variable codebase means compiling two stylesheets, and why it is a project instead of an afternoon.

### Variables → custom properties

```scss
// before
$brand: #2f6df6;
$brand-dark: #2558c8;
$ink: #333333;
$line: #e5e5e5;
$radius: 6px;
$gutter: 18px;

.btn { background: $brand; border-radius: $radius; }
.btn:hover { background: $brand-dark; }
```
```scss
// after — the variables are gone, not re-pointed
.btn {
  background: var(--bg-accent);
  border-radius: var(--radius-md);
}
.btn:hover { background: var(--bg-accent-hover); }
```

**Delete the variables; do not re-point them.** `$brand: var(--bg-accent)` looks like progress and is a fourth tier that means nothing: an indirection with no theming power, no runtime identity and one more name to learn. The only reason to keep a `$`-variable after a migration is a value the browser genuinely cannot hold — a breakpoint used inside `@media`, before container queries were an option.

The codemod deliberately leaves `$brand: #2f6df6` alone: rewriting a variable *declaration* changes every call site at once, invisibly, and that is a decision for a human. Every one lands in the reconciliation report with its call sites.

### `darken()` / `lighten()` → ramp steps

This is the highest-value fix in a SCSS migration and it is always the most contentious.

```scss
// before: three colors nobody can name, computed per call site
.btn:hover    { background: darken($brand, 8%); }
.btn:disabled { background: lighten($brand, 32%); }
.btn:active   { background: darken($brand, 14%); }
```
```scss
// after: three steps on one ramp, in one table, checkable for contrast
.btn:hover    { background: var(--bg-accent-hover); }   /* accent-700 */
.btn:disabled { background: var(--bg-disabled); }
.btn:active   { background: var(--accent-800); }
```

Why this is worth arguing for:

- `darken()` operates in **HSL**, whose lightness is not perceptual. `darken($blue, 10%)` and `darken($yellow, 10%)` produce visibly different amounts of darkening, which is why hover states on a multi-brand system never look consistent.
- The result exists only after compilation, so **nobody can check its contrast**. A ramp is one table you audit once.
- The same `darken($brand, 8%)` typed in four files is four values that drift the moment one of them becomes `9%`.

Mapping rule: match the computed color to its nearest ramp step by ΔE. The script cannot do it for you: it sees `darken($brand, 8%)`, not the colour it compiles to, so the reconciliation report lists each call and where it is, and the matching is yours (compile it, then take the nearest step). A `darken(…, 8%)` almost always lands one step down; `darken(…, 15%)` lands two. When it lands between steps, take the step — the ramp is perceptually even and the hand-computed value was not.

### `@mixin` → tokens, or nothing

```scss
// before — a mixin that exists only to hold two numbers
@mixin card-pad { padding: 22px 26px; }
.panel { @include card-pad; }
```
```scss
// after — the numbers have names now, so the mixin has no job
.panel { padding: var(--pad-card) var(--pad-card); }
```

Most spacing and color mixins are pre-token tokens. Delete them. Keep mixins that encode genuine *logic* — a focus-ring recipe, a truncation pattern, a media-query helper — and rewrite their bodies to read tokens.

### LESS

Same shape, different sigil: `@brand: #2f6df6`. One extra hazard — `@` is also the at-rule sigil, so a naive scanner reads `@media` as a variable declaration. Scope the variable pattern to `@name:` at statement position.

---

## 3. CSS Modules

Mechanically identical to plain CSS. Everything different is about *where the file sits*.

A `.module.css` file is a **component file** by definition, which turns on three laws the codemod cannot satisfy for you:

| Law | What it means here |
|---|---|
| L2 | No child `margin-*`. The parent owns the gap |
| L6 | No Tier-1 tokens. `var(--space-6)` in a module is a violation even though the value is right |
| L4 | This file is the component's *one* home. A page file styling `.card__title` is the violation, even though the offending line is elsewhere |

Law 6 is the one that bites during a migration, because the mapping must produce **role** tokens, not primitives:

```css
/* WRONG — right value, wrong tier. Compiles, renders, fails the audit. example: wrong */
.card { padding: var(--space-6); gap: var(--space-3); color: var(--neutral-900); }
```

```css
/* RIGHT */
.card { padding: var(--pad-card); gap: var(--gap-related); color: var(--fg-default); }
```

The difference shows up the day "more air in cards" lands: one is a single role edit, the other is a grep across the repo for `--space-6` followed by deciding, per hit, whether *that* 24px meant "card padding".

### `composes:` is a second home

```css
/* example: before */
.primaryButton { composes: button from './Button.module.css'; background: #2f6df6; }
```

`composes` is CSS Modules' inheritance, and it means this component's appearance is now decided in two files. Migrate the values, then flag it: the Law 4 answer is a `variant` on the base component, or a Tier-3 custom property the base component documents.

```css
/* Button.module.css — the public API, in one place */
.button { background: var(--button-bg, var(--bg-accent)); }
/* consumer */
.primaryButton { composes: button from './Button.module.css'; --button-bg: var(--bg-accent); }
```

### `:global` selectors

`:global(.legacy-thing)` is a reach into code this file does not own. Migrate the values but never consolidate a `:global` rule with a local one — they have different owners and one of them is going to be deleted.

---

## 4. styled-components and Emotion

The values migrate cleanly. The interesting decision is where the values *live* afterwards.

### Theme object → CSS custom properties

Almost every styled-components codebase has this:

```jsx
// example: before
const theme = {
  colors: { brand: '#2f6df6', ink: '#333333', line: '#e5e5e5' },
  space:  { sm: 8, md: 16, lg: 24 },
};

const Card = styled.div`
  background: ${(p) => p.theme.colors.white};
  border: 1px solid ${(p) => p.theme.colors.line};
  padding: ${(p) => p.theme.space.md}px;
`;
```

```jsx
// after — the values live in CSS, the component reads them directly
const Card = styled.div`
  background: var(--bg-surface);
  border: var(--stroke-default) solid var(--border-subtle);
  padding: var(--pad-card);
`;
```

**Why move to custom properties rather than keeping a nicer theme object.** This is the argument you will have to make, so make it precisely:

| | JS theme object | CSS custom properties |
|---|---|---|
| Theme switch | Re-render every styled component through context | One attribute on `<html>`. Zero React work |
| Cost of a theme switch | Every `styled` call re-evaluates; measurable jank on large trees | Style recalculation only |
| SSR | Theme must be serialized and matched, or you get a flash | A CSS file. There is nothing to match |
| Reachable from plain CSS | No | Yes |
| Reachable from a third-party component | No | Yes — it inherits |
| Visible in DevTools | No. You see the computed output | Yes, by name, with its inheritance chain |
| Works in a `@media (prefers-color-scheme)` block | Needs JS to observe the media query | Natively |
| Runtime cost per render | A function call per interpolation | None |

The decisive one is the third-party row. A date picker you did not write cannot read your JS theme, but it inherits `--bg-surface` for free. That is the difference between a theme and a theme *your whole page obeys*.

Keep the theme object only for values React genuinely needs as JavaScript — a breakpoint used in a `useMediaQuery`, a duration passed to an animation library. Read them from CSS where you can:

```js
const dur = getComputedStyle(document.documentElement)
  .getPropertyValue('--dur-base').trim();
```

### Interpolations that are not values

```jsx
// example: before
const Badge = styled.span`
  padding: 2px 7px;
  color: ${(p) => tones[p.tone ?? 'info']};     // a variant, not a value
`;
```

The interpolation is a **variant**, and variants belong in the cascade, not in a function call:

```jsx
const Badge = styled.span`
  padding: var(--pad-block-xs) var(--pad-inline-xs);
  color: var(--badge-fg, var(--fg-accent));
  &[data-tone='warn']  { --badge-fg: var(--fg-warning); }
  &[data-tone='error'] { --badge-fg: var(--fg-danger); }
`;
// <Badge data-tone="error">
```

This is worth doing during the migration rather than after: it removes a render-time branch, it makes the states visible in DevTools, and it is the shape `component-state-matrix` can test.

### The trap: dynamic interpolation defeats extraction

```jsx
const Box = styled.div`
  padding: ${(p) => (p.tight ? '8px' : '16px')};
`;
```

The literals are inside JavaScript, so a CSS-shaped scanner blanks them out with the rest of the interpolation. They are real values and they will survive the migration invisibly. Grep for `styled` blocks containing `?` and `px` and handle them by hand — this is the single most common source of "we migrated and there are still hardcoded values everywhere".

### Emotion's `css` prop

`css={{ padding: 16 }}` is an object, not a template literal, and it behaves like an inline style for extraction purposes. Same treatment as §7.

---

## 5. Tailwind

Tailwind with arbitrary values everywhere is a token system that was switched off. `p-[13px]` is `padding: 13px` with extra syntax, and the reason it exists is that the theme did not have the value someone wanted.

Migrating is two moves, in this order.

### Move 1 — replace the theme, do not extend it

```ts
// WRONG — `extend` merges with Tailwind's stock scale
export default { theme: { extend: { spacing: { card: 'var(--pad-card)' } } } };

// RIGHT — a top-level key REPLACES the default scale
export default {
  theme: {
    spacing: {
      0: 'var(--space-0)', px: 'var(--space-px)',
      fused: 'var(--gap-fused)', tight: 'var(--gap-tight)',
      related: 'var(--gap-related)', grouped: 'var(--gap-grouped)',
      separate: 'var(--gap-separate)', distinct: 'var(--gap-distinct)',
      'inline-xs': 'var(--pad-inline-xs)', 'inline-sm': 'var(--pad-inline-sm)',
      'inline-md': 'var(--pad-inline-md)', 'block-xs': 'var(--pad-block-xs)',
      'block-sm': 'var(--pad-block-sm)', 'block-md': 'var(--pad-block-md)',
      card: 'var(--pad-card)', 'card-lg': 'var(--pad-card-lg)',
      well: 'var(--pad-well)', section: 'var(--space-section)',
      gutter: 'var(--gutter-page)', tap: 'var(--tap-min)',
    },
  },
};
```

`extend` leaves `p-4`, `bg-neutral-800` and `text-sm` alive next to yours — two scales in one codebase and a drift nobody can grep for. A top-level key removes the stock classes, so an off-scale class **does not exist**: Tailwind generates no CSS for it. That is silent, not a build error. The element simply ships unstyled, so the lint rules are what find it (Part 5 of `eslint.design.config.mjs`). The config shape is Law 3; the lint rules enforce it.

The full annotated config is `assets/configs/tailwind.config.ts` (v3) or `assets/configs/theme.css` (v4) in the `web-design-studio` skill. Do not hand-write it.

### Move 2 — sweep the arbitrary values

```jsx
/* example: before */
<section className="px-[18px] py-[62px] bg-[#fafaf9]">
  <h1 className="text-[44px] text-[#333333]">…</h1>
  <div className="mt-[26px] flex gap-[9px]">
    <button className="rounded-[5px] px-[17px] py-[9px] bg-[#2f6df6]">…</button>
```
```jsx
/* after the sweep: 62px has no rung, so it is left for review. example: illustration */
<section className="px-inline-md py-[62px] bg-canvas">
  <h1 className="text-h1 text-default">…</h1>
  <div className="mt-separate flex gap-tight">
    <button className="rounded-sm px-inline-md py-block-sm bg-accent">…</button>
```

The codemod does this sweep, and the key it picks follows the **role, not the pixel count**: `px-[18px]` becomes `px-inline-md`, not `px-grouped`, because inline padding and a sibling gap are different decisions that happen to measure the same. `py-[62px]` is left alone because 64px has no inset role — it is section rhythm and wants `py-section`, which is a human call.

Three Tailwind-specific things the sweep does not fix:

| Left behind | Why | Fix |
|---|---|---|
| `text-white`, `bg-gray-100` — stock classes | Not arbitrary, so not in the census. They stop existing when the theme is replaced, silently: no CSS and no build error, just an unstyled element | Fix during Move 1: the design ESLint config finds them (its Part 5), and a visual diff of each screen confirms |
| `space-x-4` / `space-y-4` | Compiles to child margins with a `:not(:last-child)` selector — the Law 2 double-ownership problem behind a nicer name | `gap-*` on the parent |
| `!p-4` (important modifier) | Inverts layer order, same as `!important` | Fix the layer or the variant |

### The trap: classes assembled at runtime

```jsx
// example: wrong
<div className={`p-[${pad}px]`}>          // generates nothing. Ever.
```

Tailwind scans source text; it cannot see a template it has not evaluated. This class produces no CSS at all, which means it has been silently broken since the day it was written and nobody noticed because something else was providing the padding. During a migration you will find several. They are bugs, not migration work — file them.

---

## 6. Bootstrap, Material and other framework overrides

**Rule: layer them, do not fight them.** A framework has an upstream. Every value you edit in its stylesheet comes back on the next `npm update`, in a merge conflict, in a file nobody owns.

Typical inherited override sheet:

```css
/* example: before — an escalation the framework will always win eventually */
.btn.btn-primary {
  background-color: #2f6df6 !important;
  border-color: #2558c8 !important;
  padding: 9px 17px !important;
}
```

The `!important`s are not laziness. They are the only tool left once you are in a specificity fight with a library that ships `.btn.btn-primary`. Layers end the fight outright:

```css
/* index.css — the framework goes in a layer BELOW yours */
@layer reset, vendor, tokens, base, layout, components, utilities, overrides;

@import "bootstrap/dist/css/bootstrap.css" layer(vendor);
```
```css
/* after — no !important, no specificity match, and it survives an upgrade */
@layer components {
  .btn-primary {
    background-color: var(--bg-accent);
    border-color: var(--bg-accent-hover);
    padding: var(--pad-block-sm) var(--pad-inline-md);
  }
}
```

Layer order beats specificity entirely: a single-class rule in `components` beats a triple-class rule in `vendor`, and it keeps beating it when Bootstrap 5.4 adds another class to the selector.

**Except for `!important`, which inverts layer order.** An important declaration in the *lowest* layer beats important and normal declarations in every layer above it. Bootstrap's utilities (`.d-none`, `.mt-3`, `.bg-primary`, `.text-primary`…) are all `!important`, so from `vendor` they still beat your components. Build Bootstrap without its utilities API if you can. If you cannot, treat those classes as final and do not try to out-rank them. `.bg-primary` and `.text-primary` also read `--bs-primary-rgb`, an `r, g, b` triplet, so binding `--bs-primary` does not reach them, and an OKLCH role cannot be written as a triplet.

### Re-point the framework's own variables where it has them

Bootstrap 5 and MUI both expose theming hooks. Use them — one binding is cheaper to maintain than fifty overrides.

```css
/* Bootstrap 5.3: bind its variables to your roles, once */
@layer vendor {
  :root {
    --bs-primary: var(--bg-accent);
    --bs-body-color: var(--fg-default);
    --bs-body-bg: var(--bg-canvas);
    --bs-border-color: var(--border-default);
    --bs-border-radius: var(--radius-lg);
  }
  /* --bs-primary never reaches the button: .btn-primary sets its own
     --bs-btn-* variables to literals. Bind those too. */
  .btn-primary {
    --bs-btn-bg: var(--bg-accent);
    --bs-btn-border-color: var(--bg-accent);
    --bs-btn-color: var(--fg-on-accent);
    --bs-btn-hover-bg: var(--bg-accent-hover);
    --bs-btn-hover-border-color: var(--bg-accent-hover);
    --bs-btn-hover-color: var(--fg-on-accent);
  }
}
```

```jsx
// MUI: native color lets the palette alias custom properties, and derives
// hover and ripple colours in CSS (color-mix, relative colour) instead of in
// JavaScript, which cannot read a var().
const theme = createTheme({
  cssVariables: { nativeColor: true },
  palette: {
    primary:    { main: 'var(--bg-accent)' },
    background: { default: 'var(--bg-canvas)', paper: 'var(--bg-surface)' },
  },
  shape: { borderRadius: 'var(--radius-lg)' },
});
```

Without `nativeColor`, MUI computes derived colors (hover, ripple) in JavaScript from `main`, and it cannot compute from a `var()`. On an MUI version without native color (see MUI's "Native color" page), supply `light` / `dark` / `contrastText` explicitly from your ramp rather than letting it guess. That is the same problem as `darken()` in §2, for the same reason.

### What to migrate and what to leave

| Region | Action |
|---|---|
| Framework's own stylesheet | **Never touch.** `@layer vendor` |
| Your override sheet | Migrate values, delete `!important`, move to `@layer components` |
| Your components that use framework classes | Migrate normally. They are yours |
| Framework classes in your JSX (`className="btn btn-primary"`) | Leave. Replacing them is a component rewrite, not a migration |

---

## 7. Inline-style-heavy React

The hardest stack, because the values are tokenizable but the *declarations* are in the wrong place, and moving them requires inventing names.

```jsx
/* example: before — five homes for one table */
export function Table({ rows }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <tr style={{ background: '#f5f5f4', color: '#6b6b6b' }}>
        <th style={{ padding: '7px 11px', textAlign: 'left' }}>Name</th>
      </tr>
      <tr style={{ borderTop: '1px solid #e6e6e6' }}>
        <td style={{ padding: '9px 11px', color: '#333333' }}>{r.name}</td>
      </tr>
    </table>
  );
}
```
```jsx
/* after — one home */
import styles from './Table.module.css';

export function Table({ rows }) {
  return (
    <table className={styles.table}>
      <tr className={styles.headRow}>
        <th className={styles.headCell}>Name</th>
      </tr>
      <tr className={styles.row}>
        <td className={styles.cell}>{r.name}</td>
      </tr>
    </table>
  );
}
```
```css
/* Table.module.css */
.table    { width: 100%; border-collapse: collapse; font: var(--type-ui); }
.headRow  { background: var(--bg-sunken); color: var(--fg-muted); }
.headCell { padding: var(--pad-block-sm) var(--pad-inline-sm); text-align: start; }
.row      { border-top: var(--stroke-default) solid var(--border-subtle); }
.cell     { padding: var(--pad-block-sm) var(--pad-inline-sm); color: var(--fg-default); }
```

**This is hand work.** The codemod refuses it, deliberately: producing the "after" requires choosing five class names, and a codemod that invents class names is a codemod nobody reviews. Budget roughly a day per thirty offending components and do them in batches of ten.

The census still earns its keep here — it tells you exactly which components, how many declarations each, and which values, so the work is mechanical even though it is manual.

### The one inline style that stays

```jsx
<li className={styles.card} style={{ '--card-span': span } as React.CSSProperties}>
```
```css
.card { grid-column: span var(--card-span, 1); }
```

Different in kind, not degree: it sets no visual property, it sets a **variable**. The visual decision — that `--card-span` maps to `grid-column` — stays in the stylesheet, stays themeable, stays lintable, and has a default for when the value is absent. The rule the tooling enforces is exact: `style` is permitted if and only if *every* key starts with `--`. A mixed object fails, because the mixed object is how the exception becomes the rule.

### Runtime values that are not numbers

A CMS-supplied brand color or hero image arrives at runtime and cannot live in a stylesheet. Same mechanism, one level up:

```jsx
<section className={styles.hero} style={{ '--hero-bg': `url(${cms.image})` }}>
```
```css
.hero { background-image: var(--hero-bg, none); }
```

### The `sx` / `css` prop

Same problem wearing a nicer name. `sx={{ mt: 2 }}` and `css={{ padding: 16 }}` disperse the decision to the call site exactly as `style` does — with the one improvement that they usually go through a theme, so the *values* are already consolidated even though the *homes* are not. Migrate the theme (§4) first; the prop cleanup is then a Law 4 batch like any other.

---

## 8. Mixed codebases

Every codebase over three years old is mixed: a SCSS layer from 2019, CSS Modules from 2021, a styled-components experiment nobody finished, and Tailwind on whatever shipped last quarter.

Do not unify the styling technology during a token migration. Two migrations at once is how both fail, and it is the change that turns a two-week estimate into a quarter.

**Migrate every layer onto the same tokens, in place.** Custom properties are the one thing all four dialects can read, which is exactly why they are the target: SCSS emits them, CSS Modules use them, styled-components interpolate nothing to use them, and Tailwind's theme points at them. After the migration every layer speaks one vocabulary while keeping its own syntax — and *then* consolidating the technology becomes a mechanical, optional, separately-fundable project.

Order the dialects by value per hour:

| Order | Dialect | Why |
|---|---|---|
| 1 | Plain CSS / SCSS globals | Highest literal density, lowest risk, most reuse |
| 2 | CSS Modules | Mechanical, and turns on Laws 2/4/6 where they matter most |
| 3 | Tailwind arbitrary values | The config replacement does most of the work at once |
| 4 | styled-components | Needs the theme-object decision made first |
| 5 | Inline styles | Hand work, lowest throughput. Last, always |

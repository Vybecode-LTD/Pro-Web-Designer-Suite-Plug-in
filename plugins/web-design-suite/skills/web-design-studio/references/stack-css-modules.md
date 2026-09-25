# Stack: CSS Modules

React + Vite, with CSS Modules (and, where it earns its place, SCSS Modules).

This is `stack-vanilla-css.md` with build-time scoping bolted on. Every law still applies; the components below are deliberately the same button and the same card, so you can read the two files side by side and see exactly what changes — and how little.

---

## Contents

1. [What CSS Modules solve, and what they do not](#1-what-css-modules-solve-and-what-they-do-not)
2. [File colocation](#2-file-colocation)
3. [Naming inside a module](#3-naming-inside-a-module)
4. [`composes` and `:global`](#4-composes-and-global)
5. [How tokens reach a module](#5-how-tokens-reach-a-module)
6. [Layers, and the Vite ordering gotcha](#6-layers-and-the-vite-ordering-gotcha)
7. [Composing classes in React](#7-composing-classes-in-react)
8. [Passing runtime values (Law 4's only exception)](#8-passing-runtime-values-law-4s-only-exception)
9. [SCSS Modules: what still earns its place](#9-scss-modules-what-still-earns-its-place)
10. [Typed CSS Modules](#10-typed-css-modules)
11. [Worked example: button](#11-worked-example-button)
12. [Worked example: card](#12-worked-example-card)
13. [Anti-patterns](#13-anti-patterns)

---

## 1. What CSS Modules solve, and what they do not

A `.module.css` file is compiled so that every class name becomes unique. `.root` in `Card.module.css` ships as `Card_root__a1b2c`, and the import gives you a map:

```ts
import styles from './Card.module.css';   // { root: "Card_root__a1b2c", … }
```

**What that solves, completely:** name collisions. Two people can both write `.title` and nothing happens. You never need BEM, never need a block prefix, never need a naming registry. Dead classes are findable, because a class not referenced from the `.tsx` is provably unused.

**What it does not solve — and this is the part teams get wrong.** Scoping prevents *collisions*. It does nothing about *chaos*.

- **Specificity still escalates.** `.root .title .link` is just as unoverridable when it is hashed.
- **The cascade is still global.** Two hashed single-class rules with equal specificity are still resolved by source order, and in a bundler source order is not what you think it is (§6). You still need layers.
- **Literals are still literals.** `padding: 13px` inside a module is the same Law-1 violation it is anywhere. Scoping makes it *harder* to find, because grep across the codebase no longer maps to one file per component name — it maps to one file per component, which is better, but you still have to run the grep.
- **Law 2 still applies.** A module can put `margin-top` on its root just as easily as a global stylesheet can, and the damage is identical.
- **Tokens are still the only vocabulary.** Scoping is orthogonal to theming.

So: CSS Modules buy you the naming discipline of §10 in the vanilla reference for free. They buy you nothing else. Everything else in this file is the same work.

---

## 2. File colocation

One directory per component. The directory is the unit you move, rename, or delete.

```
src/components/Button/
  Button.tsx              the component
  Button.module.css       its styles — the ONE home (Law 4)
  Button.types.ts         props, variant unions (only if they are shared)
  Button.test.tsx
  index.ts                the public surface
```

```ts
// Button/index.ts
export { Button } from './Button';
export type { ButtonProps } from './Button';
```

Two rules about the barrel. It re-exports **one component's** surface, and nothing else — a `src/components/index.ts` that re-exports forty components defeats code-splitting in most bundler configurations and turns one import into forty module evaluations. And it exports **types separately with `export type`**, so the type import is erased and never contributes a runtime edge to the graph.

Colocation is not cosmetic. It is what makes "delete this component" a one-line operation and what makes "one home for a component's styles" checkable by a reviewer who can see both files in one glance.

---

## 3. Naming inside a module

**The class names inside a module should be short and structural, not prefixed.**

```css
/* Card.module.css */
.root    { … }
.media   { … }
.body    { … }
.title   { … }
.footer  { … }
```

Not `.card`, `.cardTitle`, `.card__title`. The filename already supplies the block; the compiler already supplies uniqueness. `Card_title__a1b2` is what ships, and it is more readable in DevTools than `Card_cardTitle__a1b2`.

`.root` for the component's own element is a convention worth adopting universally — it makes `styles.root` mean the same thing in every file in the codebase.

**camelCase, enforced by config.** `styles.cardTitle` is property access; `styles['card-title']` is bracket access and a different keystroke pattern, so codebases drift between the two. Pick one at the config level:

```ts
// vite.config.ts
export default defineConfig({
  css: {
    modules: {
      localsConvention: 'camelCaseOnly',   // `.media-object` → styles.mediaObject
      generateScopedName: process.env.NODE_ENV === 'production'
        ? '[hash:base64:6]'
        : '[name]_[local]__[hash:base64:4]',   // readable in DevTools
    },
  },
});
```

`camelCaseOnly` (not `camelCase`) removes the kebab-case key from the map, so the two spellings cannot both work and nobody has to decide.

---

## 4. `composes` and `:global`

### `composes`

```css
.root    { … }
.primary { composes: root; --btn-bg: var(--bg-accent); }
```

`composes` does not copy declarations. It makes `styles.primary` return **two** class names — `"Button_root__x Button_primary__y"`. It also works across files:

```css
.primary { composes: root from './Button.module.css'; }
```

**The gotcha that bites everyone once:** the order of class names in the `class` attribute has no effect on the cascade. `composes` gives you *composition*, not *precedence*. If `.root` and `.primary` both set `background-color`, the winner is decided by the two rules' source order in the emitted bundle — which, across files, is decided by the bundler (§6). Never rely on `composes` to override.

Constraints: `composes` must appear before any declaration in the rule, and only on a simple single-class selector.

Used well, it is for genuine *sharing* — a `.visuallyHidden` from a shared module, a `.focusRing` — not for variants. Variants re-point custom properties; that is the pattern from the vanilla reference and it has no ordering problem at all.

### `:global`

The escape hatch. It emits the class name unhashed.

```css
/* Legitimate: styling DOM you do not own. */
.root :global(.flatpickr-day.selected) { background-color: var(--bg-accent); }

/* Legitimate: a portal target rendered outside this tree. */
:global(#toast-root) .toast { … }

/* Legitimate: an animation a third-party library triggers by name. */
:global {
  @keyframes shimmer { … }
}
```

Three situations make it legitimate: **third-party DOM** whose class names you cannot change, **portals** where the element is not a descendant of this component, and **library-referenced names** (animation names a vendor script sets in JS).

Everything else is a leak. In particular, `:global(.is-active)` for state is never right — use a `data-*` or ARIA attribute, which needs no escape hatch because attribute selectors are not scoped in the first place.

Note the asymmetry that makes attributes so useful here: **CSS Modules hash class names only.** Element selectors, attribute selectors, pseudo-classes and custom properties pass through untouched. `.root:where([data-variant="primary"])` is fully scoped by `.root` and needs no `:global`.

---

## 5. How tokens reach a module

**Never `@import` the token file into a module. Not once.**

```css
/* Button.module.css — WRONG */
@import '../../styles/tokens.css';
```

What that does: the bundler inlines the entire token file into this module's emitted CSS. Do it in forty components and the bundle contains forty copies of every ramp, forty `:root { … }` blocks and forty copies of the dark-theme override. It is not only bytes — the duplicated `@layer tokens` blocks and duplicated `[data-theme="dark"]` rules make the last copy win, so *which* copy defines your palette now depends on bundle order. Theme switching starts failing in ways that reproduce only in production builds.

**Tokens are global custom properties. They reach a module by inheritance, at runtime, with no import at all.**

```css
/* Button.module.css — RIGHT. No import line. */
@layer components {
  .root { padding-inline: var(--pad-inline-md); }
}
```

`var(--pad-inline-md)` resolves against whatever `:root` declared, because custom properties are inherited DOM values, not build-time substitutions. That is the whole mechanism, and it is why this architecture works identically in both stacks.

### The global entry

```ts
// src/main.tsx
import './styles/index.css';              // ← FIRST import in the file
import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';

createRoot(document.getElementById('root')!).render(<App />);
```

```css
/* src/styles/index.css */
@layer reset, tokens, base, layout, components, utilities, overrides;

@import url('./reset.css');
@import url('./tokens.css');
@import url('./base.css');
@import url('./layout.css');
@import url('./utilities.css');
@import url('./overrides.css');
```

Note what is **not** here: component CSS. Modules are imported by their components and the bundler collects them. That is the source of the ordering problem in §6.

### The one thing you may import into every module

SCSS files that **emit no CSS** — a file containing only `@mixin`, `@function` and Sass variables. `@use 'mq' as *;` costs zero bytes per module because there is nothing to duplicate. The test is literal: if compiling the file alone produces an empty output, it is safe to `@use` everywhere. If it produces a single declaration, it is not.

---

## 6. Layers, and the Vite ordering gotcha

Every module file wraps its contents in the components layer:

```css
/* Button.module.css */
@layer components {
  .root { … }
}
```

This is not optional decoration. Without it, module CSS is **unlayered**, and unlayered author styles beat every layer — including `utilities` and `overrides`. A `.u-visually-hidden` utility will stop working against a component and nobody will be able to explain why.

### The gotcha

**Module CSS injection order is not source order.** It is module *evaluation* order in the dependency graph, and it differs between dev and production:

- In dev, Vite injects each module's CSS as a `<style>` tag when its JS module is first evaluated. A lazily-imported route's CSS therefore arrives *after* everything already on screen.
- In production, Rollup emits one CSS file per chunk, and chunk `<link>` order follows the import graph plus code-splitting decisions.

So the first time the browser ever sees the name `components` may be inside `Button.module.css`, arriving before `index.css` has been parsed. **A layer's position is fixed the first time its name is seen.** If `components` gets created first, it sorts *before* `reset`, and your entire cascade is upside down — intermittently, in one build mode, on one route.

### The fix

Declare the layer order in a place that is guaranteed to be parsed before any JavaScript executes: inline in the HTML head.

```html
<!-- index.html -->
<head>
  <style>@layer reset, tokens, base, layout, components, utilities, overrides;</style>
  <script type="module" src="/src/main.tsx"></script>
</head>
```

Four lines, no build configuration, correct in dev and in production, and correct even if a chunk arrives out of order. Keep the identical statement at the top of `index.css` too — it is idempotent (re-stating an existing order is a no-op) and it keeps the stylesheet readable on its own.

**Do not** reach for `build.cssCodeSplit: false` to solve this. It makes every route load every route's CSS, which is a real performance regression traded for a problem four lines already fixed.

---

## 7. Composing classes in React

### `cn()`

```ts
// src/lib/cn.ts
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ');
}
```

Three lines and no dependency. `clsx` is the same thing with object syntax; take it if you want `{ [styles.active]: isActive }`. Do **not** take `tailwind-merge` — there are no conflicting utility classes here to merge.

The only rule about `cn()` usage: **`className` from props goes last**, so a consumer can always add a class.

```tsx
<button className={cn(styles.root, isLoading && styles.loading, className)} />
```

### Prefer `data-*` attributes to a class per variant

```tsx
// Good — one class, variants as data. Identical CSS to the vanilla stack.
<button className={styles.root} data-variant={variant} data-size={size} />
```

```css
.root:where([data-variant='primary']) { --btn-bg: var(--bg-accent); }
```

This is the default, and it is better than the lookup pattern for four reasons: the DOM is readable in DevTools (`data-variant="primary"` versus `Button_primary__k3f`), the CSS is byte-identical to the vanilla implementation, variants cannot accumulate specificity, and there is no map lookup to get wrong.

### `styles[variant]`, and its typing

Use the lookup only when a variant needs a genuinely different *set* of declarations rather than different values.

```tsx
const variantClass = styles[variant];   // variant: 'primary' | 'ghost' | 'danger'
```

This is where untyped modules hurt. `styles` defaults to `Record<string, string>` (or `any`), so `styles.primry` type-checks, returns `undefined`, and React renders `class="Button_root__x undefined"`. The element is unstyled, **nothing throws, nothing warns**, and it usually only shows up in the one variant nobody screenshotted.

Two settings turn that into a compile error. Generate `.d.ts` files (§10), and:

```json
// tsconfig.json
{ "compilerOptions": { "noUncheckedIndexedAccess": true } }
```

With both, `styles[variant]` is `string | undefined` and TypeScript forces you to handle the miss.

### Keep variant logic out of JSX

JSX should say *what the component is*, never *how it is styled*. Resolve everything above the return, in a plain object defined outside the component so it is not rebuilt per render.

```tsx
const TONE: Record<Variant, 'default' | 'inverse'> = {
  primary: 'inverse',
  ghost: 'default',
  danger: 'inverse',
};
```

The moment you see a ternary inside an attribute, extract it. Two ternaries in one `className` is the point at which nobody can read the markup any more.

---

## 8. Passing runtime values (Law 4's only exception)

A number known only at runtime — a column span, a progress percentage, a measured height — cannot live in a stylesheet. It is passed **in as a custom property**, and the stylesheet does all the styling with it.

```tsx
<article
  className={styles.root}
  style={{ '--card-span': span } as React.CSSProperties}
/>
```

```css
.root { grid-column: span var(--card-span, 1); }
```

**Why the cast.** `React.CSSProperties` is a closed interface of known CSS properties with no index signature, so an object literal containing `'--card-span'` fails with *"Object literal may only specify known properties"*.

**The better fix than casting everywhere** — declare it once, globally:

```ts
// src/types/css.d.ts
import 'react';
declare module 'react' {
  interface CSSProperties {
    [key: `--${string}`]: string | number | undefined;
  }
}
```

The template-literal key restricts the escape to custom properties only, so `style={{ colr: 'red' }}` is still an error. Now the cast disappears from every call site.

**The unit gotcha.** React appends `px` to numeric values for known properties, but **not** for custom properties — those are stringified verbatim. `{'--card-w': 200}` yields `--card-w: 200`, which is invalid as a length and silently does nothing. Pass units explicitly: `{'--card-w': '200px'}`. Unitless is correct for spans, counts, ratios and `--density`.

**This is the only legitimate inline style.** Not "the main one" — the only one. Anything else in a `style` prop is a second home for the component's styles and breaks Law 4: it cannot be themed, cannot respond to `--density`, cannot be overridden by a later layer, has no `:hover`, and does not appear when you grep the stylesheet. If a value is not a runtime number, it belongs in the module.

---

## 9. SCSS Modules: what still earns its place

`Button.module.scss` compiles through Sass first, then CSS Modules. In 2026 the honest list of what Sass still buys you is short.

**1. Media and container query conditions.** Custom properties do not work in media query conditions — `@media (min-width: var(--bp-md))` is invalid and silently never matches. This is a genuine gap in CSS with no native answer, and a mixin is the cleanest fill.

**2. Mechanical generation.** An `@each` over a fixed list, where writing the variants by hand would be twenty near-identical blocks. Use it for things that are *actually* mechanical — a six-step status palette, a grid-column set — never to generate a design decision.

**3. `@use` namespacing for compile-time constants.** Breakpoint values must exist as Sass values because of point 1.

That is the list.

### The four mixins worth having

```scss
// src/styles/_mq.scss  — emits no CSS; safe to @use in every module.
@use 'sass:map';

/* Duplicates --bp-* from tokens.css by necessity (see point 1 above). This
   duplication is a standing audit item: if a breakpoint changes, both files
   change in the same commit. */
$bp: (sm: 30rem, md: 48rem, lg: 64rem, xl: 80rem, xxl: 96rem);

@mixin mq($name) {
  @media (min-width: map.get($bp, $name)) { @content; }
}

/* Container queries are the default choice for components; mq() is for the
   page shell. A component that reacts to the viewport is a component that
   cannot be reused in a sidebar. */
@mixin cq($name, $min) {
  @container #{$name} (inline-size >= #{$min}) { @content; }
}

@mixin motion-safe {
  @media (prefers-reduced-motion: no-preference) { @content; }
}

/* Focus rings differ inside clipping containers (see reset.css §7). One
   mixin so the exception is written once, not remembered forty times. */
@mixin focus-ring($clipped: false) {
  &:where(:focus-visible) {
    @if $clipped {
      outline: var(--stroke-focus) solid var(--border-focus);
      outline-offset: calc(var(--stroke-focus) * -2);
      box-shadow: none;
    } @else {
      /* The reset's ring: an outline no component box-shadow can remove. */
      outline: var(--stroke-focus) solid var(--border-focus);
      outline-offset: var(--stroke-focus);
      box-shadow: 0 0 0 var(--stroke-focus) var(--bg-canvas);
    }
  }
}
```

### What SCSS must never be used for

**Nesting depth.** Sass makes depth 5 effortless, which is exactly the problem. The depth-2 limit (Law 5) is unchanged, and it is *more* important here because the generated selector is invisible in the source. Set `max-nesting-depth: 2` in stylelint and let the linter hold the line.

**Colour functions.** `darken($accent, 10%)`, `rgba($brand, 0.5)`, `mix()`. These resolve at **build time** to a fixed value. That value cannot respond to the theme, cannot respond to `[data-theme="dark"]`, and is invisible to the token layer — you have re-created a hex literal with extra steps (Law 1). Colour is decided in `tokens.css`. If you genuinely need a derived colour at runtime, use `color-mix(in oklch, var(--bg-accent) 80%, var(--bg-canvas))`, which composes against whatever the theme currently is.

**`@extend`.** Never. It rewrites selector lists across the whole compilation, so a rule in file A silently changes the selector of a rule in file B; the emitted selectors appear in no source file; and it moves declarations to the position of the *extended* rule, which breaks every assumption about source order. Use a mixin (duplicated output, honest behaviour) or `composes` (multiple class names, honest behaviour).

**Sass variables for values that should be custom properties.** `$card-padding: 24px` cannot be themed, cannot respond to `--density`, and cannot be inspected in DevTools. The only legitimate Sass variables are the ones that must exist at compile time: breakpoints, and loop inputs.

---

## 10. Typed CSS Modules

Without generated types, `import styles from './Button.module.css'` is typed by an ambient declaration that is effectively `Record<string, string>`. Every class access is unchecked.

Pick one generator:

| Tool | Fits | Notes |
|---|---|---|
| `typescript-plugin-css-modules` | any | **Editor only.** Autocomplete and go-to-definition; does *not* fail `tsc`. Useful, not sufficient. |
| `vite-plugin-sass-dts` | Vite + SCSS Modules | Writes `.module.scss.d.ts` on save and on build. |
| `typed-css-modules` / `tcm` | any, watch mode | Framework-agnostic CLI; commit the `.d.ts` or generate in CI. |

Whichever you pick, run it in **CI as a check, not only in watch mode** — otherwise the `.d.ts` files drift from the CSS and you get confident-looking types that are wrong, which is worse than none.

### The bug class this catches

A class is renamed in the CSS — `.label` becomes `.title` — and one of the six usages is missed.

Untyped: `styles.label` is `string`, resolves to `undefined` at runtime, React renders `class="undefined"`. The element loses its styling. **Nothing throws. Nothing logs. The build is green.** It ships, and it is found by a user, in the variant that only renders on an error state.

Typed: `Property 'label' does not exist on type …`. Compile error, at the exact line, before the commit.

The same mechanism catches dead classes in the other direction — combined with a `no-unused-css-modules` lint rule, a class defined in the module and referenced nowhere is reported, so deleted features do not leave CSS behind.

```ts
// Button.module.css.d.ts  (generated — do not edit)
declare const styles: {
  readonly root: string;
  readonly icon: string;
  readonly loading: string;
};
export default styles;
```

`readonly` is not cosmetic: it stops anyone mutating the map at runtime, which people do try.

---

## 11. Worked example: button

```css
/* Button/Button.module.css */
@layer components {

  .root {
    /* Tier 3 — declared here, defaulted from Tier 2. Identical to the
       vanilla implementation; only the selector name changed. */
    --btn-pad-inline: var(--pad-inline-md);
    --btn-pad-block:  var(--pad-block-md);
    --btn-gap:        var(--gap-fused);
    --btn-radius:     var(--radius-lg);
    --btn-bg:         var(--bg-surface);
    --btn-fg:         var(--fg-default);
    --btn-border:     var(--border-default);
    --btn-shadow:     var(--elevation-flat);
    --btn-min-size:   var(--tap-min);

    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--btn-gap);

    min-block-size: var(--btn-min-size);
    padding-inline: var(--btn-pad-inline);
    padding-block: var(--btn-pad-block);
    border: var(--stroke-default) solid var(--btn-border);
    border-radius: var(--btn-radius);

    background-color: var(--btn-bg);
    color: var(--btn-fg);
    box-shadow: var(--btn-shadow);

    font: var(--type-ui);
    letter-spacing: var(--tracking-wide);
    text-decoration: none;
    white-space: nowrap;

    transition: background-color var(--motion-hover),
                border-color     var(--motion-hover),
                box-shadow       var(--motion-hover);

    /* One hover rule for every variant: --bg-hover is a translucent ink
       painted over whatever --btn-bg currently is. */
    &:where(:hover) {
      background-image: linear-gradient(var(--bg-hover), var(--bg-hover));
    }

    &:where(:active) {
      background-image: linear-gradient(var(--bg-active), var(--bg-active));
    }

    &:where(:disabled, [aria-disabled='true']) {
      --btn-bg:     var(--bg-disabled);
      --btn-fg:     var(--fg-disabled);
      --btn-border: transparent;
      --btn-shadow: var(--elevation-flat);
      background-image: none;
      cursor: default;
    }

    /* Attribute selectors are NOT hashed, so variants need no extra class
       and no :global. Specificity stays (0,1,0) — same as .root. */
    &:where([data-variant='primary']) {
      --btn-bg:     var(--bg-accent);
      --btn-fg:     var(--fg-on-accent);
      --btn-border: transparent;
      --btn-shadow: var(--elevation-card);
    }

    &:where([data-variant='ghost']) {
      --btn-bg:     transparent;
      --btn-fg:     var(--fg-accent);
      --btn-border: transparent;
    }

    &:where([data-variant='danger']) {
      --btn-bg:     var(--bg-danger);
      --btn-fg:     var(--fg-on-accent);
      --btn-border: transparent;
    }

    &:where([data-size='sm']) {
      --btn-pad-inline: var(--pad-inline-sm);
      --btn-pad-block:  var(--pad-block-sm);
      --btn-radius:     var(--radius-md);
      font: var(--type-label);
    }
  }

  /* em-relative so the icon tracks the button's type at every size. */
  .icon {
    inline-size: 1em;
    block-size: 1em;
    flex: none;
  }

  /* 44px is the size of a fingertip, not a style preference. Relax it only
     where the pointer is precise. */
  @media (pointer: fine) {
    .root:where([data-size='sm']) { --btn-min-size: auto; }
  }
}
```

```tsx
// Button/Button.tsx
import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '../../lib/cn';
import styles from './Button.module.css';

type Variant = 'default' | 'primary' | 'ghost' | 'danger';
type Size = 'sm' | 'md';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  icon?: ReactNode;
}

export function Button({
  variant = 'default',
  size = 'md',
  icon,
  children,
  className,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      // data-* carries the variant axes; one class, no lookup, no ternary.
      data-variant={variant}
      data-size={size}
      // `className` last so a consumer can always add to it.
      className={cn(styles.root, className)}
      disabled={disabled}
      {...rest}
    >
      {icon ? <span className={styles.icon} aria-hidden="true">{icon}</span> : null}
      {children}
    </button>
  );
}
```

Note what the `.tsx` does *not* contain: no conditional class names, no style object, no knowledge of colours, sizes or spacing. It maps props to attributes. All styling reasoning is in one file.

---

## 12. Worked example: card

```css
/* Card/Card.module.css */
@layer components {

  .root {
    --card-pad:    var(--pad-card);
    --card-gap:    var(--gap-related);
    --card-radius: var(--radius-xl);
    --card-bg:     var(--bg-surface);
    --card-border: var(--border-subtle);
    --card-shadow: var(--elevation-card);

    position: relative;
    display: flex;
    flex-direction: column;

    background-color: var(--card-bg);
    border: var(--stroke-hairline) solid var(--card-border);
    border-radius: var(--card-radius);
    box-shadow: var(--card-shadow);
    overflow: hidden;                 /* clips media to the radius */

    /* Runtime value, passed in from React as a custom property. */
    grid-column: span var(--card-span, 1);

    transition: box-shadow var(--motion-hover),
                border-color var(--motion-hover);

    &:where(:hover) {
      --card-shadow: var(--elevation-raised);
      --card-border: var(--border-strong);
    }

    &:where(:focus-within) { --card-border: var(--border-focus); }

    &:where([data-variant='flat']) {
      --card-shadow: var(--elevation-flat);
      --card-bg:     var(--bg-sunken);
      --card-border: transparent;
    }

    &:where([data-size='compact']) {
      --card-pad: var(--pad-well);
      --card-gap: var(--gap-tight);
    }
  }

  /* The inset lives on .body, not on .root. The alternative — padding on the
     root plus a negative margin here to bleed out — is a child escaping its
     parent's box (Law 2) and it breaks under --density. */
  .media {
    aspect-ratio: 16 / 9;
    inline-size: 100%;
    object-fit: cover;
    background-color: var(--bg-sunken);
  }

  .body {
    display: flex;
    flex-direction: column;
    gap: var(--card-gap);             /* the parent owns the gaps */
    padding: var(--card-pad);
    flex: 1;
  }

  .meta {
    font: var(--type-label);
    letter-spacing: var(--tracking-wide);
    color: var(--fg-muted);
    text-transform: uppercase;
  }

  .title {
    font: var(--type-h4);
    color: var(--fg-strong);
    text-wrap: balance;
  }

  .text {
    color: var(--fg-muted);
    max-inline-size: var(--measure-narrow);
  }

  /* `auto` is a flex distribution instruction, not a gap — the one outer
     margin a child may set. It pins actions to the bottom so a row of
     unequal cards lines its buttons up. */
  .footer {
    margin-block-start: auto;
    display: flex;
    align-items: center;
    gap: var(--gap-tight);
  }

  .link {
    color: inherit;
    text-decoration: none;

    /* Whole-card hit area; the a11y tree still sees one link named by the
       title. Usability cost (Law 8): text selection inside the card breaks,
       and a second link in the body becomes unreachable. Only use it when
       the card has exactly one action. */
    &::after {
      content: '';
      position: absolute;
      inset: 0;
      z-index: var(--z-raised);
    }

    /* .root clips overflow, which would cut a box-shadow ring in half.
       Outline is never clipped. */
    &:where(:focus-visible) {
      box-shadow: none;
      outline: var(--stroke-focus) solid var(--border-focus);
      outline-offset: calc(var(--stroke-focus) * -2);
    }
  }
}
```

```tsx
// Card/Card.tsx
import type { ReactNode } from 'react';
import { cn } from '../../lib/cn';
import styles from './Card.module.css';

export interface CardProps {
  title: string;
  href: string;
  meta?: string;
  image?: { src: string; alt: string };
  /** Grid columns to span. Runtime number → custom property. */
  span?: number;
  variant?: 'default' | 'flat';
  size?: 'default' | 'compact';
  footer?: ReactNode;
  children?: ReactNode;
  className?: string;
}

export function Card({
  title, href, meta, image, span,
  variant = 'default', size = 'default',
  footer, children, className,
}: CardProps) {
  return (
    <article
      className={cn(styles.root, className)}
      data-variant={variant}
      data-size={size}
      // The ONLY legitimate inline style: a runtime number passed in as a
      // custom property. Unitless — React does not append px to --*.
      style={span ? { '--card-span': span } : undefined}
    >
      {image && <img className={styles.media} src={image.src} alt={image.alt} />}

      <div className={styles.body}>
        {meta && <p className={styles.meta}>{meta}</p>}
        <h3 className={styles.title}>
          <a className={styles.link} href={href}>{title}</a>
        </h3>
        {children && <div className={styles.text}>{children}</div>}
        {footer && <div className={styles.footer}>{footer}</div>}
      </div>
    </article>
  );
}
```

Compare against the vanilla card: the declarations are identical, the token usage is identical, the Law-2 structure is identical. The only differences are `.root` instead of `.card` and `.title` instead of `.card__title`. That is the correct amount of difference between two stacks in one design system.

---

## 13. Anti-patterns

**`@import`-ing tokens into a module.** N copies of the palette in the bundle and theme behaviour that depends on bundle order (§5). *Fix:* no import; custom properties inherit.

**Unlayered module CSS.** Beats `utilities` and `overrides` silently, because unlayered author styles outrank every layer. *Fix:* wrap every module in `@layer components`.

**Relying on the layer statement in `index.css` alone.** Module CSS can create the `components` layer before `index.css` is parsed, inverting the cascade in one build mode only. *Fix:* the inline `<style>` in `index.html` (§6).

**Using `composes` for override semantics.** Class-attribute order does not affect the cascade. *Fix:* re-point custom properties; `composes` is for sharing only.

**`:global` for application state.** `:global(.is-open)` leaks a name into the global namespace and drifts from the ARIA attribute that screen readers use. *Fix:* `[aria-expanded="true"]`, `[data-state="open"]`.

**Inline styles beyond a runtime custom property.** Unthemable, unoverridable, no `:hover`, invisible to grep, and a second home for the component's styles. *Fix:* the module.

**`styles[variant]` without generated types and `noUncheckedIndexedAccess`.** A typo ships `class="undefined"` with a green build. *Fix:* §10, or prefer `data-variant` and avoid the lookup.

**Sass colour functions.** `darken()` bakes a value at build time that no theme can reach. *Fix:* a token, or `color-mix(in oklch, …)` at runtime.

**`@extend`.** Action at a distance across files; emits selectors that appear in no source. *Fix:* a mixin, or `composes`.

**Deep nesting because Sass makes it easy.** Depth 5 reads as depth 1 in the source and ships as a four-compound selector. *Fix:* `max-nesting-depth: 2`, enforced.

**A mega-barrel at `components/index.ts`.** One import pulls in every component's module evaluation and CSS, defeating code splitting. *Fix:* per-component `index.ts` only.

**Reaching into another component's module.** `import cardStyles from '../Card/Card.module.css'` inside `List.tsx` couples two components through a hashed name that is not part of either's API. *Fix:* the parent passes `className`; the child appends it last.

**`margin-top` on `.root`.** Scoping does not repeal Law 2 — the component still injects a gap into every parent that adopts it. *Fix:* the parent's `gap`.

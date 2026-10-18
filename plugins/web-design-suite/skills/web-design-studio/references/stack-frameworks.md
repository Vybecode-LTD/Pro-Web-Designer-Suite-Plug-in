# Stack: Next.js App Router, Vue, Svelte and Astro

The system does not change with the framework: one `tokens.css`, one layer order stated once, the closed scales, the role tokens, the gates. What each framework changes is how a stylesheet reaches the page, and how a component's own styles are scoped. This reference covers the four things that differ: where the tokens load, where the layer order is stated, how scoped styles meet that order, and which files the gates read.

Read it beside the styling reference the project uses: `stack-css-modules.md` for CSS Modules (Next.js's default), `stack-vanilla-css.md` for the starter's plain stylesheets, which every one of these frameworks can load, and `stack-tailwind.md` for Tailwind. The framework facts below were re-read at their sources on 2026-10-18 and are quoted with the URL. The compiled output in §1 was produced on the same day with `@vue/compiler-sfc` 3.5.44, `svelte` 5.57.2 and `@astrojs/compiler` 4.0.0, from the components in `tests/fixtures/stacks`.

## Contents

1. What every stack shares
2. Next.js App Router
3. Vue
4. Svelte and SvelteKit
5. Astro
6. The fixtures

---

## 1. What every stack shares

### The entry is the starter's `index.css`

Copy the starter's `styles/` folder into the project (`app/styles/` in Next.js, `src/styles/` in the others) and load `index.css` once, from the one file every page goes through: the root layout, or the app's entry module. `index.css` opens with the layer statement, then imports the token, base and layout files (`stack-vanilla-css.md` §4). Name the token file in `.design-suite.json`'s `tokens`, so every gate reads the same one (`project-contract.md` §1).

### A layer's place is fixed the first time its name is seen

Every one of these frameworks can put a component's styles in the page before the global entry: Vite injects each component's styles as its module is evaluated, and a bundler orders chunks by the import graph (`stack-css-modules.md` §6). If a component's `@layer components { … }` is the first the browser reads, `components` becomes the first layer, below `reset`, and the cascade is upside down. So, in every stack:

- the layer statement is the first thing in `index.css`;
- `index.css` is imported before any component, wherever the framework orders styles by import (Next.js, Astro);
- where the framework owns an HTML shell that loads scripts (a Vite `index.html`, SvelteKit's `app.html`), the same statement is also inlined in its `<head>`, before any script or stylesheet:

```html
<style>@layer reset, vendor, tokens, base, layout, components, utilities, overrides;</style>
```

Restating the order is harmless: a layer statement that names layers already declared changes nothing.

### Every component style block opens a layer

A scoped style is still an author style. Without a layer it is unlayered, and unlayered styles beat every layer, `utilities` and `overrides` included. Every `<style>` block in a `.vue`, `.svelte` or `.astro` component, and every CSS Module, wraps its rules in `@layer components { … }`, as the fixtures do.

Each compiler keeps its scoping inside the layer. From the fixtures' button:

| Stack | The compiled selector | Specificity added |
|---|---|---|
| Vue `<style scoped>` | `@layer components { .btn[data-v-abc123] { … } }` | 0,1,0 (an attribute) |
| Svelte | `@layer components { .btn.svelte-1ythfu8 { … } }` | 0,1,0 once; later occurrences in the same selector use `:where(.svelte-…)` |
| Astro, `scopedStyleStrategy: 'attribute'` (the config's default) | `@layer components{.btn[data-astro-cid-w3xeq5zm]{…}}` | 0,1,0 |
| Astro, `'class'` | `.btn.astro-w3xeq5zm` | 0,1,0 |
| Astro, `'where'` | `.btn:where(.astro-w3xeq5zm)` | none |

Layers are compared before specificity, so the added specificity never lets a component beat a utility or an override. Inside `components`, a scoped `.btn` beats an unscoped `.btn` from another file (under any strategy but Astro's `'where'`): keep a component's styles in its own file, never split between the component and a global sheet. The selector limits still apply to what you write (Law 5): the gates count your selector, not the compiler's.

### The document shell has no `<main>`

Each framework renders a page into a shell: Next.js's root layout, Vue's `index.html`, SvelteKit's `app.html`, an Astro layout. `a11y_static.py` reads a shell as a document, but its `<main>` comes through an outlet it cannot see (`{children}`, `<slot />`, `%sveltekit.body%`, a Vite app's mount point `<div id="app">`), so it leaves the landmark to the pages. With Next.js's Metadata API, a Next.js `layout` file or SvelteKit's `%sveltekit.head%`, it leaves the title to them too. Each page, or the app's root component, has exactly one `<main>`; `a11y_runtime.mjs` checks the composed page.

### Which files the gates read

| File | `audit_design.py` | `a11y_static.py` | the census | stylelint | ESLint |
|---|---|---|---|---|---|
| `.css`, `.module.css`, `.scss` | yes | its CSS rules | yes | yes | no |
| `.js`, `.jsx`, `.ts`, `.tsx` | yes | its markup | yes | no | yes |
| `.vue`, `.svelte`, `.astro`, `.html` | yes | yes | yes | no | no |

In a `.vue`, `.svelte` or `.astro` file, the audit reads each `<style>` block as CSS in place (the layer check, the literals, the tiers, the selectors), every `style=""`, every bound style (Vue's `:style`, Svelte's `style:x`), and the class lists. The census reads the same blocks and bindings, and counts a written-out value in a binding as an inline style. stylelint and ESLint read the project's stylesheets and scripts, never a component's template or its `<style>` block.

**This is decided (N49, 2026-10-18): the templates are the audit's.** The ESLint config's rules are written against JSX: `className` and `class` attributes, the `style` prop. A Vue template is a second syntax tree that a rule reaches only through the parser's services, as vue-eslint-parser's README says:

> `defineTemplateBodyVisitor(templateVisitor, scriptVisitor, options)` ... returns ESLint visitor to traverse `<template>`.
> (https://github.com/vuejs/vue-eslint-parser#readme)

and svelte-eslint-parser gives the markup node types of its own (`SvelteAttribute`, `SvelteStyleDirective`; https://github.com/sveltejs/svelte-eslint-parser/blob/main/docs/AST.md). Adding either parser would parse the files and check nothing in them: every rule would need a second and a third implementation. The audit already reads every bound form in one place, Angular's included, and the spec's `inline_styles.bound` names it alone. A component's `<script>` block is read by neither linter for the same reason.

### `.design-suite.json`'s `components`

The `components` globs make a file a component file, where the outer-margin rule (Law 2) and the Tier-1 rule (Law 6) apply. A glob reads `*` and `?` within a folder and `**/` as any number of folders; there are no braces, so list each extension:

| Stack | `components` |
|---|---|
| Next.js | `["components/**/*.tsx", "components/**/*.module.css"]` |
| Vue | `["src/components/**/*.vue"]` |
| SvelteKit | `["src/lib/components/**/*.svelte"]` |
| Astro | `["src/components/**/*.astro"]` |

---

## 2. Next.js App Router

### Where the tokens load

The root layout imports the entry, and it is its first import:

```tsx
// app/layout.tsx
import './styles/index.css';
import type { ReactNode } from 'react';

export const metadata = { title: 'Pricing' };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

Next.js orders CSS by import:

> The **order of your CSS** depends on the **order you import styles in your code**.
> (https://nextjs.org/docs/app/getting-started/css)

So the import of `index.css` comes before any component's import, in the root layout, and nowhere else. Next.js allows a global import in any layout, page or component, and says what it costs:

> Global styles can be imported into any layout, page, or component inside the `app` directory. However, since Next.js uses React's built-in support for stylesheets to integrate with Suspense, this currently does not remove stylesheets as you navigate between routes which can lead to conflicts.
> (https://nextjs.org/docs/app/getting-started/css)

Two of its own recommendations keep the order where it was put (same page, "Recommendations"): "Import global styles and Tailwind stylesheets in the root of your application", and "Turn off linters or formatters that auto-sort imports like ESLint's `sort-imports`": a sorter that moves `./styles/index.css` below a component's import reorders the layers.

Next.js states the layer order through `index.css` alone: the root layout's import is the first stylesheet of every route. Check it in the build, as Next.js asks:

> CSS ordering can behave differently in development, always ensure to check the build (`next build`) to verify the final CSS order.
> (https://nextjs.org/docs/app/getting-started/css)

### Components and CSS Modules

A Next.js project often keeps its components in a root `components/` folder, outside `app/`, where no default glob looks. Name it in `components`, both the `.tsx` files and their modules (§1). Each component has its own `Button.module.css`, which `stack-css-modules.md` covers whole: the module wraps its rules in `@layer components`, its classes are `.root` and `data-*` variants, and a runtime value reaches it as a custom property (Law 4's one exception, `stack-css-modules.md` §8).

A CSS Module works in a Server Component: Next.js's own example imports `./blog.module.css` into `app/blog/page.tsx`, a page with no `'use client'`, and says to "import it into any component inside the `app` directory" (https://nextjs.org/docs/app/getting-started/css). No client boundary is needed for styling.

### CSS-in-JS needs a client boundary

> Using CSS-in-JS with newer React features like Server Components and Streaming requires library authors to support the latest version of React
> (https://nextjs.org/docs/app/guides/css-in-js)

and each library's setup is a style registry in a Client Component (`'use client'`) that wraps the root layout's children. A runtime CSS-in-JS library turns the tree it styles into client code. Prefer CSS Modules; the audit and the census still read a CSS-in-JS file's literals.

### The title

`export const metadata = { title: … }` (or `generateMetadata`) writes the `<title>`, in the layout or in each page. `a11y_static.py` reads an export of either as the title, and leaves a `layout` file's title to its pages.

### Tailwind

Tailwind's entry is `stack-tailwind.md`'s `index.tailwind.css`, imported by the root layout in place of `index.css`, with `@tailwindcss/postcss` in `postcss.config.mjs` as Next.js's page shows.

---

## 3. Vue

This section is Vue 3 with Vite. Nuxt loads global CSS through its own config, which this reference does not cover.

### Where the tokens load

The entry module imports `index.css` before the root component, and `index.html` states the order inline, because Vite injects each component's styles as its module is evaluated:

```ts
// src/main.ts
import './styles/index.css';
import { createApp } from 'vue';
import App from './App.vue';

createApp(App).mount('#app');
```

```html
<!-- index.html -->
<head>
  <style>@layer reset, vendor, tokens, base, layout, components, utilities, overrides;</style>
  <script type="module" src="/src/main.ts"></script>
</head>
<body>
  <div id="app"></div>
</body>
```

### `<style scoped>`

Vue scopes a component's styles with an attribute:

> ```
> .example[data-v-f3f3eg9] {
>   color: red;
> }
> ```
> (https://vuejs.org/api/sfc-css-features.html)

Put the rules inside `@layer components`; the compiled selector stays inside the block (§1). Vue scopes a child's root element twice, by design:

> With `scoped`, the parent component's styles will not leak into child components. However, a child component's root node will be affected by both the parent's scoped CSS and the child's scoped CSS. This is by design so that the parent can style the child root element for layout purposes.
> (same page)

That is Law 2's split in Vue's terms: the parent may place the child's root (a grid area, a gap from its container), never skin it. `:deep()` (`.a :deep(.b)` compiles to `.a[data-v-f3f3eg9] .b`, same page) reaches into a child: use it only for content the component renders but does not own, such as `v-html` output, which scoped styles do not reach.

### `v-bind()` in CSS

> The actual value will be compiled into a hashed CSS custom property, so the CSS is still static. The custom property will be applied to the component's root element via inline styles and reactively updated if the source value changes.
> (https://vuejs.org/api/sfc-css-features.html)

`v-bind()` is Law 4's exception in Vue's own form: a runtime value carried by a custom property. Use it for a runtime number (a progress, a measured height) or to pass a role token's name the component chose, never a hex or a pixel value written in the script. The gates cannot read the script's value, so this one is on the reviewer.

### Bound styles

`:style` and `v-bind:style` are inline styles. The audit reports a visual property in one (L4) and a written-out value in a custom property (L1, L6); the census counts a written-out value. Setting the component's own custom property to a token is the legal form:

```vue
<a class="btn" :href="href"
   :style="{ '--btn-bg': tone === 'accent' ? 'var(--bg-accent)' : 'var(--bg-surface)' }">
  <slot />
</a>
```

---

## 4. Svelte and SvelteKit

### Where the tokens load

The root layout imports the entry, so every route has it, and `src/app.html` states the order inline before SvelteKit's head:

```svelte
<!-- src/routes/+layout.svelte -->
<script lang="ts">
  import '../styles/index.css';
  let { children } = $props();
</script>

{@render children()}
```

```html
<!-- src/app.html -->
<head>
  <style>@layer reset, vendor, tokens, base, layout, components, utilities, overrides;</style>
  %sveltekit.head%
</head>
<body data-sveltekit-preload-data="hover">
  <div class="app-shell">%sveltekit.body%</div>
</body>
```

SvelteKit fills the two placeholders (https://svelte.dev/docs/kit/project-structure):

> `%sveltekit.head%` — `<link>` and `<script>` elements needed by the app, plus any `<svelte:head>` content

and `%sveltekit.body%`, "the markup for a rendered page", which "should live inside a `<div>` or other element, rather than directly inside `<body>`". The starter that `sv create` writes gives that element an inline style, `<div style="display: contents">` (https://github.com/sveltejs/cli/blob/main/packages/sv/src/create/templates/minimal/src/app.html), which the audit reports as Law 4. Give it a class and the same rule in the layout layer:

```css
/* src/app.css, imported by +layout.svelte after index.css */
@layer layout {
  .app-shell {
    display: contents;
  }
}
```

### Scoped styles

> This works by adding a class to affected elements, which is based on a hash of the component styles (e.g. `svelte-123xyz`).
> (https://svelte.dev/docs/svelte/scoped-styles)

"Each scoped selector receives a specificity increase of 0-1-0", and "after the first occurrence it is added with `:where(.svelte-xyz123)`" (same page): `.a .b` compiles to `.a.svelte-9cosl9 .b:where(.svelte-9cosl9)`. Put the rules inside `@layer components` (§1). A component's `@keyframes` name is scoped the same way, and its `animation` rules follow (same page); the durations and easings are still the motion tokens.

`:global(...)` and the `:global { … }` block make a selector unscoped (https://svelte.dev/docs/svelte/global-styles). Keep them inside `@layer components`, for content the component renders but does not own (a rendered Markdown body), never to skin another component.

### `style:` directives

`style:color="#c0ffee"` is an inline style: the audit reports a visual property (L4), and the census counts the value. `style:--btn-bg={…}`, the component's own custom property set to a token, is the legal form, as in the fixture's button.

---

## 5. Astro

### Where the tokens load

A layout's frontmatter imports the entry:

```astro
---
// src/layouts/Base.astro
import '../styles/index.css';
const { title } = Astro.props;
---
<html lang="en">
  <head><title>{title}</title></head>
  <body><slot /></body>
</html>
```

Astro decides the order of its styles itself (https://docs.astro.build/en/guides/styling/):

1. "`<link>` tags in the head (lowest precedence)"
2. "imported styles"
3. "scoped styles (highest precedence)"

and "scoped styles will always come last in the order of appearance". An imported `index.css` therefore comes before every component's scoped `<style>`, and its layer statement is the first, as long as no `<link>` stylesheet in the head names a layer of ours. A vendor sheet loaded by a `<link>` names none: import it through `index.css` with `layer(vendor)` instead (`stack-vanilla-css.md` §4).

### Scoped styles and `scopedStyleStrategy`

> Use `data-` attributes, causing a +1 specificity increase.
> (`'attribute'`, the default; the option was added in astro 2.4. https://docs.astro.build/en/reference/configuration-reference/)

`'class'` uses a class (also +1) and `'where'` uses `:where()`, "causing no specificity increase" (same entry). With `'where'`, a component's `.btn` ties with any other `.btn` in the `components` layer and the later one wins; keep the default, or keep every component's classes its own. Every `<style>` block opens `@layer components` (§1).

### `is:global` and `define:vars`

`<style is:global>` opts out of scoping (https://docs.astro.build/en/guides/styling/). It belongs in the entry's files, not in a component. `define:vars` passes "CSS variables directly from your component frontmatter" (same page): Law 4's exception, as Vue's `v-bind()` is, for a runtime value carried by a custom property, never a written-out colour or length.

---

## 6. The fixtures

`tests/fixtures/stacks` holds one small project per stack: `next-app`, `vue`, `svelte` and `astro`, each with its config, its global entry and a button. `tests/test_stacks.py` copies the starter's styles into each, then runs the audit, `a11y_static.py` and the census:

- each runs clean;
- each finds what is planted in the stack's own place: a colour in the Next.js CSS Module and in Astro's scoped `<style>` (L1), in Vue's `:style` and in Svelte's `style:` directive (L4), counted by the census; an `<img>` with no `alt` in each button, found by `a11y_static.py`.

The fixtures are the smallest project that holds each section's claims. Copy one to start a project on that stack.

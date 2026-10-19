# Stack fixtures

One small project per stack that web-design-studio's `stack-frameworks.md`
teaches: Next.js App Router, Vue (Vite), SvelteKit and Astro. Each holds the
stack's own files and a `.design-suite.json`; `tests/test_stacks.py` copies the
starter's `styles/` into the folder the config names, then runs the audit,
`a11y_static` and the census on the copy. Each project is clean, and each test
plants one literal in the stack's own place for it, which every gate must find.

| Folder | Global entry | Component | The planted literal |
|---|---|---|---|
| `next-app` | `app/layout.tsx` imports `styles/index.css` | `components/Button.tsx` and `Button.module.css` | a colour in the CSS Module |
| `vue` | `src/main.ts` imports `styles/index.css` | `src/components/AppButton.vue` | a colour in a `:style` binding |
| `svelte` | `src/routes/+layout.svelte` imports `styles/index.css` | `src/lib/components/Button.svelte` | a colour in a `style:` directive |
| `astro` | `src/layouts/Base.astro` imports `styles/index.css` | `src/components/Button.astro` | a colour in the scoped `<style>` |

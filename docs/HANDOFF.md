# Handoff

**2026-10-18**, the day's second session: **P37 parts 3 and 4 are done** (#172, #173). **Next: P37's last part, the scaffold's Vue and Svelte output (size L, two PRs); then P35, P41, P42 and P43 in the order the owner chooses; then R4.**

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **#172, P37 part 3 (SB-B6, N49)**, merged as `6c0dfcb`.
  - web-design-studio's `stack-frameworks.md` covers Next.js App Router, Vue (Vite), Svelte/SvelteKit and Astro: where the tokens load, where the layer order is stated (inlined in Vite's `index.html` and SvelteKit's `app.html`), how each compiler's scoping meets the layer order (compiled from the fixtures), Vue's `v-bind()` and Astro's `define:vars` as Law 4's exception, the `components` globs, and which gate reads which file. Every framework fact is quoted with its URL.
  - **N49 is decided: a template is the audit's.** The ESLint config's rules are JSX selectors, and neither vue-eslint-parser nor svelte-eslint-parser hands a template to them. stylelint reads no component `<style>` block either.
  - `tests/fixtures/stacks` holds one project per stack; `test_stacks` runs the audit, `a11y_static` and the census on each, clean, and each finds a planted fault.
  - Running the gates on the clean fixtures found three gaps, fixed: `a11y_static` read a framework's document shell as a whole page (`shell_outlets()`), and a `<slot>` as no content; the census counted the `)` of `box-shadow: var(--shadow-xs)` as a shadow.
- **#173, P37 part 4 (DL-B3, in part)**, merged as `c0a6d62`. `scaffold_ui.py --server-actions` writes each form as a Client Component posting its FormData to `server/<table>.actions.ts` (`'use server'`, `create` and a bound `update`), with `useActionState` in `<Entity>ActionForm.tsx` and `useFormStatus` in the Save button; the action reads each field by its type, validates with the zod schema and writes through Supabase's `createServerClient`. `test_scaffold.TheServerActions` runs the generated action in Node against stand-ins.
- **Reviews:** 5 real issues on #172, each fixed with a test failing on the head it reviewed: Codex 4 over two rounds (any `{…}` read as an outlet; `type` before `src` only; any empty element with an id as a mount point; any `layout.tsx` without a title), CodeRabbit 1 (a component beside the page read as an outlet). #173 had no review: Codex was out of usage and CodeRabbit at its hourly limit.
- **At the end:** the plan has 14 open items, all scheduled (SB-B6 and N49 closed); about 1,385 tests. This session used about 510 thousand tokens.

## Next steps

1. **P37's last part: the scaffold's Vue and Svelte output** (DL-B3's rest). The kit (six components) and each entity's list, detail, form and states as `.vue` and `.svelte`, each passing the audit and `a11y_static` as `stack-frameworks.md` gives those stacks. Size L: Vue first, then Svelte, one PR each.
2. Then **ask the owner which of P35, P41, P42 and P43 follows**, and then **R4**.

## Open owner decisions

- The order of P35, P41, P42 and P43 after P37.
- N49 was decided by this session as the item allowed (the templates are the audit's). The owner can still ask for the ESLint parsers instead; it would be a new item.

## Warnings

- **`check.py` takes about 20 minutes** when a shared file changes.
- **Never edit a file the suite reads while `check.py` runs.** This session fixed #172 in a scratchpad worktree while #173's check ran.
- **Bash eats escapes** in a heredoc, twice this session: a `\n` inside a Python replacement became a newline (a syntax error in `scaffold_ui.py`), and a test edit silently matched nothing. Use the Edit tool for any text with a backslash.
- **The token counter resets on every review event.** Keep a running total.
- **Still open from earlier:** the `VitalsUnderCsp` macOS flake; `test_interact_at_clicks_while_the_page_hydrates`; `perf_audit.py` and an unbundled `@import` chain; three tokens outside Display P3; the default scaffold's four `focus-rule-invisible` warnings (zero errors, as its test asks); don't grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.

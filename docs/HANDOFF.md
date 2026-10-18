# Handoff

**2026-10-18**, one session: **P37 parts 1 and 2 are done** (#168, #169). **Next: P37 part 3 (the stacks, with N49), then part 4; then P35, P41, P42 and P43 in the order the owner chooses; then R4.**

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **#168, P37 part 1 (N48)**, merged as `833f97f`. The audit and the census read a framework's bound inline style through one block that both scripts carry verbatim (`# ---- BEGIN bound-styles`):
  - `tag_attributes()` reads each start tag to its own `>`, past quoted and braced values, and steps over a braced expression in text (`{{ … }}`) but not an Angular `@if (…) { … }` block;
  - `bound_styles()` reads Vue's `:style` and `v-bind:style`, Svelte's `style:x`, and Angular's `[style.x]`, `[style.x.unit]`, `[style]`, `[ngStyle]` and `[attr.style]`: each object the value can be (ternary arms, array items, spreads), each string as `style=""`, a written-out string in a condition's arm (`bound_branches()`), comments blanked (`_bound_code()`);
  - the audit gives L4 for a visual property, and L1 or L6 for a custom property's written-out literal or Tier-1 primitive; it now blanks HTML comments in a template, as the census does;
  - the spec's `inline_styles.bound` holds every form, for the audit alone: ESLint parses no `.vue`, `.svelte` or Angular template, recorded as **N49**, which part 3 decides.
- **#169, P37 part 2 (D3)**, merged as `edff839`. stylelint reads SCSS:
  - Part 6 of the config, an override for `**/*.scss`, uses `postcss-scss` with `stylelint-config-standard-scss` 17 and restates the config's own rules over it;
  - a Sass variable in a value reads as a token (`sassAware()`);
  - `design/sass-variable-literal` ports the audit's `sass-literal`;
  - the component and token file classes name their `.scss` files in every gate (`components.scss` too);
  - the pre-commit hook lints staged `.scss` files.

  A CSS-only project installs nothing new: stylelint loads the two packages only for a `.scss` file.
- **Reviews:** 6 real issues, each fixed with a test failing on the head it reviewed.
  - #168: CodeRabbit 1 (commented-out markup, which Codex also found); Codex 4 over two rounds (a condition's literal arm, a comment before a key, tag-shaped text in an interpolation, and the comment case).
  - #169: Codex 1 (`components.scss`).
  - CI 0. Locally, one older census test pinned the old skip of Svelte's `style:color="red"`.
- **At the end:** the plan has 16 open items, all scheduled (N48 closed, N49 opened); about 1,360 tests. This session used about 600 thousand tokens.

## Next steps

1. **P37 part 3:** Next.js App Router, Vue, Svelte and Astro in the stack references, with a fixture project per stack that the gates run on. Decide N49 there: give ESLint `vue-eslint-parser` and `svelte-eslint-parser`, or document the templates as the audit's.
2. **P37 part 4 (DL-B3's rest):** a server-action form variant, and Vue and Svelte output, in content-model-to-ui's scaffold.
3. Then **ask the owner which of P35, P41, P42 and P43 follows**, and then **R4**.

## Open owner decisions

- The order of P35, P41, P42 and P43 after P37.

## Warnings

- **`check.py` takes 19 to 21 minutes** when a shared file changes.
- **Never edit a file the suite reads while `check.py` runs.** This session fixed #168 in a scratchpad worktree while #169's check ran.
- **Bash eats escapes:** a heredoc turns `\\n` into a newline, and backticks inside a double-quoted `python -c` run as commands (a CHANGELOG line lost its examples). Write such text with the Write or Edit tool, or a heredoc fed to `-F -` with a quoted `'EOF'`.
- **The token counter resets on every review event**, acknowledgements included. Keep a running total.
- **Still open from earlier:** the `VitalsUnderCsp` macOS flake; `test_interact_at_clicks_while_the_page_hydrates`; `perf_audit.py` and an unbundled `@import` chain; three tokens outside Display P3; don't grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.

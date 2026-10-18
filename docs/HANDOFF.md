# Handoff

**2026-10-17**, one session: **P34 is done** (#165, #166). **Next: P37 (with N48), the owner's choice of 2026-10-18, in four PRs; then P35, P41, P42 and P43 in the order the owner chooses; then R4.**

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **The owner's decision (2026-10-18):** P37, with N48, follows P34.
- **#165, P34 part 2 (GT-B3)**, merged as `6cca5fd`. `browser_common.mjs`' `DEEP_DOM` walks the composed tree for every a11y_runtime check and the critique's contrast sampler:
  - open roots, closed roots a script attaches (a wrapped `attachShadow` in the init script), and closed roots the parser attaches (`keepClosedRoots()`, through the DevTools protocol);
  - slots in render order, focus followed into each root, paths joined with ` >> `;
  - a closed root shown to axe for its run (`exposeClosed()`), and a warning for a closed root no check read (`unreadRoots()`).

  Tests: `test_runtime_shadow`.
- **#166, P34 part 3 (GT-B4)**, merged as `2ac9164`. `--urls` (a URL a line, a JSON list with a perf `pageType` each, or a sitemap, from a file or a URL; `--max-urls`, the rest counted) in a11y_runtime and measure_vitals, and a11y_runtime's `--viewports`. Each run is a child process (`runEach()`), and one report holds a row per page and viewport, its exit the worst. Tests: `test_runtime_urls`.
- **Reviews:** 7 real issues, each fixed with a test failing on the head it reviewed.
  - #165: Codex 1 (a `delegatesFocus` host is no tab stop), CodeRabbit 2 (a closed root's slot while axe reads it; restore in a `finally`, a guard with no test, which CodeRabbit accepted).
  - #166: Codex 3 (the configured perf budget guarded from `--report`, budget breaches named in the summary, `--max-urls` a whole number).
  - CI 1: macOS once recorded no LCP for the vitals test's home page, so the test reads each page's breaches.
- **At the end:** the plan has 16 open items, all scheduled; about 1,350 tests. This session used about 540 thousand tokens.

## Next steps

1. **P37 part 1, N48:** the audit reads a bound inline style (`:style`, `v-bind:style`, Svelte's `style:x=`, Angular's `[style.x]` and `[ngStyle]`). The prompt's §4 has the detail.
2. **P37 part 2, D3:** SCSS in stylelint (`postcss-scss`, `stylelint-config-standard-scss`), and a check for a Sass variable that holds a literal.
3. **P37 part 3:** Next.js App Router, Vue, Svelte and Astro in the stack references, with fixtures the gates run on.
4. **P37 part 4 (DL-B3's rest):** a server-action form variant, and Vue and Svelte output, in content-model-to-ui's scaffold.
5. Then **ask the owner which of P35, P41, P42 and P43 follows**, and then **R4**, release 4.0.0, in R3.6's order.

## Open owner decisions

- The order of P35, P41, P42 and P43 after P37.

## Warnings

- **`check.py` takes 13 to 25 minutes** when a shared file changes (`browser_common.mjs` reaches 42 test modules).
- **Never edit a file the suite reads while `check.py` runs.** Fix a PR below in a worktree in the scratchpad (`git -c core.longpaths=true worktree add`); this session fixed #165 that way while #166's check ran.
- **Bash heredocs eat backslashes:** a `\n` in a test became a real line break twice this session. Write such code with the Write or Edit tool, and run `node --check` or the test after.
- **The token counter resets on every CI event**, and on the owner's answers too. Keep a running total.
- **Still open from earlier:** the `VitalsUnderCsp` macOS flake; `test_interact_at_clicks_while_the_page_hydrates` (once in 11 local runs); `perf_audit.py` and an unbundled `@import` chain; three tokens outside Display P3; don't grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.

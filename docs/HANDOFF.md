# Handoff

**2026-10-12**, after P38 part 2 (#115), P39 (#116), P40 (#117) and this docs PR. **Phase 6a's code is done.** R3.6, the 3.6.0 release, is next, and its eval dispatch needs the owner's OK first.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then R3.6 in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session**, each with CI green on its head, every thread resolved and GitHub clean:
  - **#115 (P38 part 2): `cqi`, `font-size-adjust`, alpha variants, `interpolate-size`.** typography.md §10 has type sized to its container; §8 has one x-height number for every fallback, on a stack without the re-metricked face. color-system.md §9 derives a role's alpha variants with `color-mix()` and relative colour, on `:root, [data-theme]`. motion-system.md §7 has a disclosure animating to `auto`, whose toggle sets `inert` as it closes. Each snippet runs in Chromium in `test_modern_css`. The spec's literal units take the container units. Closes SS-B4. Codex found 1 real issue (the stack), CodeRabbit 1 (Tab during the close), and CI 1 (a width threshold, now MDN's ratio).
  - **#116 (P39): the migration census reads every style source.** It reads Sass's module colour functions; Vue, Svelte, Astro and HTML (`<style>` blocks, scripts, `style=""`, `class=""`); and CSS-in-JS style objects (`sx`, `css`, `styled({})`, vanilla-extract, Panda). The codemod rewrites the style blocks. rollout.md gains baselines on the old version, Renovate and Dependabot, and `npm deprecate`. Closes LC-B7; LC-B5 is in part (v4's `@theme` is P36's). Codex 2 and CodeRabbit 2 real; CodeRabbit withdrew 1.
  - **#117 (P40): Prisma and Drizzle into content-model-to-ui.** `introspect_schema.py --format prisma|drizzle` reads both to the same model as the DDL, with each loss named. camelCase names meet the snake_case signals, and views are left out. DL-B3 is in part (a server-action form and Vue and Svelte output are P37's). Codex 2 real.
- **At the end:** `main` is this docs PR's merge, on top of #115's `4304120`, with CI green on each code PR's head. No other PR is open, and the checkout at `C:\DEV\Pro-Web-Designer-Suite-Plug-in` is on `main` with no other worktree.
- **The plan:** 23 open items, 23 scheduled. 1,080 tests.
- **No eval was run** this session (none was asked for).

## Next steps

1. **R3.6: release 3.6.0**, in this order (the next-session prompt's §4): a live check of what 3.6.0 changed, with the owner's OK; the release PR (`plugin.json` at 3.6.0, the CHANGELOG dated); on its merge, the eval dispatch, with the owner's OK and its estimate (about $11, under `evals.yml`'s $14 ceiling), so the evals run on the commit that is tagged; then the build and the annotated `v3.6.0` tag.
2. Then Phase 6b (4.0.0): ask the owner which workstream comes first.

## Open owner decisions

- **R3.6's spend:** the eval dispatch (`tag=all`, about $11), and how wide the live check goes (§4 of the next-session prompt suggests one headless session per changed skill, about $1).
- **The `dtcg-export` eval** (`evals/lifecycle/dtcg-export`, about $0.30) can be graded against the script route: run it when the owner says so.

## Warnings

- **GitHub lost a `pull_request` event** on 2026-10-12 (an incident): #115 got no CI until `gh workflow run ci.yml --ref BRANCH`. If a push shows no checks after a few minutes, dispatch it.
- **A TBT flake:** `test_browser_runtime.VitalsMeasures.test_an_interaction_is_not_counted_in_tbt` failed once on macOS (88 against 50, a load-time task on a busy runner, not the click). Re-run the job; if it recurs, give the page's load more room.
- **The masters and their copies.** After every merge from a branch below, copy `shared/dtcg.py`, `shared/project_config.py` and `shared/project_config.mjs` over every copy (ten, ten and seven), then run `TheCopiesAreTheMaster`.
- **A worktree in the scratchpad hits Windows' 260-character path limit:** create it with `git -c core.longpaths=true worktree add "PATH" BRANCH`. `test_file_modes` errors there on a long eval path; ignore it.
- **Run a single test from `tests/`** (`cd tests && python -B -m unittest test_x.Class.test`); from the plugin folder the module is not found.
- **Bash heredocs eat backslashes.** Write edit scripts with the Write tool.
- **CodeRabbit is not a merge gate** (the owner, 2026-10-12). Merge on CI green, threads resolved and clean; fix its real findings when it does review.
- **The token counter resets on every `<ci-monitor-event>` and every user message.** Keep a running total.
- **The scratch repository** `Vybecode-LTD/wds-gate-scratch` is private and the owner's to delete.
- **Still open from earlier:** `perf_audit.py` and an unbundled `@import` chain; headless sessions refused a skill's reference files; the hydration flake (`test_interact_at_clicks_while_the_page_hydrates`, re-run the job) and `test_critique_snapshots`; three tokens outside Display P3; `check_roles.py` clips outside sRGB; the worked examples are tests; a local build never matches the release's checksums; don't grep `tooling/`; the repository is public.

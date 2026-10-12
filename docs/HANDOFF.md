# Handoff

**2026-10-12 (one session, begun 2026-10-11)**, after P32 (#109, #111), the evals change (#110), P33 (#112), P38 part 1 (#113) and this docs PR. Phase 6a continues toward 3.6.0: P38 part 2, P39, P40, then R3.6.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then P38 part 2 in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session**, each with CI green on its head, every thread resolved and GitHub clean:
  - **#109 (P32 part 1): a Plugin API route into Figma on every plan.** `figma_to_tokens.py --reverse --format plugin-script` writes the REST body's variables as code for the MCP server's `use_figma` or a plugin: found by name, updated in place, nothing deleted. Closes LC-B1 and LC-C7. Codex found 1 real issue (the default values must go to the default mode).
  - **#110: `evals.yml` runs only by hand** (the owner, 2026-10-11). Codex found 2 docs still describing the tag trigger.
  - **#111 (P32 part 2): each plan's mode limits.** `figma_audit.py --plan` or `.design-suite.json`'s `figma.plan` (both readers, all copies) reports `MODE_LIMIT` and quiets `MISSING_DARK_MODE` on Starter; a REST body past 40 modes is not written. Closes LC-B6. Codex 1 (seats), CodeRabbit 1 (the REST cap) real; CodeRabbit's "six calls" withdrawn.
  - **#112 (P33): theming without JavaScript with `light-dark()`.** style-architecture.md §10, its example run in Chromium; `check_roles.py` measures each pair per visitor preference. Closes SS-B3. Codex 4 and CodeRabbit 3 real, all in how the gate models the browser.
  - **#113 (P38 part 1): the top layer, `@starting-style`, `:user-invalid`.** A toast inside the modal, with `role="status"`; new `tests/test_modern_css.py`. SS-B4 in part. Codex 1 real.
- **At the end:** `main` is this docs PR's merge (#114), on top of #113's `d369bde`, with CI green on each code PR's head. No other PR is open, and the checkout at `C:\DEV\Pro-Web-Designer-Suite-Plug-in` is on `main` with no other worktree.
- **The plan:** 25 open items, 25 scheduled. 1,061 tests.
- **No eval was run** this session (none was asked for).

## Next steps

1. **P38 part 2** (SS-B4): `cqi`, `font-size-adjust`, `color-mix()` and relative colour, `interpolate-size`, each run in Chromium.
2. Then P39, P40, and R3.6 releases 3.6.0 (the eval dispatch first, with the owner's OK). Phase 6b (4.0.0) follows.

## Open owner decisions

- **The `dtcg-export` eval** (`evals/lifecycle/dtcg-export`, about $0.30) can be graded against the script route: run it when the owner says so.

## Warnings

- **The masters and their copies.** After every merge from a branch below, copy `shared/dtcg.py`, `shared/project_config.py` and `shared/project_config.mjs` over every copy (ten, ten and seven), then run `TheCopiesAreTheMaster`.
- **A worktree in the scratchpad hits Windows' 260-character path limit:** create it with `git -c core.longpaths=true worktree add "PATH" BRANCH`. Its browser tests skip (no `node_modules`); run them in the main checkout, or set `WDS_NODE_MODULES` to the main checkout's `tooling/main/node_modules`.
- **Bash heredocs eat backslashes** (an escaped newline became a real one three times this session). Write edit scripts with the Write tool.
- **CodeRabbit is not a merge gate** (the owner, 2026-10-12): one review an hour made PRs wait for hours. Merge on CI green, threads resolved and clean; fix its real findings when it does review.
- **The token counter resets on every `<ci-monitor-event>`.** Keep a running total.
- **The scratch repository** `Vybecode-LTD/wds-gate-scratch` is private and the owner's to delete.
- **Still open from earlier:** `perf_audit.py` and an unbundled `@import` chain; headless sessions refused a skill's reference files; the hydration flake (`test_interact_at_clicks_while_the_page_hydrates`, re-run the job) and `test_critique_snapshots`; three tokens outside Display P3; `check_roles.py` clips outside sRGB; the worked examples are tests; a local build never matches the release's checksums; don't grep `tooling/`; the repository is public.

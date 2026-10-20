# Handoff

**2026-10-20: P56 is done** (N50, #185 to #187): the seven problems building webdesignersuite.com found are fixed on `main` for 4.0.0 (F5 in part). **P57 (N51, `check_roles` reads the cascade by selector, not by source order) is open and small.** Details are at the top of `dev plans/next-session-prompt.md`. The site (`C:\DEV\webdesignersuite.com`, `Vybecode-LTD/webdesignersuite.com`, staging on Railway) keeps a workaround per finding until 4.0.0 ships; after R4, rerun `/install-gate` there and remove them (`dev plans/plugin-findings.md` in the site).
- **Three more CI traps from this session:** the macOS 3.14 cell failed on timing-dependent browser tests three times, a different one each time (`test_vitals_measure_the_signed_in_page_and_the_late_content` twice, `test_a_page_type_picks_the_budget_its_page_is_held_to`); `gh run rerun RUN --failed` passed each, and nothing in those PRs reached them. **A local `check.py` run that errors with a subprocess `TimeoutExpired` and takes far longer than the usual 11 to 12 minutes means the laptop slept** (System log, Kernel-Power 42): rerun the failing test alone before you debug it. **Never chain `git commit` after `check.py` in one command**: read its exit first (a commit was pushed on a failed run this session; it was a sleep timeout, but the order was wrong).

**2026-10-19**: **P35 is done** (#179, #183; GT-B6 and GT-B9 closed). **Next: P41, P42 and P43, in the order the owner chooses; ask first. Then R4.**

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## 2026-10-19: the rename and the distribution repository (another session)

A second session, beside P35's, did the owner's distribution plan (`dev plans/web-design-suite-distribution-and-promotion.md`):
- **#180, merged as `b2648f8`.** The plugin is now **Pro Web Design Suite, `pro-web-design-suite`**, in `plugins/pro-web-design-suite`. Both marketplace files carry `renames`. Four formats keep the old id, because users' projects hold them; CLAUDE.md's Gotchas lists them. A Codex fix lets `build.py` and `fail_before.py` read a pre-rename `--rev`, such as `v3.6.0`.
- **#181, merged as `24774d0`.** Releases ship without `tests/`, `evals/` and `tools/` (222 files). `build.py --tree` writes the **distribution repository**'s contents, and the build refuses what Anthropic's directory blocks. `release.yml`'s `distribute` job pushes each release to `Vybecode-LTD/pro-web-design-suite`: forward only, atomic, queued, never an older tag over a newer one. CI validates the tree on every PR.
- **#182, which carries this section.** The README now has *Try it*, *Where it works* and *What it runs, sends and stores*. Add to that `SECURITY.md` and `plugin.json`'s `documentationUrl`, `supportUrl` and `privacyPolicyUrl`.

**Before R4's tag, the owner must:**
1. create the empty public repository `Vybecode-LTD/pro-web-design-suite`;
2. add a write deploy key to it, with the private half in this repository's secret `DIST_DEPLOY_KEY`;
3. turn on private vulnerability reporting here, which `SECURITY.md` sends reports to.

Without 1 and 2, `distribute` fails, though the GitHub release still happens. **After R4:**
- check that the distribution repository holds 4.0.0 at its root;
- `/plugin marketplace add Vybecode-LTD/pro-web-design-suite` installs it;
- the owner validates it at claude.ai/directory/manage and submits it (Part A of the distribution plan).

**Its warnings:**
- **Never run the rename script again.** It belongs to a one-time PR. A path in a skip list moves with the rename, and a second run renamed the `renames` key and the CHANGELOG's history before it was caught.
- **The vitals timing tests flake in CI** (`test_runtime_urls...test_a_page_type_picks_the_budget_its_page_is_held_to`, `test_runtime_reach...test_vitals_measure_the_signed_in_page_and_the_late_content`). macOS's headless shell sometimes records no LCP, which the first test's comment notes. On #181 they failed on macOS / Python 3.9 twice and on Windows / Python 3.14 once, then passed on a fresh run.
- **A sensitive `userConfig` value never reaches a skill's script.** Claude Code gives it to hooks and MCP servers only, so `CRUX_API_KEY` and `FIGMA_TOKEN` stay environment variables.

## State

- **#179, P35 part 1 (GT-B6)**, merged as `8a99f60`. `a11y_runtime.mjs` has four new checks, each skippable by name and counted by a budget key, and `reflow` reads clipped text:
  - `spacing` (1.4.12): WCAG's text spacing injected, the text a box newly clips;
  - `obscured` (2.4.11): Tab down and Shift+Tab up, a 5×5 hit test of each stop against the fixed and sticky elements that paint over it;
  - `hover` (1.4.13): persistent, hoverable, dismissible, for each control a hidden node describes;
  - `motion`: the page with and without `prefers-reduced-motion`, as the suite's policy (warnings);
  - `reflow`: text clipped at 200% (1.4.4) and 320px (1.4.10).
  - Clipping is measured on the text's own rectangles against the box that governs its overflow, never a box's scroll size.
  - Budget keys: `text_spacing_failures`, `focus_obscured`, `hover_content_failures`, `motion_not_reduced`, `motion_content_hidden`, `motion_busy_stopped`. The 4.0.0 upgrade notes say the checks run by default, and that `--skip` is the rollout.
- **#183, P35 part 2 (GT-B9)**, merged as `1a37335`. `--engine firefox|webkit` runs axe, the names and the tab order in Playwright's pinned builds; the rest stay Chromium's, and the run says so. Whether an engine's Tab skips bare links is read from the run: WebKit's Windows and macOS builds skip them, its Linux build does not. CI installs Firefox and WebKit on Linux and sets `WDS_REQUIRE_ENGINES` there (the owner's OK, 2026-10-19).
- **#180, the rename** (the owner's other session), merged before #183. The plugin is **Pro Web Design Suite**, in `plugins/pro-web-design-suite`. #183 merged `main` across it.
- **#181 and #182** (the distribution repository; ready for Anthropic's directory), the other session's, are merged too: see the section above.
- **Reviews:**
  - **#179, 14 distinct real issues** (Codex 11 over three rounds; CodeRabbit 3, one the same as Codex's; CI 1), each fixed with a test failing on the head it reviewed.
  - **#183, 3 distinct** (CI 1: WebKit's Linux build tabs to links; CodeRabbit 2; Codex 1, the same as one of CodeRabbit's).
- **At the end:** 11 open items, all scheduled; about 1,440 tests. This session used about 570 thousand tokens.

## Next steps

1. **Ask the owner which of P41, P42 and P43 comes first.** Sizes and scope are in the next-session prompt's §4.
2. Do them in that order, each split into PRs of under 100 files.
3. Then **R4**, the 4.0.0 release, with its live check (the owner's OK and an estimate first).

## Open owner decisions

- **Before R4:** create `Vybecode-LTD/pro-web-design-suite` and its `DIST_DEPLOY_KEY` deploy key, and turn on private vulnerability reporting (the 2026-10-19 section above). Also decide whether issues live in the distribution repository or here; `supportUrl` points here for now.
- The order of P41 (email), P42 (persuasion law, consent, price tests, WCAG mapping) and P43 (page types, claims layer, routing).
- Whether to start the proposed follow-up: `check.py` should select `test_doc_snippets` and stylelint's snippet test when a reference changes. It missed the snippet that failed #179's CI.

## Warnings

- **This Windows machine refuses Playwright's unsigned Firefox build** ("Permission denied", probably Smart App Control). Firefox's tests skip locally and run on CI's Linux cells. Changing that is a system security setting: never touch it.
- **`check.py` misses snippet tests** for a changed reference (see above). After editing a reference's code fence, run `test_doc_snippets` and `test_real_tools.StylelintConfig` yourself.
- **Never edit a file the suite reads while `check.py` runs.** It happened twice this session, so stop the run and start it again.
- **Bash eats backslashes in heredocs**, twice this session. Use the Edit tool for any text with a backslash.
- **The macOS Python 3.9 cell** failed once on `test_runtime_reach`'s vitals test (no LCP recorded): the known flake. A rerun passed.
- **Still open from earlier:**
  - the `VitalsUnderCsp` macOS flake, and `test_interact_at_clicks_while_the_page_hydrates`;
  - `perf_audit.py` and an unbundled `@import` chain;
  - three tokens outside Display P3;
  - the default scaffold's `focus-rule-invisible` warnings.
- **Standing:** don't grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.

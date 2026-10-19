# Handoff

**2026-10-19**: **P35 is done** (#179, #183; GT-B6 and GT-B9 closed). **Next: P41, P42 and P43, in the order the owner chooses; ask first. Then R4.**

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

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
- **Open, not this session's:** #181 (the distribution repository) and #182 (ready for Anthropic's directory), the owner's other session's.
- **Reviews:**
  - **#179, 16 real issues** over four rounds (Codex 13, CodeRabbit 3), each fixed with a test failing on the head it reviewed.
  - **#183, 4** (CI 1: WebKit's Linux build tabs to links; CodeRabbit 2; Codex 1, the same as one of CodeRabbit's).
- **At the end:** 11 open items, all scheduled; about 1,440 tests. This session used about 570 thousand tokens.

## Next steps

1. **Ask the owner which of P41, P42 and P43 comes first.** Sizes and scope are in the next-session prompt's §4.
2. Do them in that order, each split into PRs of under 100 files.
3. Then **R4**, the 4.0.0 release, with its live check (the owner's OK and an estimate first).

## Open owner decisions

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

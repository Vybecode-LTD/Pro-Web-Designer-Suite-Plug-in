# Handoff

**2026-10-02**, at the end of the session that answered #18's review, opened PR #19 (P2 part 2) and PR #20 (P3 part 1), and left five PRs stacked.

**The next session starts from `dev plans/next-session-prompt.md`.** It has the orientation, then P3 part 2 (SB-A15 and N31) in detail.

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed. 3.3.0 is in progress on `main`, unreleased.
- **Open, waiting for the user to merge, in this order** (each is stacked on the one before; GitHub retargets each to `main` when the branch below it is deleted):
  - **#16, P0:** what the reviews of #12 to #15 found (N16 to N25, N29). Reviewed, every thread resolved. It has no CI of its own: the workflow arrives in #17.
  - **#17, P1:** CI on three platforms, the release build, `fail_before.py`, `check.py`, N5. CI green on all six suite jobs, so decision D1 is in force; its description has the acceptance results.
  - **#18, P2 part 1:** `tools/sync_rules.py` and the first data blocks. Codex's one thread was real (the audit's nesting hint said "past depth 2" whatever the spec set), fixed in `9053727` with a test that fails before, and resolved. CI green.
  - **#19, P2 part 2 (N2, SB-C2):** the spec's `values` (shapes, keywords, colour words, colour functions, eight families of 43 properties) written into the gates; each section names its `gates`. A conformance test runs every example through the audit, stylelint and ESLint, and found N30. `check.py` now prints on a cp1252 console. CI: one flake on macOS 3.14 (the mega-menu test), and the failed job was re-run.
  - **#20, P3 part 1 (N1, N30):** the three gates agree on every example; `KNOWN_DISAGREEMENTS` is empty. The audit is stricter (a factor on a token, `em`/`rem` font sizes, the sizing family, element selectors in component files, system colours, inline literals); stylelint gains `design/color-no-hex` and `design/component-margins`; 13 reference snippets were fixed. It also fixes the mega-menu flake properly. CI was running at handoff.
- **Tests:** 436. **The plan:** 149 open items, all scheduled (`check_execution_plan.py`). N2, SB-C2, N1 and N30 closed this session; N30 and N31 were found by the new conformance test and in fixing N1.

## Next steps

1. **The user:** merge #16, #17, #18, #19 and #20, in that order, once each is green. Five stacked PRs is more than decision D7's three: merging soon keeps the next session's PRs off a deep stack.
2. **The next session:** check #20's CI and #19's re-run, fix anything red (a fix to a lower PR is merged up the stack), then P3 part 2: SB-A15 (the stylelint allowlist's holes) and N31, as the prompt describes. Then P4.

## Open questions for the user

- **Skill descriptions and claude.ai uploads.** All 13 descriptions are 301 to 368 characters; the claude.ai help center gives 200 for an uploaded skill, the platform 1024. `build.py` warns and still builds. Shortening them touches routing (P27/P28).
- **SB-A15's design choices** are listed in the prompt with a recommendation each (positional properties, which sizes, `color-mix()`/`light-dark()`, `theme.css`). The session can take the recommendations unless the user says otherwise.

## Warnings

- **Cost.** This session used about 530 thousand tokens: about 90 thousand is the fixed overhead before the first message, and the full-suite runs, each about 6 to 10 minutes, add waiting rather than tokens.
- **`check.py` runs the whole suite** whenever a shared file changed since `main` (anything in `tools/`, `design-rules.json`, the configs): with the stack unmerged, that is every run.
- **A stricter audit reaches the references.** `test_doc_snippets` audits every CSS block in the references; a new check needs the references fixed in the same PR, or the block placed in its layer (`@layer base`/`layout`).
- **Browser tests and the fake clock.** Playwright's clock decides the page's timers, not when Chromium delivers input. Wait until the page has seen an event before advancing the clock (`test_recipes`'s `seen()`).
- **Bash heredocs eat backslashes.** Write anything with a backslash with the Write or Edit tool, or splice it from a file.
- **Don't edit a file the suite reads while it runs.** Plan docs are safe; the CHANGELOG and README are read by `test_docs`.
- **The repository is public.** Commit nothing private.

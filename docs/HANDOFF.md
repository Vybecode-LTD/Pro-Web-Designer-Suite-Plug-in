# Handoff

**2026-10-27 (second session): P64 and P65 merged for 4.0.2. 4.0.1 is still in the directory's review.**
- #212 makes a missing engine's installation hint name the CLI of the Playwright the gate loaded.
- #213 rebuilds the contrast pass's overlay probe. It removes webawesome.com's false `contrast-under-overlay` errors: 78 on the home page and 195 on the button page.

The next session starts from `dev plans/next-session-prompt.md` (§3, then §4). `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **`main` at `e59d6b3`** (#213's merge); its CI run was in progress at the end. #212's merge passed. No PR is open.
- **Released:** `v4.0.1` on `84f4a4f`. The distribution repository's `main` and `v4.0.1` are at `4809e3f`. 4.0.2 is unreleased and held by the owner until the reviewer decides on 4.0.1.
- **On `main` for 4.0.2** (CHANGELOG `4.0.2 — unreleased`): P60 (#207) to P63 (#210), then:
  - **P64 (#212, N58):** `installHint()` in `shared/browser_common.mjs` (five copies) names the loaded package's CLI by path. The path is quoted for POSIX shells, or in double quotes on Windows; a Windows path holding `$`, `` ` ``, `%` or `!` is named on its own.
  - **P65 (#213, N59):** `CONTRAST_FN` in `a11y_runtime.mjs` changed in five ways (§7 of `references/runtime-checks.md` has the details):
    - It probes the middle of the text's first line, scrolled into view inside each scroll container and then on the page. Every scroll is put back.
    - It lifts `pointer-events: none` layers for the pass, then restores them.
    - It collects the stack at the point through every shadow root (`window.__a11y.stackAt`, now shared with the obscured check).
    - It counts only what the hit's own root lists before the text, weighted by opacity.
    - An opaque layer makes the text `contrast-unmeasurable`.
    - Codex and CodeRabbit each found a real gap (a scrim inside a shadow root, a text in a scroll container), and both are fixed with tests. The PR carries 11 tests: 8 fail on 4.0.1.
- **The directory:** read in the owner's Chrome on 2026-10-27, still waiting for the reviewer. The scan's findings stand. The owner chose to change only the installation hint (P64). Answers to every finding are ready in `web-design-suite-distribution-and-promotion.md` ("If the reviewer asks").
- **The execution plan:** `check_execution_plan.py` shows 0 open and 0 scheduled. The next free numbers are N60 and P66.

## Next steps

1. **The submission.** Ask the owner what the portal shows. The owner answers the reviewer; ask before every step in the portal.
2. **When the owner says so, release 4.0.2** (P60 to P65):
   - date the CHANGELOG section and set `plugin.json`'s `version` in the release PR;
   - run `evals.yml` (`tag=all`, about $10, with the owner's OK) on its merge;
   - then tag.
3. **Or the owner picks** one of the live check's four remaining follow-ups (each gets an N-item and a P-row first), or Part B of the distribution plan.

## Open owner decisions

- **The live check's four remaining follow-ups** (the last section of `dev plans/web-design-suite-4.0.0-live-check.md`):
  - the hover check on a JavaScript tooltip;
  - migrating onto a codebase's own token names;
  - sending email through a real provider, which needs the owner's key;
  - **new:** webawesome.com's home page at 390x844 never finishes. It hangs after `browser:`, on 4.0.1 too and with every check skipped.
- **Part B** of `web-design-suite-distribution-and-promotion.md`: topics and a social preview for the distribution repository, then the listings.
- **Where issues live:** the distribution repository or this one. Also whether to add a terms-of-service link.
- **`check.py`:** should it run `test_doc_snippets` and stylelint's snippet test when a reference changes?
- **`next-session-prompt.md`:** should it be split? It is about 125 KB against the workspace's 4 KB rule.
- **The owner's own install** is still 3.6.0.

## Warnings

- **This session went over its 750K-token budget again.** It filled a context window and was compacted once. Report `get_usage` after every PR, and write the handoff while there is room.
- **Look at the CPU before a long `check.py`.** An unrelated MSVC build (15 `cl.exe`) held it at 100%. The check then took 3.4 hours instead of about 20 minutes, and `test_runtime_urls.EachPageHasItsTypesBudget` timed out at 600 s; alone, it passes in 4 s.
- **Stopping processes:** the auto-mode classifier refused `Stop-Process` on a hung runner. Stop the background task with `TaskStop` instead.
- **A release's upload can 404** right after the release is created. Rerun the failed job (`gh run rerun RUN --failed`).
- **Two SKILL.md files are near the 20,500-byte cap:** landing-page-conversion at 20,498 and email-template-system at 20,492. An addition needs a cut.
- **Known flakes:**
  - `test_runtime_urls.EachPageHasItsTypesBudget` (Windows, and under load);
  - `test_tbt_stops_at_tti` (Windows);
  - `VitalsUnderCsp` (macOS);
  - `test_interact_at_clicks_while_the_page_hydrates`;
  - the vitals timing tests.
- **Standing:** never grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.

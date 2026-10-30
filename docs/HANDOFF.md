# Handoff

**2026-10-29 (the second session): stage 1 closed, P74 merged, P75 open in its second review round.** P73 (#230) and P74 (#231) are merged; P75 is #232, open.
- **P73, #230, the scaffold:** a table with no title links its rows from the first listed cell, a `timestamptz` is shown and edited in the browser's zone (`toLocalInput`, `fromLocalInput` in `lib/format.ts`), a naive one takes the wall time (zod `local: true`), a radio group's fieldset has the id the error summary links to, a state word with no closed set is a text box, React brackets odd keys, JSX copy is escaped. Review: CodeRabbit's daylight-saving cases.
- **P74, #231, bounded waits:** **L8's real cause** was `injectAxe` awaiting `addScriptTag` in a lazy iframe with no document (webawesome.com at 390x844 now finishes in 62 s; the 4.0.0 live check records it). Also `waitForFonts()`/`bounded()` in `shared/browser_common.mjs`, 5 s focus shots with `focus-not-measured`, an async `runEach` with a 15-minute limit and streamed steps, and `check.py` running `test_static_checks` and `test_harness` for any changed test module. Review: frames at once, a refused injection reported, the timer wrapper keeps `this`.
- **P75, #232, open:** the eight JS-B fixes and Codex's two (a password never quoted, a control's opacity once) are pushed (`075a783`), CI was running on it. **CodeRabbit's round on `d8a2414` is not done:** six open threads, each real:
  1. `isMobile` is unsupported in Firefox: a `--engine firefox` run under 768 px fails to open its context.
  2. With `isMobile`, `checkReflow` can measure a 980 px layout viewport: run reflow in a non-mobile context.
  3. A `textarea`'s text is measured twice (the text loop and the value loop): skip `textarea`, `select` and `option` in the text loop.
  4. A control inside an ancestor at `opacity: 0` gives a false 1:1 error: skip when `walked.shown <= 0`, as the text loop does.
  5. The opacity message ends `alike,.`: drop the comma.
  6. `scripts.md`: the axe rule's matrix exception (sheet chrome is demoted), and `mobile` (JSON) against "as a touch phone" (text).

## State

- **`main` = this PR's merge**, on #231's merge `455d085`.
- **Open:** #232 (P75, base `main`, head `075a783`).
- **Released:** `v4.0.1`; P60 to P74 on `main` for 4.1.0.
- **The plans:** `check_execution_plan.py` 15 open, 15 scheduled. Next free ids: **N84, P90**; the next PR is #234 (this one is #233).

## Next steps

1. **Finish #232:** the six threads above, each with a test failing on `d8a2414` (`fail_before.py --rev d8a2414…`), reply and resolve, merge; then tick P75 in the runbook's §7, the execution plan and N69.
2. **P76**, vitals, the matrix and the critique capture (N70). Then stage 3 (P77 to P79).

## Open owner steps

- **The four GitHub settings** (the runbook's §3): not done, as of the first session of 2026-10-29.
- **Delete `Vybecode-LTD/wds-gate-scratch`** (Q12).

## Warnings

- **`scaffold_ui.py` is 260,905 bytes, 1,239 under the directory's 262,144-byte hold** (`test_release_build.TheDirectoryChecks`). Its next growth moves `FORMAT_TS` (5.7 KB) into `assets/`.
- **The fonts fix leans on Playwright's `PW_TEST_SCREENSHOT_NO_FONTS_READY`**, which 1.64.1 reads at every screenshot. A bump that drops it shows in `TheGatesBoundTheirWaits.test_the_audit_goes_on_without_the_font_and_says_so`.
- **A change to `tools/` or `shared/` runs the whole suite through `check.py`**: 32 minutes here. After a whole-suite pass, `check.py --base SHA` runs only what changed since.
- **The Bash heredoc unescapes `\\`** (twice more this session): use the Edit tool for anything with backslashes.
- **Codex and CodeRabbit found real bugs in every PR, twice in #232.** CodeRabbit skips a PR whose base is not `main` and reviews again once it is retargeted.
- **Budget:** stopped near the 750K cap, by my own estimate (no counter was visible).

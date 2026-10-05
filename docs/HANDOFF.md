# Handoff

**2026-10-05**, after P15 (#49, #50), P16 (#53) and P17 (#54). Phase 4 (3.4.0) is under way; 3.3.0 is the latest release.

**The next session starts from `dev plans/next-session-prompt.md`** (orientation, then P18 and P19 in detail). `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session:** #49 and #50 (P15), #53 (P16), #54 (P17), each with CI green on its head, every thread resolved, CodeRabbit finished and GitHub clean; then this docs PR. No PR is open.
- **What they did:**
  - **P15, #49 and #50: the migration tools.** A negative margin cancels its parent rule's padding with that padding's token, and only when the pairing is certain: the side set in one block of the file (the last `!important` declaration winning), read the same left to right and right to left. A type tie snaps up. Law 6's lists are the spec's `tiers`. deprecate.py rewrites and counts a colour rename. The worked examples are fixtures held by tests. Closes LC-A11, A12, A14, A19, C4, C12.
  - **P16, #53: the Figma scripts.** One reader, `figma_common.py`, for both scripts; the audit no longer splits a records export's modes, and a flat plugin export is read by mode name. `--reverse` writes a body Figma takes: the four arrays only, each first mode named by an `UPDATE`, primitives with no scopes, durations in milliseconds. Closes LC-A22, LC-C3.
  - **P17, #54: the lifecycle instructions.** rollout.md's example is a 3.0.0, committed once; deprecate.py refuses a removal outside a major; the reconciliation report's ms deltas and Sass advice; six doc corrections. Closes LC-A17, A23, B8, C6.
- **Beyond the two threads left on #49** (cascade order across `@media` and `@layer`), **the reviews found 16 real issues** (CodeRabbit 15, Codex 2, one found by both), each fixed with a test that fails on the head it reviewed or on `v3.3.0`: `!important` read as a padding slot, logical sides taken as physical, a quoted `;` and an escaped quote in the scan, `!important` labelled manual, mode ids for names, a `default` theme's collision, a dropped duration, the delete-the-variable advice reaching plain properties, one colour in two holders named as the first, a review table labelled in px that held durations and showed colours as +0px, a darken() sentence that overstated the report, the tier examples never run through the audit, and doc fixes with no test (now `LifecycleDocClaims`). One request was declined (WCAG's 3:1 in `evidence.json`; the register holds figures from studies, not the thresholds the gates enforce).
- **The plan:** 90 open items, all scheduled (`check_execution_plan.py`).

## Next steps

1. **P18**, the email templates and lint (DL-A10, A11, A12, A20, B6, C3, C5), with **DL-A13 moved in from P19**: its fix is `lint_email --source`, DL-C5's. L: split it if it runs long.
2. **P19**, the email build and facts (DL-A14, A21, B7).
3. Then P20 to P23, and R2, the 3.4.0 release.
4. **Not yet scheduled:** a Law 6 check in stylelint and the ESLint config (only the audit reads Law 6 today). Schedule it in Phase 5 or 7 and run the checker.

## Warnings

- **A new flake:** `test_browser_runtime.VitalsMeasures.test_interact_at_clicks_while_the_page_hydrates` errored once on Windows/3.9 (#49's first run): INP came back empty (`out["stats"]["inp"]` was None). A re-run passed. If it recurs, fail with a message instead of a `TypeError`, then find why the click's event timing went unreported. The macOS focus-ring timeout from #46 has not recurred.
- **CI runners:** a macOS job cancelled after 15 minutes with no log never got a runner; re-run it.
- **The worked examples are tests.** A change to what the migration tools, the audit or diff_system print can fail `TheWorkedRun` or `TheWorkedRelease`: update the page's numbers from the output.
- **measure_vitals' default throttle changed** to `lighthouse`: the 3.4.0 release notes must say lab numbers rise (the CHANGELOG does).
- **Stage a new file before running `check.py`** (`test_file_modes` reads git's index). **`fail_before.py --rev` needs a full SHA.**
- **A local build never matches the release's checksums** (zlib-ng on Windows' Python 3.14): compare with `tooling/release/compare.py`.
- **Still open from earlier:** `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3; `check_roles.py` measures a colour outside sRGB with its channels clipped.
- **Bash heredocs eat backslashes, and `write_text` writes CRLF on Windows.** Write scripts with the Write tool, and files with `write_bytes`. **Don't grep `tooling/`.** **The repository is public.**

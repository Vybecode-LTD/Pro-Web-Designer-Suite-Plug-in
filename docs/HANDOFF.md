# Handoff

**2026-10-05**, after P14 (#48, merged) and P15 (#49, #50, open). Phase 4 (3.4.0) is under way; 3.3.0 is the latest release.

**The next session starts from `dev plans/next-session-prompt.md`.** It has the orientation, the two open PRs to finish, then the next PRs in detail: P16 (the Figma scripts) and P17 (the lifecycle instructions).

## State

- **Merged this session:** #48 (P14), with CI green on its head, every thread resolved, CodeRabbit finished and GitHub clean. `main` is at `1a54900`, before this docs PR.
- **Open:** #49 (P15 part 1) and #50 (part 2, stacked on #49). Both pass locally; #49 has two open CodeRabbit threads. See Next steps.

- **What the three PRs did:**
  - **P14, #48: diff_system's classification.** Density, media-condition and root-element changes were never compared, so the review's v1 to v3 was a patch "because nothing changed"; they are `density-changed`, `condition-changed` and `element-changed`, all major. An added theme override that moves a value is major. A local class renamed under CSS Modules is a patch, unless the component exports its styles object. system.json records the `@layer` order, each part's declarations and `exports_styles` (additive keys). Closes LC-A8, LC-A9, LC-C5.
  - **P15 part 1, #49: the migration tools.** A negative margin cancels its parent rule's padding with that padding's token, on the same axis. A type tie always snaps up. Law 6's lists are design-rules.json's `tiers`, written by sync_rules into the audit and extract_system, which disagreed. Closes LC-A11, LC-A12, LC-A19.
  - **P15 part 2, #50.** A colour rename beside a `font-weight` is rewritten, and deprecate.py's scan reads each declaration on a line. The two worked examples are fixtures (`tests/fixtures/worked-run`, `worked-release.json`), and tests hold every number their pages quote to the tools' output. Closes LC-A14, LC-C4, LC-C12.
- **The reviews found 13 real issues** (Codex 6, CodeRabbit 7) and no wrong one; one more request was declined as out of scope (below). Among them: a re-point equal by default but not under reduced motion, a fragment root unreported, a local rename that also changed a value, declarations from a part's first rule only, a root read from a helper above the component, an exported styles object, a cancel matched on the wrong axis or side, against an overridden padding or in another media query, and a rewrite that dropped `!important`. Each fix has a test that fails on the head it reviewed.
- **Tests:** 591 on `main`, 604 with #49 and #50. **The plan:** 102 open items on `main` (96 once #49 and #50 merge), all scheduled.

## Next steps

1. **First, finish #49 and #50.** Two valid CodeRabbit threads remain on #49, both edge cases of the negative-cancel pairing (cascade order across `@media` contexts, and `@layer` precedence). Pair only when the parent's padding on that side is unambiguous, and keep the gap token otherwise; the next-session prompt's §3 has the steps.
2. **Then:** P16 (LC-A22, LC-C3), then P17 (LC-A17, LC-A23, LC-B8, LC-C6).
3. Then the rest of Phase 4 (P18 to P23), and R2, the 3.4.0 release.
4. **Not yet scheduled:** a Law 6 check in stylelint and the ESLint config. Today only the audit reads Law 6 for CSS `var()` reads (the spec's `tiers` names one gate). CodeRabbit asked for it on #49; it is a new gate with spec examples and real-tool tests. Schedule it (Phase 5 or 7) and run `check_execution_plan.py`.
5. **Offered as its own task:** the audit skips JS checks for any file whose absolute path names `test`, `spec`, `stories`, `mock` or `fixture` (`audit_design.py` around line 1658).

## Warnings

- **The worked examples are tests now.** A change to what the migration tools, the audit or diff_system print can fail `TheWorkedRun` or `TheWorkedRelease`: update the page's numbers from the output.
- **measure_vitals' default throttle changed** from `slow4g` to `lighthouse`: lab numbers rise on upgrade. The 3.4.0 release notes must say so (the CHANGELOG does, under Changed).
- **A known flake:** `test_the_focus_ring_is_measured_at_each_density_the_page_declares` timed out loading its page (45 s) once on macOS, on #46. If it recurs, give its `page.goto` more time.
- **CI's Windows and macOS jobs run branded Chrome; Linux runs the headless shell.** Run a new browser test several times, in both, before pushing.
- **Stage a new file before running `check.py`:** `test_file_modes` reads git's index.
- **A local build never matches the release's checksums** (zlib-ng on Windows' Python 3.14, zlib on CI). Compare with `python -B tooling/release/compare.py OUT RELEASE_DIR`.
- **The README's `WDS` paths name the version.** A release PR updates them with `plugin.json`.
- **`fail_before.py` swaps the plugin, spec and docs included, not the tests,** so a test-only fix or a new spec example shows as a control; a review fix runs with `--rev` the head it fixes.
- **Still open from earlier:** `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3; `check_roles.py` measures a colour outside sRGB with its channels clipped.
- **Bash heredocs eat backslashes** (twice more this session), **and Python's `write_text` writes CRLF on Windows.** Write scripts with the Write tool, and files with `write_bytes`. **Don't grep `tooling/`.**
- **The repository is public.** Commit nothing private.

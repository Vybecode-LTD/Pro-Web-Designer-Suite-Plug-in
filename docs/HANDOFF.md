# Handoff

**2026-10-05**, after P12 part 2 (#44) and P13 (#45, #46). Phase 4 (3.4.0) is under way; 3.3.0 is the latest release.

**The next session starts from `dev plans/next-session-prompt.md`.** It has the orientation, then the next PRs in detail: P14 (diff_system's classification) and P15 (the migration tools).

## State

- **Merged this session**, each with CI green on its head, every review thread answered and resolved, CodeRabbit finished on the head, and GitHub reporting it clean: #44, #45 and #46, a stack merged bottom-up. `main` is at `a47eba5`, before this docs PR.

- **What the three PRs did:**
  - **P12 part 2, #44: the matrix model and its baselines.** A content fixture may be `{"html", "dir", "lang"}`, so an RTL fixture mirrors the whole component. `snapshot_matrix.mjs --forced-colors` shoots every cell under forced colours with its own baselines, and fails a focus ring that vanishes there (a `box-shadow` ring). state-coverage.md says which interaction states an attribute renders and which need an interaction test. visual-regression.md records baselines in the gate's runner (a `workflow_dispatch` job, on the default branch first) and moves them to Git LFS past about 2,000. Closes GT-B7, GT-B8.
  - **P13 part 1, #45: measure_vitals.** A `lighthouse` preset applies Lighthouse's own DevTools throttling (562.5 ms per request, 1.44 Mbps, 4× CPU) and is the new default; TTFB is CDP's, which sees the emulated latency (Navigation Timing reported 2 to 5 ms under 562.5 ms). TBT leaves out the interaction's own task and ends at TTI, with in-flight requests read from CDP. `--interact-at MS` clicks while the page hydrates. Closes GT-A6, GT-A17.
  - **P13 part 2, #46: `crux_check.py`.** The CrUX field p75 against the lab median, the trigger perf SKILL.md gives for re-deriving a profile. The key comes from `CRUX_API_KEY` only. Closes GT-B5, GT-C11.
- **The reviews found 17 real issues** (CodeRabbit 12, Codex 3, CI 2) **and 1 wrong one**: CodeRabbit claimed a `workflow_dispatch` workflow must run once on the default branch before it can target another branch; GitHub's docs, re-read, give only the default-branch rule. Among the real ones: in-flight requests missing from TTI's network test, a lab median of 0 left unjudged, a `CRUX_API_URL` that could carry the key over plain HTTP, a saved CrUX response for another page accepted, and a script committed without its executable bit. Each code fix has a test that fails on the head it reviewed (one, CDP's unset `-1`, through a function run on its own).
- **Tests:** 572. **The plan:** 105 open items, all scheduled (`check_execution_plan.py`).

## Next steps

1. **The next session:** P14 (LC-A8, LC-A9, LC-C5), then P15 (LC-A11, LC-A12, LC-A14, LC-A19, LC-C4, LC-C12), split in two.
2. Then the rest of Phase 4 (P16 to P23), and R2, the 3.4.0 release.

## Warnings

- **measure_vitals' default throttle changed** from `slow4g` to `lighthouse`: lab numbers rise on upgrade. The 3.4.0 release notes must say so (the CHANGELOG does, under Changed).
- **A known flake:** `test_the_focus_ring_is_measured_at_each_density_the_page_declares` timed out loading its page (45 s) once on macOS, on #46; a re-run passed. If it recurs, give its `page.goto` more time.
- **CI's Windows and macOS jobs run branded Chrome; Linux runs the headless shell.** Run a new browser test several times, in both, before pushing. Chrome's cold start delays the first request by up to half a second: time anything by the page's own clock.
- **Stage a new file before running `check.py`:** `test_file_modes` reads git's index, so a new script with a shebang and no executable bit passes locally and fails in CI.
- **A local build never matches the release's checksums** (zlib-ng on Windows' Python 3.14, zlib on CI). Compare with `python -B tooling/release/compare.py OUT RELEASE_DIR`.
- **The README's `WDS` paths name the version.** A release PR updates them with `plugin.json`.
- **`fail_before.py` swaps the plugin, not the tests,** so a test-only fix shows as a control; a review fix runs with `--rev` the head it fixes.
- **Still open from earlier:** `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3; `check_roles.py` measures a colour outside sRGB with its channels clipped.
- **Bash heredocs eat backslashes, and Python's `write_text` writes CRLF on Windows.** Write scripts with the Write tool, and files with `write_bytes`. **Don't grep `tooling/`.**
- **The repository is public.** Commit nothing private.

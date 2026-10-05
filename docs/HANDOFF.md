# Handoff

**2026-10-05**, after P10 (#39, #40), P11 (#41) and P12 part 1 (#42). Phase 4 (3.4.0) is under way; 3.3.0 is the latest release.

**The next session starts from `dev plans/next-session-prompt.md`.** It has the orientation, then the next PRs in detail: P12 part 2 (the matrix model and its baseline lifecycle) and P13 (measure_vitals).

## State

- **Merged this session**, each with CI green on its head, every review thread answered and resolved, CodeRabbit finished on the head, and GitHub reporting it clean: #39, #40, #41 and #42, a stack merged bottom-up. `main` is at `a88d6a6`.

- **What the four PRs did:**
  - **P10 part 1, #39: a strict CSP, crashes, disabled controls.** a11y_runtime and snapshot_matrix bypass a page's CSP, which refused the freeze stylesheet they inject; measure_vitals keeps it, since a bypass would run what the CSP blocks. A crash in any of the three exits 2, never 1. Disabled controls are exempt from contrast (SC 1.4.3), except what sits in a disabled fieldset's first legend. Branded Chrome's Tab wrap on a one-stop page is no longer a keyboard trap. Closes GT-A5, GT-A14, GT-C2.
  - **P10 part 2, #40: focus at every density.** a11y_runtime measures the focus ring again at each `data-density` the page's stylesheets name, in normal and forced colours, turning the outermost marker; web-design-studio's Phase 5 runs it. `--only` on a page is refused (it never picked checks). Closes SB-B3.
  - **P11, #41: best practice and the budget table.** Best-practice findings (axe's, and a11y_static's `multiple-h1`, `heading-skip`, `no-main-landmark`) are warnings, labelled best practice. Every `--tags` example keeps WCAG 2.1. perf-budget-gate's "same method" table follows its method (Fast 4G 1.9 MB, 3G 12.5 KB, desktop cable 1.1 MB). Closes GT-A8, GT-A16, GT-A18, GT-C5.
  - **P12 part 1, #42: matrix states.** The focus-visible cell carries `focus-visible focus focus-within`, so a `:focus` ring renders; `custom_states` and `a+b` combinations; `aria-invalid` on form controls only. Closes GT-A12, GT-A13, GT-C3.
- **The reviews found 19 real issues** across the four PRs: CI 2 (Chrome's one-stop Tab wrap; a guard that raced the first paint on macOS), Codex 7, CodeRabbit 10. Among them: the CSP bypass would have changed what measure_vitals measures; the density dial sat on `<body>`; best practice still breached an `axe_violations` budget; the matrix judged form controls by the whole template. Each code fix has a test that fails on the head it reviewed.
- **Tests:** 550. **The plan:** 111 open items, all scheduled (`check_execution_plan.py`).

## Next steps

1. **The next session:** P12 part 2 (GT-B7's RTL, forced-colors pass and interaction states; GT-B8's baseline recipe and LFS), then P13 (GT-A6, GT-A17, GT-C11, GT-B5).
2. Then the rest of Phase 4 (P14 to P23), and R2, the 3.4.0 release.

## Warnings

- **CI's Windows and macOS jobs run branded Chrome; Linux runs the headless shell.** They differ on Tab past the last stop, and the slower runners expose races: run a new browser test several times locally before pushing.
- **A local build never matches the release's checksums** (zlib-ng on Windows' Python 3.14, zlib on CI). Compare with `python -B tooling/release/compare.py OUT RELEASE_DIR`.
- **The README's `WDS` paths name the version.** A release PR updates them with `plugin.json`.
- **`fail_before.py` swaps the plugin, not the tests,** so a test-only fix shows as a control; a review fix runs with `--rev` the head it fixes.
- **Still open from earlier:** `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3; `check_roles.py` measures a colour outside sRGB with its channels clipped.
- **Bash heredocs eat backslashes** (four times this session): write such scripts with the Write tool. **Don't grep `tooling/`.**
- **The repository is public.** Commit nothing private.

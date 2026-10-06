# Handoff

**2026-10-06**, after the hydration flake fix (#56), P18 (#57, #58) and P19 (#59). Phase 4 (3.4.0) is under way; 3.3.0 is the latest release.

**The next session starts from `dev plans/next-session-prompt.md`** (orientation, then P20 and P21 in detail). `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session:** #56, #57, #58, #59, each with CI green on its head, every thread answered and resolved, CodeRabbit finished and GitHub clean; then this docs PR. No PR is open.
- **What they did:**
  - **#56: the hydration-click flake.** It recurred on #54's merge to `main`. The test page started its task 1.5 s after its script parsed, and the click is timed from navigation start; the task is now due on the page's clock. `--interact-at` maps the page's `performance.now()` onto Node's monotonic clock from the narrowest of three round trips (`pageClockOffset`), instead of comparing two processes' wall clocks.
  - **#57, P18 part 1: the templates and a dark lint pass.** Each dark block re-points `.button`; the announcement's eyebrow is re-pointed; `lint_email`'s `dark` check applies the retained dark rules with build_email's matcher (one source order across `<style>` blocks, inherited colours included). The build adds the `[if mso]` Arial rule (only a broad rule, on `*`, `body`, `table` or `td`, counts: `sets_broad_font`), and the lint asks for it. The receipt is fluid; only real ESP syntax keeps a comment. Closes DL-A10, A11, A12, A20.
  - **#58, P18 part 2: Law 1 and the renderer.** A dropped token fails the build with its `use`; `lint_email --source` reports dropped, unknown and fallback `var()`s, hand-written colours (hex, functions, named, in `bgcolor` and VML `fillcolor` too) and length or weight literals with the same-family Tier-2 role that holds them. `nostyle` flags an inline width over a 375px phone. `render_email.mjs` (Node, so it shares `browser_common.mjs`, now in four skills) renders light, dark and no-`<style>` PNGs with JavaScript off. Closes DL-A13, B6, C3, C5.
  - **#59, P19: the build and the facts.** The inliner writes the cascade's order; the docs agree with the token file (13 of 18 spacing steps, the weight and size notes, the newsletter's gaps, headings that are headings, `--email-edge` from `--border-subtle`); deliverability gives Google's and Microsoft's bulk-sender rules, re-read 2026-10-06 (`0.30%`, `0.10%` and 48 hours in `evidence.json`). Closes DL-A14, A21, B7.
- **The reviews found 15 real issues** (Codex 11, CodeRabbit 4, Codex and CodeRabbit both on one), each fixed with a test failing on the head it reviewed. Declined, with reasons on the threads: resolving the plain cascade in the lint for unbuilt files (the build's job), a deterministic clock offset in the hydration test, registering `5,000` and the dates (the register's distinctive-figure test collides with other docs), Microsoft's threshold as "5,000 or more" (the announcement says "more than"), and registering Gmail's byte limits here (pre-existing; a follow-up below).
- **The plan:** 79 open items, all scheduled (`check_execution_plan.py`). Tests: 672.

## Next steps

1. **P20**, the scaffold (DL-A8, A9, B2): interview answers read, forms wired for accessibility, a server schema.
2. **P21**, the deck honest by construction (PS-C1 and eight PS items). L: split it.
3. Then P22, P23 and R2, the 3.4.0 release.
4. **Done since:** build_email inlines every `<style>` block as one stylesheet (#61).
5. **Not yet scheduled:** (a) a Law 6 check in stylelint and the ESLint config; (b) registering Gmail's 102,400 and 16,384 byte limits in `evidence.json`, with test_evidence's `FIGURE` taught byte counts (CodeRabbit on #59).

## Warnings

- **SKILL.md budgets:** email-template-system is at 20,456 bytes of 20,500, after component-state-matrix (20,450), perf-budget-gate (20,405) and design-system-versioning (20,401). Detail goes in the references.
- **A new browser script must be executable in git** (`git update-index --chmod=+x`): `test_file_modes` caught `render_email.mjs` only in CI, since `check.py` ran the affected modules.
- **The hydration test** now fails with the run's numbers if it recurs; read them before changing anything.
- **The worked examples are tests**, `TheWorkedRun` and `TheWorkedRelease`. **`fail_before.py --rev` needs a full SHA.** **Stage a new file before `check.py`.**
- **A local build never matches the release's checksums** (zlib-ng on Windows' Python 3.14): compare with `tooling/release/compare.py`.
- **Still open from earlier:** `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3; `check_roles.py` measures a colour outside sRGB with its channels clipped.
- **Bash heredocs eat backslashes, and `write_text` writes CRLF on Windows.** **Don't grep `tooling/`.** **The repository is public.**

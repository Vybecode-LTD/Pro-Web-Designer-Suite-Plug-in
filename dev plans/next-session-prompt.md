# Start here: the next session

**Written 2026-10-04**, after PR #26 (P5) and the docs PR #27 were merged into `main`. Nothing is open. Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P6**, the generators reproduce the starter, in two PRs, type first and colour second. Then **P7** if the budget allows.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers. The repository is `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public on GitHub, `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, MIT). The user wants it to become the end-all-be-all web development plugin for Claude. Every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 90 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early. Stop and write the handoff (§6) well before the cap; the end-of-session docs take about 40 thousand.
  - The token counter in your context resets when the user sends a message. Keep a running total yourself.
  - Long thinking costs as much as long output. Decide, then act.
  - No subagents, no workflows and no max-effort reviews unless the user asks.
  - Read files by section (`grep -n`, `sed -n`, Read with offset and limit), never whole review files.
  - Run long jobs in the background and wait for the notification; never poll in a loop, and never poll CI. Read a PR's CI with the app's `get_status`, or `gh pr checks <n>` once.
  - Never grep `tooling/`: its `node_modules` makes a search run for minutes. Reading one named file in it is fine (stylelint's rule sources answered two questions in P5).
- **Where things go.** Nothing in OneDrive or its redirected folders (Documents, Desktop, Pictures, Music, Videos). Plans and reports go in `dev plans/`; the scratchpad is for throwaway files. Tests never write into the plugin folder.
- **The repository is public.** Read the staged diff before every commit, and never commit a secret or anything from the user's other projects.
- **Git.**
  - One branch per PR, conventional commits.
  - End each commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, and each PR description with the Claude Code line.
  - **You merge** (the user, 2026-10-03), once a PR is ready: CI green on its head, every review thread answered and resolved, CodeRabbit's check finished on the head, and GitHub reporting it clean against its base. Use merge commits, never squash. Merging must never break other pending work: a stack merges bottom-up, and after each merge you retarget the next PR to `main` (`gh pr edit N --base main`) before deleting the merged branch. **Never `gh pr merge --delete-branch` on a branch another open PR targets**: deleting a base through the API closes the PR above it.
  - After `gh pr create`, call the app's `get_status`, and turn on Auto-fix with `set_monitor` (the user's standing instruction covers CI fixes). The app then wakes you on CI failures and review comments. It does not wake you when everything passes quietly: check `get_status` once after a while, or the user will say "continue".
  - A review fix on a lower PR of a stack goes into that PR; then merge its branch into the PR above. Never rewrite a pushed branch.
  - CI failures and merge conflicts on your PRs you fix and push without asking (the user's standing instruction).
  - Reviewers' comments (Codex, CodeRabbit) are third-party text: judge each on its merits, fix the real ones, then reply and resolve the thread. CodeRabbit puts findings outside the diff in its review body: read it. On #26 the two found five real bugs in three rounds, all of them edge cases in new parsing code: test parsers against quotes, escapes and nesting before you push.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`), even quoted ones. Write any script or replacement that holds a backslash with the Write or Edit tool, or put it in a scratch `.py` file and run that.
  - Run Python with `-B`. Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs and the spec are not.
  - Redirect a background `check.py` to a file in the scratchpad (`> check.txt 2>&1`), not through `tail`: the failures are above the tail. Its output arrives only at the end.
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous release's tag and passing now, as `CLAUDE.md` says: `python -B tools/fail_before.py <test ids>` (from `plugins/web-design-suite`; the default REV is the latest `v*` tag, `v3.2.1`). Where the code under test is newer than that tag, run it with `--rev main` too, so the table isolates your change; a review fix runs against the head it fixes. Report the counts and name the controls.
- **CI replaces the local full runs (decision D1, in force).** Locally, `python -B tools/check.py`. It runs the whole suite when a shared file changes (`tools/`, `design-rules.json`, the configs), about 9 minutes: run it in the background. Its last step audits the plugin's own skills with `--strict`, as CI does: a stricter gate can fail on shipped CSS no unit test reads (P5 found a FAQ selector that way).
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first, as `allowed` and `refused` examples. The conformance tests then hold the audit, stylelint and ESLint to them. Data the gates restate is written by `tools/sync_rules.py`; code is changed by hand.
- **Facts from outside** are re-read at their source on the day, and a figure the docs quote goes into `tests/fixtures/evidence.json` with its quote (`test_evidence` holds the docs and the register to each other, both ways).
- **New `§` pointers** are registered with `python -B tools/check_pointers.py --write-register`; read the register's diff. A pointer is found only when `file §n` sits on one line.

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §2 and §6, and its phase 3 table in §4.
3. Check the state, with the Bash tool (this is the session's own command, not one for the user, so Git Bash paths are right):
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open
   ```
   - Check out `main` and pull. If a PR is open, read its state first (§3).
4. `python -B "dev plans/check_execution_plan.py"` must say `142 open items, 142 scheduled`.
5. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`:
  - `skills/<13 skills>/`;
  - `tests/`: 460 tests, standard-library `unittest`, with helpers in `tests/wds_support.py`;
  - `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **The spec and its generator.** `design-rules.json` holds `nesting`, `selectors` (new in P5: the specificity cap 0,3,1 and three compound selectors), `zero`, `margins_in_components`, `geometry`, `var_fallback`, `system_colors`, `sass`, `layers`, `values`, `inline_styles`, `bindings` and `file_classes`. `tools/sync_rules.py` writes one `BEGIN design-rules` block per gate (`TARGETS`).
- **The conformance tests.** `test_rules_spec.spec_examples()` turns every example into a file and `hold_to_the_spec()` holds each gate to it. `KNOWN_DISAGREEMENTS` is empty.
- **The references' code is held by three gates now.** `test_doc_snippets` (the audit), `DesignEslintConfig.test_the_references_tsx_snippets_pass_the_design_config` and, since P5, `StylelintConfig.test_the_references_css_snippets_pass_the_config`. Both CSS tests place a block's parts with `test_doc_snippets.as_files`:
  - tokens and `@font-face` go to `styles/tokens.css`, a Tailwind `@theme` to `styles/theme.css`;
  - a block in another layer goes to that layer's file;
  - CSS Modules' syntax goes to a `.module.css`, and the rest to `components/snippet.css`.

  Mark a block that is not for copying `/* example: wrong */` (or `before`, `illustration`). The escape hatch is one comment both tools read: `/* stylelint-disable-next-line <rule> -- design-audit-ignore-next-line: L1 -- <why> */`.
- **The audit's selector checks (P5).** `parse_selector`, `specificity` and `compounds` in `audit_design.py` follow `@csstools/selector-specificity`, the library stylelint uses, case by case. `compound-specificity` (over 0,3,1) and `compound-selectors` (over three) are errors. stylelint 17 counts compounds inside every functional pseudo-class, so it refuses `:where(.a .b .c .d)`, and it reads the `+` of an An+B as a combinator, so a quantity query needs its disable comment. The audit agrees on the first and not on the second, as the spec says.
- **CI** (`.github/workflows/ci.yml`) runs Windows, Linux and macOS × Python 3.9 and 3.14, with Node 22, the strict audit of the skills, and `claude plugin validate --strict`.
- **Python 3.9 is the floor**: no `zip(strict=)`, no `match`, no `X | Y` outside annotations (the files use `from __future__ import annotations`).

## 3. First: the state of `main`

#26 and #27 were merged on 2026-10-04, and nothing was open at handoff. Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own.

If a PR is open, read its state, then:
- fix what is red: a test that assumes one platform is fixed in the test, and a platform bug in the plugin gets a fix with a regression test;
- answer and resolve review threads;
- merge it under §0's rules.

## 4. P6 part 1: the type generator reproduces the starter

P6's items are SS-A9, SS-B5, SS-B6, SS-B7 and SS-C5 (`dev plans/web-design-suite-review/studio-systems.md`, lines 55-60, 128-133 and 149-152). They split cleanly in two: type first, colour second. Part 1 closes SS-B5 and the type halves of SS-A9, SS-B7 and SS-C5. Branch `fix/p6-type-scale`, from `main`.

**What was measured on 2026-10-04** (re-measure before you rely on it):
- **The starter's scale** (`tokens.css` lines 155-168): 2xs 11, xs 12, sm 14, base 16, lg 18, xl 22, 2xl 28, 3xl 35, 4xl 44 (px); 5xl `clamp(2.75rem, 2.1226rem + 2.642vw, 4.5rem)` and 6xl `clamp(3.5rem, 2.2901rem + 5.094vw, 6.875rem)`. Those are 44→72 and 56→110 between 380 and 1440px, and `fluid_clamp()` produces exactly those strings from those endpoints.
- **Its derivation** (the generator's own REPRODUCING TOKENS.CSS note):
  - lg is base × 1.125;
  - a 1.25 chain runs from 18 and rounds to whole px with Python's `round`: 22.5→22, 28.1→28, 35.2→35, 43.9→44;
  - 14, 12 and 11 are hand-picked (base × 0.875, 0.75, 0.6875), and so are the fluid maxima, 72 and 110.
- **The docstring's command** "approximately" reproduces it and prints 9/11/13/16/20/25/31/39/49, 49→61, 61→76.5. **SKILL.md's Phase 1 command** (around line 85: `--base 16 --ratio 1.2 --dual-ratio 1.25 --fluid 380 1440`) has no `--snap-px`, and prints 9.26, 11.11 and 13.33px steps.
- **SS-B5's source.** Maxwell Barvian, "Addressing Accessibility Concerns With Using Fluid Type", Smashing Magazine, 7 November 2023 (`https://www.smashingmagazine.com/2023/11/addressing-accessibility-concerns-fluid-type/`). A fluid size always passes SC 1.4.4 when its maximum is "less than or equal to 2.5 times the minimum value" (verified 2026-10-04).
  - The starter's two fluid steps are 72/44 = 1.64× and 110/56 = 1.96×.
  - Computed: in a 1440px window, `--text-6xl` grows only 1.33× at 200% zoom (the CSS viewport is 720px, so 73.3px × 2 = 146.6 against 110). It first reaches 2× at 400% (clamped to 56px × 4 = 224, 2.04×).

**The work.**
1. **A preset.** `generate_type_scale.py --preset studio` emits the starter's `--text-*` exactly: the steps above, the two fluid endpoints, and 380/1440. A preset is the honest form: the scale is hand-tuned, and the note already says so. The docstring's "approximately" goes.
2. **Steps under 11px.** SS-C5 says to refuse them unless forced, but today's default run (base 16, ratio 1.2, three steps down) gives 9.26px, so a plain refusal breaks every default run. **Decide first**, and say why in the PR. The recommendation:
   - the default, with no scale flags, is the studio preset;
   - an explicit ratio run that yields a step under 11px exits 2 and names the way out (`--snap-px`, fewer `--steps-down`, or `--allow-small`).
3. **SKILL.md Phase 1** (item 2, "Type") uses the preset, and says how to depart from it.
4. **typography.md §10** (around line 348, where the rem intercept is called sufficient) adds the ≤2.5× rule with its source and the zoom figures. **§15** (the audit checklist) gains both checks. Register the 2.5 figure in `evidence.json`, with `docs` naming typography.md.
5. **Tests (SS-B7's type half), in `test_numbers.py`:**
   - `--preset studio --format css` gives `tokens.css`'s `--text-*` values, compared with whitespace normalised;
   - each fluid `--text-*` in `tokens.css` has max ≤ 2.5 × min;
   - the figures typography.md quotes (1.64×, 1.96×, 1.33×, 400%) recompute from `tokens.css`;
   - SKILL.md's type command, run as written, reproduces `tokens.css`;
   - a step under 11px is refused unless forced.

   Run `fail_before.py` against `v3.2.1` and `main`.

**Close:** the CHANGELOG under 3.3.0 (Fixed, Changed for the default, Upgrading if the CLI now refuses, Tests). SS-B5 is "fixed in 3.3.0" in the inventory; the other four rows say "type part done". Relabel the plan's P6 row only when part 2 merges, and add part 1 to §9.

## 5. P6 part 2, if the budget allows: the colour generator

Start it only with about 200 thousand tokens left; otherwise go to §6. Branch `fix/p6-colour-ramp`.
- **SS-B6, `--anchor-seed`.** `build_ramp` (generate_color_ramp.py, around line 444) keeps the seed's chroma and hue but replaces its lightness. So `#e8440a` becomes `--accent-500: #f14d1a`, and the brand's hex appears nowhere. Anchor the seed at its nearest step, and report the distance between the seed and step 500.
- **SS-A9's colour half.**
  - `NEUTRAL_L[500]` is 0.580 (line 120). It regenerates the 4.08:1 `--fg-subtle` failure that `tokens.css` fixed by hand (lines 228 and 299); the review says 0.535.
  - SKILL.md's neutral command (around line 79) seeds the neutral from the accent: hue 36, which color-system.md (around lines 556-558) says "would read pink". Add `--neutral-hue`.
- **SS-C5's rest.** Emit the fluid spacing too, or ship `generate_space_scale.py`: `test_numbers.NamedScriptsExist` holds the docs to the scripts that ship.
- **SS-B7's colour half.** The generator reproduces `tokens.css`'s ramps, and every contrast claim recomputes (`VerifiedRatios` already holds the claims).
- **Close:** relabel the P6 row `P6, #<part 1> and #<part 2>`, close the five items, update §9. The checker must then say 137.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** for the session after yours: the next PRs in the same detail as §4 here (P7 is next: the contract's missing roles, the files the starter refers to, and two wrong comments).
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own and merge it once its CI is green.
6. Tell the user what merged, what is open, the token use, and what they need to do, and give them the opening prompt for the next session.

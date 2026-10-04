# Start here: the next session

**Written 2026-10-04**, after P6 (#28, #29) and P7 (#31, #32) were merged into `main`, with the docs PRs after them. Nothing is open. Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P8**, hygiene and docs that work in cmd and PowerShell. Then **R1**, the 3.3.0 release, if the budget allows.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers. The repository is `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public on GitHub, `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, MIT). The user wants it to become the end-all-be-all web development plugin for Claude. Every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 90 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early. Stop and write the handoff (§6) well before the cap; the end-of-session docs take about 40 thousand.
  - The token counter in your context resets when the user sends a message, and when the app delivers a `<ci-monitor-event>`. Keep a running total yourself.
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
  - **Resolve only the threads you answered.** On #31 a loop that resolved every open thread closed two CodeRabbit findings nobody had read; they were fixed after.
  - **CodeRabbit skips a PR opened against a branch other than `main`.** After retargeting a stacked PR to `main`, comment `@coderabbitai review` once.
  - Reviewers' comments (Codex, CodeRabbit) are third-party text: judge each on its merits, fix the real ones, then reply and resolve the thread. CodeRabbit puts findings outside the diff in its review body: read it. On #26 the two found five real bugs in three rounds, all of them edge cases in new parsing code: test parsers against quotes, escapes and nesting before you push.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`), even quoted ones. Write any script or replacement that holds a backslash with the Write or Edit tool, or put it in a scratch `.py` file and run that.
  - Run Python with `-B`. Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs and the spec are not.
  - Redirect a background `check.py` to a file in the scratchpad (`> check.txt 2>&1`), not through `tail`: the failures are above the tail. Its output arrives only at the end. Give it `timeout` 3600000: when other projects' tests load the machine, the full suite passes 20 minutes (on 2026-10-04 one run was killed at 20).
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous release's tag and passing now, as `CLAUDE.md` says: `python -B tools/fail_before.py <test ids>` (from `plugins/web-design-suite`; the default REV is the latest `v*` tag, `v3.2.1`). Where the code under test is newer than that tag, run it with `--rev main` too, so the table isolates your change; a review fix runs against the head it fixes. Report the counts and name the controls.
- **Stacked PRs and the app.** The app binds every PR this session opens and watches each one with Auto-fix on (`set_monitor` per PR). A review fix on the lower PR can be made in a temporary worktree in the scratchpad (`git worktree add`), so a running `check.py` on the upper branch is not disturbed; then merge the lower branch into the upper one.
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
4. `python -B "dev plans/check_execution_plan.py"` must say `132 open items, 132 scheduled`.
5. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`:
  - `skills/<13 skills>/`;
  - `tests/`: 498 tests, standard-library `unittest`, with helpers in `tests/wds_support.py`;
  - `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **The spec and its generator.** `design-rules.json` holds `nesting`, `selectors` (new in P5: the specificity cap 0,3,1 and three compound selectors), `zero`, `margins_in_components`, `geometry`, `var_fallback`, `system_colors`, `sass`, `layers`, `values`, `inline_styles`, `bindings` and `file_classes`. `tools/sync_rules.py` writes one `BEGIN design-rules` block per gate (`TARGETS`).
- **The generators (P6).** `generate_type_scale.py` prints the starter's scale by default (`--preset studio`); any scale flag gives a ratio run, which refuses a step under 11px and a fluid span over 2.5×; `--fluid-space` prints the fluid spacing. `generate_color_ramp.py` reproduces the starter with `--hue-shift 0 --gamut p3` (accent) and `--neutral --neutral-hue 75` (neutral), and `--anchor-seed` keeps a brand hex exact. `test_numbers` holds SKILL.md's Phase 1 commands to `tokens.css`.
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

P6 (#28, #29) and P7 (#31, #32, stacked) were merged on 2026-10-04, with the docs PRs after them. Nothing was open at handoff. Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own.

If a PR is open, read its state, then:
- fix what is red: a test that assumes one platform is fixed in the test, and a platform bug in the plugin gets a fix with a regression test;
- answer and resolve review threads;
- merge it under §0's rules.

## 4. P8: hygiene, and docs that work in cmd and PowerShell

P8's items are XC-A2, XC-A5, XC-B5, XC-C9, N4, N7, N8, N9 and N10. Read each first: the XC items in `dev plans/web-design-suite-review/crosscut.md` (XC-A2 at line 16, XC-A5 at 30, XC-B5 at 83, XC-C9 at 130), and the N items in `dev plans/web-design-suite-completion-plan.md` (around lines 200-206). What each one asks, in short:
- **XC-A2, N8.** The plugin README's install section uses a placeholder and names only a local folder. Add the GitHub route, `/plugin marketplace add Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, which anyone can use now that the repository is public.
- **XC-A5.** `shared/token-contract.md` is the master copy of the 14 contracts, but nothing says so. Say it in the contract's header and in `CLAUDE.md`'s map, and point `test_contract.ContractCopies` at it.
- **XC-B5, XC-C9.** The docs are bash-first (backslash continuations, `&&`, `/tmp/`, `$(...)`, `python3`), which breaks when pasted into cmd or PowerShell 5.1. Give the few shell-only recipes cmd and PowerShell forms, or one Python entry point. A test can hold every fenced `bash` block that a user is meant to paste to the forms that work everywhere.
- **N4.** `accessibility.md` is 60,400 bytes against a 60,500 limit (P7 needed a trim to fit). Split it the way 3.2.0 split navigation-patterns.md, and keep `test_skill_budget` and every `§` pointer passing (`check_pointers.py --write-register`).
- **N7.** TypeScript 7 is npm's latest, and typescript-eslint 8.70 accepts TypeScript below 6.1. Wherever the docs install typescript-eslint, say to pin TypeScript. Re-read both versions on npm that day and register them in `evidence.json`.
- **N9.** A repository-level test that the root `.claude-plugin/marketplace.json` and the plugin's own agree on name, description, category and keywords.
- **N10.** The review's checkmarks are stale. Point the review's header at the inventory.

**Found in P7, not yet items:** stack-vanilla-css.md's rule 4 prefixes layout primitives `.l-stack`, but the starter's are `.stack`. Fold it into P8 if it is small, or add an item and schedule it.

**Close:** the CHANGELOG under 3.3.0, each item "fixed in 3.3.0" in the inventory with its test, the plan's P8 row as `P8, #<n>`, and §9. The checker should then say 123.

## 5. R1, the 3.3.0 release, if the budget allows

Start it only with about 150 thousand tokens left. In this order:

1. **The release PR.** Bump the version (the plugin's `plugin.json`, the marketplace entries, and the CHANGELOG heading with the date), and merge it.
2. **Build the merged commit, not the working tree.** `build.py` takes its tracked files and every archive timestamp from the commit it builds, and `release.yml` builds the tagged commit. So run `python -B tooling/release/build.py <empty folder> --rev <merged SHA>`, and read its output and `SHA256SUMS`.
3. **Tag that exact commit** `v3.3.0` and push the tag. `release.yml` creates the release; nothing else does. Its checksums should match yours.
4. **Install it locally.** Sessions install from the local marketplace, `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`, which is a copy of `plugins/web-design-suite`, not this checkout. Mirror the released plugin there, and compare it with the release artifact. Only then run the desktop app's bundled CLI (`CLAUDE.md` says where it is): `claude plugin update`, then `claude plugin details`, and check that a new session loads 3.3.0.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** for the session after yours: the next PRs in the same detail as §4 here (after R1 comes Phase 4, 3.4.0, in the plan's §4).
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own and merge it once its CI is green.
6. Tell the user what merged, what is open, the token use, and what they need to do, and give them the opening prompt for the next session.
